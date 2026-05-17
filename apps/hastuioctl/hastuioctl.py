#!/usr/bin/env -S uv --no-project --with pyyaml --with paho-mqtt --with loguru --with pydantic run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyyaml",
#     "paho-mqtt",
#     "loguru",
#     "pydantic>=2",
# ]
# ///

"""
hastuioctl - Home Assistant audio control daemon.

Waits in the background, connects to MQTT, and dispatches commands
to local media players (playerctl, pactl, mpv, espeak ...) based on
a declarative events.yaml file.

Usage:
    uv run ./hastuioctl.py --config events.yaml

Environment:
    HASTUOCTL_CONFIG      path to events.yaml (default: events.yaml in cwd)
    HASTUOCTL_LOG_LEVEL   logging level (default: INFO)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from typing import Any, Dict, List

import yaml

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover
    mqtt = None

from loguru import logger
from pydantic import BaseModel, Field, model_validator

# ── Pydantic models ─────────────────────────────────────────────────

class Trigger(BaseModel, extra="forbid"):
    """Match criteria: command exact, text regex, optional extra keys."""
    command: str | None = None
    text: str | None = None

    def match(self, payload: Dict[str, Any]) -> bool:
        """AND logic: command -> text -> extra keys."""
        # 1 - command match
        if self.command is not None and payload.get("command") != self.command:
            return False
        # 2 - text regex match
        if self.text is not None:
            params = payload.get("params")
            if not isinstance(params, dict):
                return False
            text = params.get("text") or str(params)
            if not re.search(self.text, str(text), re.IGNORECASE):
                return False
        # 3 - extra exact-match keys
        if self.model_extra:
            for k, v in self.model_extra.items():
                if payload.get(k) != v:
                    return False
        return True


class Action(BaseModel):
    """Shell command to execute."""
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    description: str = ""
    publish_reply_to: str | None = None


class Event(BaseModel):
    """MQTT topic + trigger -> list of actions."""
    topic: str
    trigger: Trigger
    actions: List[Action]

    @model_validator(mode="before")
    @classmethod
    def _backward_compat(cls, data: Any) -> Any:
        """Allow single 'action' key for backward compat."""
        if not isinstance(data, dict):
            return data
        if "action" in data and "actions" not in data:
            data["actions"] = [data.pop("action")]
        return data


class Config(BaseModel):
    """Top-level config: a list of events."""
    events: List[Event] = Field(default_factory=list)


# ── Template engine ─────────────────────────────────────────────────

_RE_TPL = re.compile(r"\{\{(.*?)\}\}")


def _resolve_path(parts: list[str], obj: Any) -> Any:
    """Navigate dict/list keys via '.'-split path."""
    if not parts:
        return None
    for key in parts:
        if key.startswith('"') and key.endswith('"'):
            key = key[1:-1]
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list):
            try:
                obj = obj[int(key)]
            except (ValueError, IndexError):
                obj = None
                break
        elif hasattr(obj, key):
            obj = getattr(obj, key)
        else:
            return None
        if obj is None:
            return None
    return obj


def _eval_expr(expr: str, ctx: Dict[str, Any]) -> Any:
    """Evaluate {{ expr }} with optional | default fallback."""
    if " | default " in expr:
        key_part, _, default_val = expr.partition(" | default ")
        value = _resolve_path(key_part.strip().split("."), ctx)
        if value is None:
            return default_val.strip() if default_val.strip() else ""
        return str(value)
    return _resolve_path(expr.split("."), ctx)


def render(template: str, ctx: Dict[str, Any]) -> str:
    """Substitute {{ ... }} placeholders."""
    def _inner(m: re.Match) -> str:
        value = _eval_expr(m.group(1).strip(), ctx)
        return str(value) if value is not None else ""
    return _RE_TPL.sub(_inner, template)


# ── YAML loading ────────────────────────────────────────────────────

def load_config(path: str) -> Config:
    """Parse events.yaml into a Config with Pydantic validation."""
    with open(path) as f:
        raw: Any = yaml.safe_load(f)
    if raw is None:
        raw = {}
    return Config.model_validate(raw)


# ── Action executor ─────────────────────────────────────────────────

def _execute_action(action: Action, payload: Dict[str, Any]) -> str | None:
    """Run a single action, return stdout for reply."""
    ctx: Dict[str, Any] = {"params": payload.get("params") or {}}
    if (cmd := payload.get("command")) is not None:
        ctx["command"] = cmd

    rendered_args: List[str] = [render(a, ctx) for a in action.args]
    extra_env: Dict[str, str] = {k: render(v, ctx) for k, v in action.env.items()}
    env = {**os.environ, **extra_env}
    cmd_line = [action.command] + rendered_args

    logger.debug("[%s] %s %s", action.description, action.command,
                 shlex.join(cmd_line))

    try:
        result = subprocess.run(cmd_line, capture_output=True, text=True,
                                timeout=30, env=env)
        if result.returncode != 0:
            logger.warning("[%s] return code %d: %s",
                           action.description, result.returncode,
                           result.stderr[:200])
        return result.stdout
    except FileNotFoundError:
        logger.error("[%s] binary '%s' not found",
                     action.description, action.command)
    except subprocess.TimeoutExpired:
        logger.error("[%s] timed out after 30s", action.description)
    return None


# ── MQTT callback ───────────────────────────────────────────────────

def _mqtt_handler(msg: Any, events: List[Event], client: Any) -> None:
    """Dispatch incoming MQTT message to matching events, publish replies."""
    stdout_stack: List[str] = []  # track stdout for reply chain

    def _do_reply(action: Action, action_stdout: str | None) -> None:
        """Publish stdout to specified topic."""
        if not action.publish_reply_to or not action_stdout:
            return
        data = action_stdout.strip()
        if not data:
            return
        reply_payload = {"status": "ok", "data": data}
        try:
            client.publish(action.publish_reply_to, json.dumps(reply_payload))
            logger.debug("reply -> %s", action.publish_reply_to)
        except Exception as exc:
            logger.warning("publish reply failed: %s", exc)

    try:
        payload = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        payload = {"command": msg.payload.decode(), "params": ""}

    logger.debug("received  topic=%s  payload=%s", msg.topic, payload)

    for event in events:
        if event.trigger.match(payload):
            logger.info("matched  topic=%s", event.topic)
            for i, action in enumerate(event.actions):
                stdout = _execute_action(action, payload)
                stdout_stack.append(stdout or "")
                if i < len(event.actions) - 1:
                    # Middle actions - pass stdout to next action via params
                    if stdout and stdout.strip():
                        merged = dict(payload.get("params") or {})
                        merged["stdout"] = stdout.strip()
                        payload["params"] = merged
                else:
                    # Last action - publish reply if configured
                    _do_reply(action, stdout)
            # Clear stdout_stack for next message
            stdout_stack.clear()
            break  # first match only
    else:
        logger.debug("no match for topic=%s", msg.topic)


# ── Main ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="HA-to-desktop audio control daemon")
    parser.add_argument("--config", "-c",
                        default=os.environ.get("HASTUOCTL_CONFIG", "events.yaml"),
                        help="Path to events.yaml")
    parser.add_argument("--mqtt-host",
                        default=os.environ.get("MQTT_HOST", "127.0.0.1"),
                        help="MQTT broker hostname")
    parser.add_argument("--mqtt-port", type=int,
                        default=int(os.environ.get("MQTT_PORT", "1883")),
                        help="MQTT broker port")
    parser.add_argument("--mqtt-client-id",
                        default=os.environ.get("MQTT_CLIENT_ID", "hastuioctl"),
                        help="MQTT client ID")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    handler = {"sink": sys.stdout}
    log_level = os.environ.get("HASTUOCTL_LOG_LEVEL",
                               "DEBUG" if args.verbose else "INFO")
    logger.remove()
    logger.add(**handler, level=log_level)

    logger.info("(c) hastuioctl - HA audio control daemon")

    path = os.path.abspath(args.config)
    logger.info("loading config from %s", path)
    try:
        config = load_config(path)
    except Exception as exc:
        logger.error("failed to load config: %s", exc)
        sys.exit(1)

    events = config.events
    logger.info("loaded %d event rules", len(events))

    topics = sorted({e.topic for e in events})
    logger.info("MQTT topics: %s", ", ".join(topics,))

    if mqtt is None:  # pragma: no cover
        logger.error("paho-mqtt not installed: pip install paho-mqtt")
        sys.exit(1)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=args.mqtt_client_id)

    def on_connect(_c: Any, _u: Any, _f: Any, rc: int) -> None:
        if rc == 0:
            for topic in topics:
                client.subscribe(topic)
                logger.info("subscribed -> %s", topic)
            logger.info("MQTT connected")
        else:
            logger.error("MQTT connect failed: %d", rc)

    def on_disconnect(_c: Any, _u: Any, rc: int) -> None:
        logger.warning("MQTT disconnected (rc=%d) - reconnecting", rc)

    client.on_connect = on_connect
    client.on_message = lambda c, u, m: _mqtt_handler(m, events, c)
    client.on_disconnect = on_disconnect

    def _reconnect() -> None:
        try:
            client.connect(args.mqtt_host, args.mqtt_port, 60)
            client.loop_start()
        except OSError as exc:
            logger.error("cannot connect to MQTT at %s:%d - %s",
                         args.mqtt_host, args.mqtt_port, exc)
            raise exc

    try:
        _reconnect()
    except OSError:
        logger.info("will retry in 5 s ...")
        while True:
            try:
                _reconnect()
                break
            except OSError:
                time.sleep(5)

    logger.info("ready. listening for HA commands ...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("shutting down ...")
        client.loop_stop()
        client.disconnect()


# ── Exported API ────────────────────────────────────────────────────

load_events = load_config  # alias for backward compat


if __name__ == "__main__":
    main()

