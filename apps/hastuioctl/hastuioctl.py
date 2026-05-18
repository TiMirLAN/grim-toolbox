#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "click",
#     "paho-mqtt",
#     "loguru",
#     "pydantic>=2",
#     "pyyaml",
# ]
# ///

"""
hastuioctl - Home Assistant audio control daemon.

Waits in the background, connects to MQTT, and dispatches commands
to local media players (playerctl, pactl, mpv, espeak ...) based on
a declarative events.yaml file.

Config location (in order of priority):
    1. $HASTUOCTL_CONFIG env variable
    2. ~/.config/hastuioctl/events.yaml (default)
    3. events.yaml in current working directory

Usage:
    uv run ./hastuioctl.py
    uv run ./hastuioctl.py --config /path/to/events.yaml

Environment:
    HASTUOCTL_CONFIG      path to events.yaml
    HASTUOCTL_LOG_LEVEL   logging level (default: INFO)
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from typing import Any, Dict, List

import click
import paho.mqtt.client as mqtt
import yaml
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class HaPayload(BaseModel):
    """Validated Home Assistant MQTT payload."""

    model_config = ConfigDict(extra="allow")
    command: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: Any) -> "HaPayload":
        """Parse raw MQTT payload into validated model."""
        # If already parsed dict, validate directly
        if isinstance(raw, dict):
            return cls.model_validate(raw)
        # Try JSON parse
        if isinstance(raw, str):
            try:
                return cls.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValueError):
                # Treat as plain command
                return cls(command=raw)
        # None or other → minimal model
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


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

    logger.debug("[%s] %s %s", action.description, action.command, shlex.join(cmd_line))

    try:
        result = subprocess.run(
            cmd_line, capture_output=True, text=True, timeout=30, env=env
        )
        if result.returncode != 0:
            logger.warning(
                "[%s] return code %d: %s",
                action.description,
                result.returncode,
                result.stderr[:200],
            )
        return result.stdout
    except FileNotFoundError:
        logger.error("[%s] binary '%s' not found", action.description, action.command)
    except subprocess.TimeoutExpired:
        logger.error("[%s] timed out after 30s", action.description)
    return None


# ── MQTT callback ───────────────────────────────────────────────────


def _do_reply(client: Any, action: Action, action_stdout: str) -> None:
    """Publish action stdout to configured reply topic."""
    if not action.publish_reply_to or not action_stdout.strip():
        return
    reply_payload = {"status": "ok", "data": action_stdout}
    try:
        client.publish(action.publish_reply_to, json.dumps(reply_payload))
        logger.debug("reply -> %s", action.publish_reply_to)
    except Exception as exc:
        logger.warning("publish reply failed: %s", exc)


# ── MQTT Handler class ─────────────────────────────────────────────────


class MQTTHandler:
    """Encapsulates MQTT connection state and callbacks."""

    def __init__(self, topics: List[str], events: List[Event], client: Any) -> None:
        self.topics = topics
        self.events = events
        self.client = client

    def on_connect(self, _c: Any, _u: Any, _f: Any, rc: int, _p: Any = None) -> None:
        """Handle MQTT connection."""
        if rc == 0:
            for topic in self.topics:
                self.client.subscribe(topic)
                logger.info("subscribed -> %s", topic)
            logger.info("MQTT connected")
        else:
            logger.error("MQTT connect failed: %d", rc)

    def on_disconnect(
        self, _c: Any, _u: Any, _df: Any, rc: int, _p: Any = None
    ) -> None:
        """Handle MQTT disconnection."""
        logger.warning("MQTT disconnected (rc=%d) - reconnecting", rc)

    def on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        """Handle incoming MQTT message."""
        payload_dict = HaPayload.from_raw(msg.payload.decode()).model_dump()

        logger.debug("received  topic=%s  payload=%s", msg.topic, payload_dict)

        matched = False
        for event in self.events:
            if event.trigger.match(payload_dict):
                matched = True
                logger.info("matched  topic=%s", event.topic)
                for i, action in enumerate(event.actions):
                    stdout = _execute_action(action, payload_dict)
                    if not stdout or not stdout.strip():
                        continue
                    if i < len(event.actions) - 1:
                        stdout_copy = dict(payload_dict.get("params") or {})
                        stdout_copy["stdout"] = stdout.strip()
                        payload_dict["params"] = stdout_copy
                    else:
                        _do_reply(client, action, stdout.strip())
        if not matched:
            logger.debug("no match for topic=%s", msg.topic)


# ── Main ────────────────────────────────────────────────────────────────


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--config",
    "-c",
    default=lambda: os.environ.get(
        "HASTUOCTL_CONFIG",
        os.path.expanduser("~/.config/hastuioctl/events.yaml"),
    ),
    show_default=True,
    help="Path to events.yaml",
)
@click.option(
    "--mqtt-host",
    default=lambda: os.environ.get("MQTT_HOST", "127.0.0.1"),
    show_default=True,
    help="MQTT broker hostname",
)
@click.option(
    "--mqtt-port",
    type=int,
    default=lambda: os.environ.get("MQTT_PORT", "1883"),
    show_default=True,
    help="MQTT broker port",
)
@click.option(
    "--mqtt-client-id",
    default=lambda: os.environ.get("MQTT_CLIENT_ID", "hastuioctl"),
    show_default=True,
    help="MQTT client ID",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def main(
    config: str, mqtt_host: str, mqtt_port: int, mqtt_client_id: str, verbose: bool
) -> None:
    """HA-to-desktop audio control daemon."""
    # Click auto-generates --help, uses lazy defaults from env
    handler = {"sink": sys.stdout}
    log_level = os.environ.get("HASTUOCTL_LOG_LEVEL", "DEBUG" if verbose else "INFO")
    logger.remove()
    logger.add(**handler, level=log_level)

    logger.info("(c) hastuioctl - HA audio control daemon")

    path = os.path.abspath(config)
    logger.info("loading config from %s", path)
    try:
        config_obj = load_config(path)
    except Exception as exc:
        logger.error("failed to load config: %s", exc)
        sys.exit(1)

    events = config_obj.events
    logger.info("loaded %d event rules", len(events))

    topics = sorted({e.topic for e in events})
    logger.info("MQTT topics: %s", ", ".join(topics))

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=mqtt_client_id)
    handler = MQTTHandler(topics, events, client)

    client.on_connect = handler.on_connect
    client.on_message = handler.on_message
    client.on_disconnect = handler.on_disconnect

    def _reconnect() -> None:
        client.connect(mqtt_host, mqtt_port, 60)
        client.loop_start()

    try:
        _reconnect()
    except OSError as exc:
        logger.error("cannot connect to MQTT at %s:%d - %s", mqtt_host, mqtt_port, exc)
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


if __name__ == "__main__":
    main()
