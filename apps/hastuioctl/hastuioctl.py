#!/usr/bin/env -S uv --no-project --with pyyaml --with paho-mqtt --with loguru run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyyaml",
#     "paho-mqtt",
#     "loguru",
# ]
# ///

"""
hastuioctl — Home Assistant audio control daemon.

Waits in the background, connects to MQTT, and dispatches commands
to local media players (playerctl, pactl, mpv, espeak …) based on
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
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Dependencies ────────────────────────────────────────────────────
import yaml  # noqa: E402

try:
    import paho.mqtt.client as mqtt  # noqa: E402
except ImportError:  # pragma: no cover
    mqtt = None

from loguru import logger  # noqa: E402

# ── Data classes ────────────────────────────────────────────────────

@dataclass
class Trigger:
    command: Optional[str] = None
    text: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    publish_reply_to: Optional[str] = None


@dataclass
class Event:
    topic: str
    trigger: Trigger
    action: Action

# ── Template engine ─────────────────────────────────────────────────

RE_TEMPLATE = re.compile(r"\{\{(.*?)\}\}")


def _resolve_path(parts: list[str], obj: Any) -> Any:
    """Navigate dict/list keys via '.'-split path."""
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


def _eval_expr(expr: str, context: Dict[str, Any]) -> Any:
    """Evaluate a single template expression."""
    if "| default " in expr:
        key_part, _, default_val = expr.partition("| default ")
        value = _walk_path(key_part.strip().split("."), context)
        if value is None:
            return default_val.strip() if default_val.strip() else ""
        return str(value)
    return _walk_path(expr.split("."), context)


def _walk_path(path: list[str], context: Dict[str, Any]) -> Any:
    """Resolve a dotted path against a context dict."""
    if not path:
        return None
    obj: Any = context
    for key in path:
        obj = _resolve_path([key], obj)
        if obj is None:
            return None
    return obj


def render(template: str, context: Dict[str, Any]) -> str:
    """Substitute {{ ... }} placeholders in *template*."""

    def _inner(match: re.Match) -> str:
        expr = match.group(1).strip()
        value = _eval_expr(expr, context)
        return str(value) if value is not None else ""

    return RE_TEMPLATE.sub(_inner, template)


# ── YAML loader ─────────────────────────────────────────────────────

def load_events(path: str) -> List[Event]:
    """Parse events.yaml and return a list of Event objects."""
    with open(path, "r") as f:
        raw: Dict[str, Any] = yaml.safe_load(f)

    raw_events: List[Dict[str, Any]] = raw.get("events", [])
    events: List[Event] = []

    for raw_ev in raw_events:
        trigger_section: Dict[str, Any] = raw_ev.get("trigger", {})

        # Split trigger keys into "primary" (command, text) vs "extra"
        primary: Dict[str, Any] = {}
        extra: Dict[str, Any] = {}
        for k, v in trigger_section.items():
            if k in ("command", "text"):
                primary[k] = v
            else:
                extra[k] = v

        trigger = Trigger(
            command=primary.get("command"),
            text=primary.get("text"),
            extra=extra,
        )

        action = Action(
            command=raw_ev["action"]["command"],
            args=raw_ev["action"].get("args", []),
            env=raw_ev["action"].get("env", {}),
            description=raw_ev["action"].get("description", ""),
            publish_reply_to=raw_ev["action"].get("publish_reply_to"),
        )

        events.append(Event(
            topic=raw_ev["topic"],
            trigger=trigger,
            action=action,
        ))

    return events


# ── Event matching ──────────────────────────────────────────────────

def match_trigger(trigger: Trigger, payload: Dict[str, Any]) -> bool:
    """Return True if *payload* matches the trigger rules.

    Evaluation order:
    1. If trigger has a ``command``, it must match exactly.
    2. If trigger has ``text`` (regex), payload["params"]["text"] must
       match it. Both checks apply when both fields are present (AND).
    3. Extra keys must also match exactly.
    """
    command = payload.get("command")

    # 1 — command match
    if trigger.command is not None:
        if command is None or command != trigger.command:
            return False

    # 2 — text regex match
    if trigger.text is not None:
        params = payload.get("params")
        if not isinstance(params, dict):
            return False
        text = params.get("text", "")
        if text is None:
            text = str(params)
        if not re.search(trigger.text, str(text), re.IGNORECASE):
            return False

    # 3 — extra exact-match keys
    for k, v in trigger.extra.items():
        if payload.get(k) != v:
            return False

    return True


# ── Action executor ─────────────────────────────────────────────────

def build_context(
    params: Any, command: Optional[str] = None,
) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {"params": params or {}}
    if command is not None:
        ctx["command"] = command
    return ctx


def run_action(
    action: Action,
    payload: Dict[str, Any],
    *,
    mqtt_client: Any,
) -> Optional[str]:
    """Execute the action. Returns stdout (used for reply publishing)."""
    params = payload.get("params") or {}
    cmd = payload.get("command")
    ctx = build_context(params, cmd)

    rendered_args: List[str] = [render(a, ctx) for a in action.args]

    extra_env: Dict[str, str] = {
        k: render(v, ctx) for k, v in action.env.items()
    }
    env = {**os.environ, **extra_env}

    cmd_line = [action.command] + rendered_args
    logger.debug(
        "[action] %s: %s %s",
        action.description,
        action.command,
        shlex.join(rendered_args),
    )

    try:
        result = subprocess.run(
            cmd_line,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        if result.returncode != 0:
            logger.warning(
                "[action] %s return code %d: %s",
                action.description,
                result.returncode,
                result.stderr[:200],
            )

        # Publish reply if requested
        reply_topic = action.publish_reply_to
        if reply_topic and result.stdout.strip() and mqtt_client:
            reply_payload = {"status": "ok", "data": result.stdout.strip()}
            try:
                mqtt_client.publish(
                    reply_topic, json.dumps(reply_payload)
                )
                logger.debug("reply → %s", reply_topic)
            except Exception as exc:
                logger.warning(
                    "failed to publish reply to %s: %s", reply_topic, exc
                )

        return result.stdout

    except FileNotFoundError:
        logger.error(
            "[action] %s — binary '%s' not found",
            action.description,
            action.command,
        )
    except subprocess.TimeoutExpired:
        logger.error(
            "[action] %s — timed out after 30s",
            action.description,
        )

    return None


# ── MQTT callback ───────────────────────────────────────────────────

def _mqtt_on_message(
    _client: Any,
    _userdata: Any,
    msg: Any,
    *,
    subscriptions: List[Event],
) -> None:
    """Try every subscribed event for each incoming message."""
    try:
        payload = json.loads(msg.payload.decode())
    except json.JSONDecodeError:
        payload = {"command": msg.payload.decode(), "params": ""}

    logger.debug("received  topic=%s  payload=%s", msg.topic, payload)

    for event in subscriptions:
        if match_trigger(event.trigger, payload):
            logger.info("⚡ matched  topic=%s", event.topic)
            run_action(event.action, payload, mqtt_client=_client)
            break  # first match wins
    else:
        logger.debug("no match for topic=%s", msg.topic)


# ── Main ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="HA-to-desktop audio control daemon",
    )
    parser.add_argument(
        "--config", "-c",
        default=os.environ.get("HASTUOCTL_CONFIG", "events.yaml"),
        help="Path to events.yaml",
    )
    parser.add_argument(
        "--mqtt-host",
        default=os.environ.get("MQTT_HOST", "127.0.0.1"),
        help="MQTT broker hostname",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=int(os.environ.get("MQTT_PORT", "1883")),
        help="MQTT broker port",
    )
    parser.add_argument(
        "--mqtt-client-id",
        default=os.environ.get("MQTT_CLIENT_ID", "hastuioctl"),
        help="MQTT client ID",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
    )
    args = parser.parse_args()

    handler = {"sink": sys.stdout}
    log_level = os.environ.get(
        "HASTUOCTL_LOG_LEVEL", "DEBUG" if args.verbose else "INFO"
    )
    logger.remove()
    logger.add(**handler, level=log_level)

    logger.info(
        r"""╔══════════════════════════════════════════╗
