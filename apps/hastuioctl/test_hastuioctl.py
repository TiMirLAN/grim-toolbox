"""
Tests for hastuioctl core logic: templates, YAML loader, matching, actions.

Run with:
    cd apps/hastuioctl
    uv run pytest test_hastuioctl.py -v
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import hastuioctl as _mod
from hastuioctl import Action, Event, Trigger, load_config, render

# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def tmp_events(tmp_path: Path) -> Path:
    """YAML with single 'action' key (backward compat tested separately)."""
    cfg = tmp_path / "events.yaml"
    cfg.write_text(
        "events:\n"
        '  - topic: "ha/audio/command"\n'
        '    trigger:\n'
        '      command: "play"\n'
        '    actions:\n'
        '      - description: Play\n'
        '        command: "playerctl"\n'
        '        args: ["play"]\n'
        '  - topic: "ha/audio/command"\n'
        '    trigger:\n'
        '      command: "volume"\n'
        '    actions:\n'
        '      - description: Volume\n'
        '        command: "pactl"\n'
        '        args:\n'
        '          - "set-sink-volume"\n'
        '          - "@DEFAULT_SINK@"\n'
        '          - "{{ params }}"\n'
        '  - topic: "ha/audio/tts"\n'
        '    trigger:\n'
        '      text: "."\n'
        '    actions:\n'
        '      - description: TTS\n'
        '        command: "espeak"\n'
        '        env:\n'
        '          VOICE: "{{ params.voice | default \'\' }}"  \n'
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
        assert render("{{ params.a }} + {{ params.b }}", ctx) == "A + B"


# ── Trigger.match() tests ───────────────────────────────────────────

class TestMatchTrigger:
    def test_command_exact_match(self):
        t = Trigger(command="play")
        assert t.match({"command": "play"}) is True
        assert t.match({"command": "pause"}) is False
        assert t.match({}) is False
        assert t.match({"command": None}) is False

    def test_text_regex_match(self):
        t = Trigger(text="hello")
        assert t.match({"params": {"text": "say hello world"}}) is True
        assert t.match({"params": {"text": "goodbye"}}) is False
        assert t.match({"params": "string"}) is False
        assert t.match({"params": None}) is False

    def test_extra_keys_via_pydantic_extra_forbid(self):
        """Trigger uses extra='forbid' — unknown keys raise ValueError."""
        with pytest.raises(Exception):  # ValidationError
            Trigger(command="cmd", source="ha")

    def test_trigger_with_only_command(self):
        t = Trigger(command="stop")
        assert t.match({"command": "stop", "params": 50}) is True

    def test_command_and_text_both_checked(self):
        """Both must pass (AND logic)."""
        t = Trigger(command="cmd2", text="hello")
        assert t.match({"command": "cmd2", "params": {"text": "hello"}}) is True
        assert t.match({"command": "cmd1", "params": {"text": "hello"}}) is False
        assert t.match({"command": "cmd2", "params": {"text": "goodbye"}}) is False


# ── load_events() / Config tests ────────────────────────────────────

class TestLoadEvents:
    def test_load_empty(self, tmp_path: Path):
        cfg = tmp_path / "empty.yaml"
        cfg.write_text("events: []\n")
        config = load_config(str(cfg))
        assert config.events == []

    def test_load_single(self, tmp_events: Path):
        config = load_config(str(tmp_events))
        assert len(config.events) == 3

    def test_load_sets_fields(self, tmp_events: Path):
        config = load_config(str(tmp_events))
        first = config.events[0]
        assert first.topic == "ha/audio/command"
        assert first.trigger.command == "play"
        assert first.trigger.text is None
        # actions is now a list
        assert len(first.actions) == 1
        assert first.actions[0].description == "Play"
        assert first.actions[0].command == "playerctl"
        assert first.actions[0].args == ["play"]
        assert first.actions[0].publish_reply_to is None

    def test_load_volume_has_template(self, tmp_events: Path):
        config = load_config(str(tmp_events))
        vol = config.events[1]
        assert vol.trigger.command == "volume"
        assert "{{ params }}" in vol.actions[0].args[2]

    def test_load_tts_has_env(self, tmp_events: Path):
        config = load_config(str(tmp_events))
        tts = config.events[2]
        assert tts.trigger.text == "."
        assert tts.actions[0].env == {"VOICE": "{{ params.voice | default '' }}"}

    def test_load_missing_action_keys(self, tmp_path: Path):
        cfg = tmp_path / "minimal.yaml"
        cfg.write_text(
            "events:\n"
            '  - topic: "test"\n'
            '    trigger: {}\n'
            '    action:\n'
            '      command: "echo"\n'
        )
        config = load_config(str(cfg))
        assert len(config.events) == 1
        assert config.events[0].topic == "test"
        assert config.events[0].actions[0].command == "echo"
        assert config.events[0].actions[0].args == []
        assert config.events[0].actions[0].description == ""

    def test_backward_compat_single_action(self, tmp_path: Path):
        """'action' (singular) should be auto-converted to 'actions' list."""
        cfg = tmp_path / "compat.yaml"
        cfg.write_text(
            "events:\n"
            '  - topic: "test"\n'
            '    trigger: {}\n'
            '    action:\n'
            '      command: "echo"\n'
        )
        config = load_config(str(cfg))
        assert len(config.events) == 1
        assert len(config.events[0].actions) == 1
        assert config.events[0].actions[0].command == "echo"


# ── _execute_action() tests ────────────────────────────────────────

class TestExecuteAction:
    def test_runs_command(self):
        from hastuioctl import _execute_action
        action = Action(command="echo", args=["hello"])
        result = _execute_action(action, {"command": "test", "params": {}})
        assert result == "hello\n"

    def test_rendered_args_substituted(self):
        from hastuioctl import _execute_action
        action = Action(command="echo", args=["vol:", "{{ params.level }}"])
        result = _execute_action(
            action, {"command": "set", "params": {"level": 80}}
        )
        assert "80" in result

    def test_default_renders(self):
        from hastuioctl import _execute_action
        action = Action(command="echo", args=["{{ params.delta | default 5 }}"])
        result = _execute_action(action, {"command": "up", "params": {}})
        assert "5" in result

    def test_env_merged(self):
        from hastuioctl import _execute_action
        action = Action(
            command="sh",
            args=["-c", "echo $HASTUIOCTL_TEST_MARKER"],
            env={"HASTUIOCTL_TEST_MARKER": "exists"},
        )
        result = _execute_action(action, {"command": "test", "params": {}})
        assert "exists" in result

    def test_binary_not_found(self):
        from hastuioctl import _execute_action
        action = Action(command="/no/such/binary", args=["arg"])
        result = _execute_action(action, {"command": "x", "params": {}})
        assert result is None

    def test_timeout_mocked(self):
        from hastuioctl import _execute_action
        action = Action(command="sleep", args=["9999"])
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("sleep", 30),
        ):
            result = _execute_action(action, {"command": "test", "params": {}})
        assert result is None

    @patch.object(_mod, "mqtt")
    def test_publishes_reply_via_mqtt_handler(self, mock_mqtt):
        from hastuioctl import _mqtt_handler
        mock_client = MagicMock()
        mock_client.publish = MagicMock()

        action = Action(
            command="echo",
            args=["metadata"],
            publish_reply_to="ha/audio/status",
        )
        event = Event(topic="t", trigger=Trigger(command="status"), actions=[action])

        class FakeMsg:
            topic = "t"
            payload = b'{"command": "status", "params": {}}'

        _mqtt_handler(FakeMsg(), [event], mock_client)
        mock_client.publish.assert_called_once()
        call_args = mock_client.publish.call_args
        assert call_args[0][0] == "ha/audio/status"
        reply = json.loads(call_args[0][1])
        assert reply["status"] == "ok"
        assert "metadata" in reply["data"]


# ── Pydantic validation tests ───────────────────────────────────────

class TestPydanticValidation:
    def test_trigger_extra_forbid(self):
        """Unknown trigger keys should be rejected by Pydantic."""
        with pytest.raises(Exception):  # ValidationError
            Trigger(command="play", unknown_key="value")

    def test_config_missing_events(self, tmp_path: Path):
        """Config.model_validate handles empty/None input gracefully."""
        cfg = tmp_path / "no_events.yaml"
        cfg.write_text("{}\n")
        config = load_config(str(cfg))
        assert len(config.events) == 0
