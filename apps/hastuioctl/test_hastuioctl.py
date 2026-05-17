"""
Tests for hastuioctl core logic: templates, YAML loader, matching, actions.

Run with:
    cd apps/hastuioctl
    uv run pytest test_hastuioctl.py -v
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import hastuioctl as _mod
from hastuioctl import (
    Action,
    Trigger,
    build_context,
    load_events,
    match_trigger,
    render,
    run_action,
)

# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def tmp_events(tmp_path: Path) -> Path:
    cfg = tmp_path / "events.yaml"
    cfg.write_text(
        "events:\n"
        '  - topic: "ha/audio/command"\n'
        '    trigger:\n'
        '      command: "play"\n'
        '    action:\n'
        '      description: Play\n'
        '      command: "playerctl"\n'
        '      args: ["play"]\n'
        '  - topic: "ha/audio/command"\n'
        '    trigger:\n'
        '      command: "volume"\n'
        '    action:\n'
        '      description: Volume\n'
        '      command: "pactl"\n'
        '      args:\n'
        '        - "set-sink-volume"\n'
        '        - "@DEFAULT_SINK@"\n'
        '        - "{{ params }}"\n'
        '  - topic: "ha/audio/tts"\n'
        '    trigger:\n'
        '      text: "."\n'
        '    action:\n'
        '      description: TTS\n'
        '      command: "espeak"\n'
        '      env:\n'
        '        VOICE: "{{ params.voice | default \'\' }}"  \n'
    )
    return cfg


# ── render() tests ──────────────────────────────────────────────────

class TestRender:
    def test_simple_params(self):
        ctx = {"params": 75}
        assert render("{{ params }}", ctx) == "75"

    def test_params_nested_key(self):
        ctx = {"params": {"url": "https://example.com/track.mp3"}}
        assert render("{{ params.url }}", ctx) == "https://example.com/track.mp3"

    def test_default_absent(self):
        ctx = {"params": {}}
        assert render("{{ params.delta | default 5 }}", ctx) == "5"

    def test_default_present(self):
        ctx = {"params": {"delta": 3}}
        assert render("{{ params.delta | default 5 }}", ctx) == "3"

    def test_no_placeholders(self):
        assert render("static text", {}) == "static text"

    def test_empty_str_when_null(self):
        ctx = {"other": "value"}
        assert render("{{ params.missing }}", ctx) == ""

    def test_multiple_placeholders(self):
        ctx = {"params": {"a": "A", "b": "B"}}
        res = render("{{ params.a }} + {{ params.b }}", ctx)
        assert res == "A + B"


# ── match_trigger() tests ───────────────────────────────────────────

class TestMatchTrigger:
    def test_command_exact_match(self):
        t = Trigger(command="play")
        assert match_trigger(t, {"command": "play"}) is True
        assert match_trigger(t, {"command": "pause"}) is False
        assert match_trigger(t, {}) is False
        assert match_trigger(t, {"command": None}) is False

    def test_text_regex_match(self):
        t = Trigger(text="hello")
        assert match_trigger(t, {"params": {"text": "say hello world"}}) is True
        assert match_trigger(t, {"params": {"text": "goodbye"}}) is False
        assert match_trigger(t, {"params": "string"}) is False
        assert match_trigger(t, {"params": None}) is False

    def test_extra_keys(self):
        t = Trigger(command="cmd", extra={"source": "ha"})
        assert match_trigger(t, {"command": "cmd", "source": "ha"}) is True
        assert match_trigger(t, {"command": "cmd", "source": "other"}) is False

    def test_trigger_with_only_command(self):
        t = Trigger(command="stop")
        assert match_trigger(t, {"command": "stop", "params": 50}) is True

    def test_command_and_text_both_checked(self):
        """When trigger has both command and text, BOTH must match (AND logic)."""
        t = Trigger(command="cmd2", text="hello")
        # both match
        assert match_trigger(
            t, {"command": "cmd2", "params": {"text": "hello"}}
        ) is True
        # command mismatch → false
        assert match_trigger(
            t, {"command": "cmd1", "params": {"text": "hello"}}
        ) is False
        # text mismatch → false
        assert match_trigger(
            t, {"command": "cmd2", "params": {"text": "goodbye"}}
        ) is False


# ── load_events() tests ─────────────────────────────────────────────

class TestLoadEvents:
    def test_load_empty(self, tmp_path: Path):
        cfg = tmp_path / "empty.yaml"
        cfg.write_text("events: []\n")
        assert load_events(str(cfg)) == []

    def test_load_single(self, tmp_events: Path):
        events = load_events(str(tmp_events))
        assert len(events) == 3

    def test_load_sets_fields(self, tmp_events: Path):
        events = load_events(str(tmp_events))
        first = events[0]
        assert first.topic == "ha/audio/command"
        assert first.trigger.command == "play"
        assert first.trigger.text is None
        assert first.action.description == "Play"
        assert first.action.command == "playerctl"
        assert first.action.args == ["play"]
        assert first.action.publish_reply_to is None

    def test_load_volume_has_template(self, tmp_events: Path):
        events = load_events(str(tmp_events))
        vol = events[1]
        assert vol.trigger.command == "volume"
        assert "{{ params }}" in vol.action.args[2]

    def test_load_tts_has_env(self, tmp_events: Path):
        events = load_events(str(tmp_events))
        tts = events[2]
        assert tts.trigger.text == "."
        assert tts.action.env == {"VOICE": "{{ params.voice | default '' }}"}

    def test_load_missing_action_keys(self, tmp_path: Path):
        cfg = tmp_path / "minimal.yaml"
        cfg.write_text(
            "events:\n"
            '  - topic: "test"\n'
            '    trigger: {}\n'
            "    action:\n"
            '      command: "echo"\n'
        )
        events = load_events(str(cfg))
        assert len(events) == 1
        assert events[0].topic == "test"
        assert events[0].action.command == "echo"
        assert events[0].action.args == []
        assert events[0].action.description == ""


# ── build_context() tests ───────────────────────────────────────────

class TestBuildContext:
    def test_basic(self):
        ctx = build_context(75, "volume")
        assert ctx == {"params": 75, "command": "volume"}

    def test_none_params(self):
        ctx = build_context(None, "play")
        assert ctx == {"params": {}, "command": "play"}

    def test_no_command(self):
        ctx = build_context({"x": 1})
        assert ctx == {"params": {"x": 1}}


# ── run_action() tests ──────────────────────────────────────────────

class TestRunAction:
    def test_runs_command(self):
        action = Action(
            command="echo",
            args=["hello"],
            description="test echo",
        )
        result = run_action(
            action,
            {"command": "test", "params": {}},
            mqtt_client=None,
        )
        assert result == "hello\n"

    def test_rendered_args_substituted(self):
        action = Action(
            command="echo",
            args=["vol:", "{{ params.level }}"],
            description="test render",
        )
        result = run_action(
            action,
            {"command": "set", "params": {"level": 80}},
            mqtt_client=None,
        )
        assert "80" in result

    def test_default_renders(self):
        action = Action(
            command="echo",
            args=["{{ params.delta | default 5 }}"],
        )
        result = run_action(
            action,
            {"command": "up", "params": {}},
            mqtt_client=None,
        )
        assert "5" in result

    def test_env_merged(self):
        """Verify env vars from the action are merged into subprocess."""
        action = Action(
            command="bash",
            args=["-c", "echo $HASTUIOCTL_TEST_MARKER"],
            env={"HASTUIOCTL_TEST_MARKER": "exists"},
        )
        result = run_action(
            action,
            {"command": "test", "params": {}},
            mqtt_client=None,
        )
        assert "exists" in result

    def test_binary_not_found(self):
        action = Action(
            command="/no/such/binary",
            args=["arg"],
            description="missing bin",
        )
        result = run_action(
            action,
            {"command": "x", "params": {}},
            mqtt_client=None,
        )
        assert result is None

    def test_timeout(self):
        action = Action(
            command="sleep",
            args=["60"],
            description="timeout test",
        )
        result = run_action(
            action,
            {"command": "test", "params": {}},
            mqtt_client=None,
        )
        assert result is None

    @patch.object(_mod, "mqtt")
    def test_publishes_reply(self, mock_mqtt):
        mock_client = MagicMock()
        mock_client.publish = MagicMock()

        action = Action(
            command="echo",
            args=["metadata"],
            publish_reply_to="ha/audio/status",
        )

        run_action(
            action,
            {"command": "status", "params": {}},
            mqtt_client=mock_client,
        )

        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        assert call_args[0][0] == "ha/audio/status"
        reply = json.loads(call_args[0][1])
        assert reply["status"] == "ok"
        assert "metadata" in reply["data"]


# ── Integration flow tests ──────────────────────────────────────────

class TestFlow:
    def test_play_event_flow(self, tmp_events: Path):
        events = load_events(str(tmp_events))
        assert len(events) == 3

        match = [e for e in events if e.trigger.command == "play"][0]
        assert match.trigger.command == "play"

        ctx = _mod.build_context({}, "play")
        rendered = [_mod.render(a, ctx) for a in match.action.args]
        assert rendered == ["play"]

    def test_volume_event_flow(self, tmp_events: Path):
        events = load_events(str(tmp_events))
        match = [e for e in events if e.trigger.command == "volume"][0]

        ctx = _mod.build_context(85, "volume")
        rendered = [_mod.render(a, ctx) for a in match.action.args]
        assert rendered == ["set-sink-volume", "@DEFAULT_SINK@", "85"]