║   hastuioctl — HA audio control daemon   ║
╚══════════════════════════════════════════╝"""
    )

    path = os.path.abspath(args.config)
    logger.info("loading events from %s", path)
    events = load_events(path)
    logger.info("loaded %d event rules", len(events))

    topics = sorted({e.topic for e in events})
    logger.info("MQTT topics: %s", ", ".join(topics))

    if mqtt is None:  # pragma: no cover
        logger.error("paho-mqtt not installed: pip install paho-mqtt")
        sys.exit(1)

    def on_connect(_client: Any, _userdata: Any, _flags: Any, rc: int) -> None:
        if rc == 0:
            for topic in topics:
                _client.subscribe(topic)
                logger.info("subscribed → %s", topic)
            logger.info("✅ MQTT connected")
        else:
            logger.error("MQTT connect failed: %d", rc)

    def on_disconnect(
        _client: Any,
        _userdata: Any,
        rc: int,
    ) -> None:
        logger.warning("❌ MQTT disconnected (rc=%d) — reconnecting", rc)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=args.mqtt_client_id,
    )
    client.on_connect = on_connect
    client.on_message = lambda c, u, m: _mqtt_on_message(
        c, u, m, subscriptions=events
    )
    client.on_disconnect = on_disconnect

    def _connect_loop() -> None:
        client.connect(args.mqtt_host, args.mqtt_port, 60)
        client.loop_start()

    try:
        _connect_loop()
    except OSError as exc:
        logger.error(
            "cannot connect to MQTT at %s:%d — %s",
            args.mqtt_host,
            args.mqtt_port,
            exc,
        )
        logger.info("will retry in 5 s …")
        while True:
            try:
                _connect_loop()
                break
            except OSError:
                logger.info("retrying …")
                time.sleep(5)

    logger.complete()
    logger.info("ready. listening for HA commands …")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("shutting down …")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
