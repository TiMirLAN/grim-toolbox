import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent))

from modelloader import cli


@pytest.fixture(autouse=True)
def cleanup_json_files():
    """Cleanup JSON files created during tests."""
    test_files = [
        "RouterAI.models.json",
        "NeuroAPI.models.json",
        "Cailaio.models.json",
        "AgentPlatform.models.json",
    ]
    yield
    for filename in test_files:
        path = Path(filename)
        if path.exists():
            path.unlink()
        data_dir = Path("data")
        if data_dir.exists():
            data_file = data_dir / filename
            if data_file.exists():
                data_file.unlink()
                try:
                    data_dir.rmdir()
                except OSError:
                    pass


@pytest.fixture
def runner():
    """Fixture providing a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_auth_file():
    """Fixture providing a temporary auth file with mock credentials."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        auth_data = {
            "routerai": {"key": "test-routerai-key"},
            "neuroapis": {"key": "test-neuroapi-key"},
            "caila-oai": {"key": "test-caila-key"},
            "agentplatform": {"key": "test-agentplatform-key"},
        }
        json.dump(auth_data, f)
        temp_path = f.name

    yield temp_path

    os.unlink(temp_path)


@pytest.fixture
def mock_auth_path(mock_auth_file):
    """Fixture that mocks the auth file path."""
    with patch("modelloader.os.path.expanduser") as mock_expand:
        mock_expand.return_value = mock_auth_file
        yield mock_auth_file


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_cli_help(self, runner):
        """Test that main CLI help works."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "CLI для управления моделями" in result.output

    def test_models_help(self, runner):
        """Test that models command help works."""
        result = runner.invoke(cli, ["models", "--help"])
        assert result.exit_code == 0
        assert "список моделей" in result.output.lower()
        assert "--provider" in result.output
        assert "--dump" in result.output
        assert "--json" in result.output

    def test_providers_help(self, runner):
        """Test that providers command help works."""
        result = runner.invoke(cli, ["providers", "--help"])
        assert result.exit_code == 0
        assert "провайдер" in result.output.lower()
        assert "--provider" in result.output
        assert "--json" in result.output


class TestModelsCommand:
    """Tests for the models CLI command."""

    def test_models_command_basic(self, runner, mock_auth_path):
        """Test basic models command execution."""
        with patch("modelloader.requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {"id": "gpt-4", "object": "model"},
                    {"id": "gpt-3.5-turbo", "object": "model"},
                ]
            }
            mock_session.get.return_value = mock_response

            result = runner.invoke(cli, ["models"])

            assert result.exit_code == 0

    def test_models_with_json_output(self, runner, mock_auth_path):
        """Test models command with JSON output flag."""
        with patch("modelloader.requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"id": "gpt-4", "object": "model"}]
            }
            mock_session.get.return_value = mock_response

            result = runner.invoke(cli, ["models", "--json"])

            assert result.exit_code == 0
            json_start = result.output.find("{")
            output_data = json.loads(result.output[json_start:])
            assert isinstance(output_data, dict)

    def test_models_with_provider_filter(self, runner, mock_auth_path):
        """Test models command with provider filter."""
        with patch("modelloader.requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"id": "gpt-4", "object": "model"}]
            }
            mock_session.get.return_value = mock_response

            result = runner.invoke(cli, ["models", "--provider", "RouterAI"])

            assert result.exit_code == 0

    def test_models_with_invalid_provider(self, runner, mock_auth_path):
        """Test models command with invalid provider."""
        result = runner.invoke(cli, ["models", "--provider", "InvalidProvider"])

        assert result.exit_code == 0
        assert (
            "не найден" in result.output.lower() or "not found" in result.output.lower()
        )

    def test_models_with_dump_flag(self, runner, mock_auth_path, tmp_path):
        """Test models command with --dump flag."""
        with patch("modelloader.os.path.dirname") as mock_dirname:
            mock_dirname.return_value = str(tmp_path)

            with patch("modelloader.requests.Session") as mock_session_class:
                mock_session = MagicMock()
                mock_session_class.return_value = mock_session

                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "data": [{"id": "gpt-4", "object": "model"}]
                }
                mock_session.get.return_value = mock_response

                result = runner.invoke(cli, ["models", "--dump"])

                assert result.exit_code == 0


class TestProvidersCommand:
    """Tests for the providers CLI command."""

    def test_providers_command_basic(self, runner, mock_auth_path):
        """Test basic providers command execution."""
        result = runner.invoke(cli, ["providers"])

        assert result.exit_code == 0
        assert "RouterAI" in result.output
        assert "NeuroAPI" in result.output
        assert "Caila" in result.output
        assert "AgentPlatform" in result.output

    def test_providers_with_json_output(self, runner, mock_auth_path):
        """Test providers command with JSON output flag."""
        result = runner.invoke(cli, ["providers", "--json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert "RouterAI" in output_data
        assert "NeuroAPI" in output_data

    def test_providers_with_provider_filter(self, runner, mock_auth_path):
        """Test providers command with specific provider filter."""
        result = runner.invoke(cli, ["providers", "--provider", "RouterAI"])

        assert result.exit_code == 0
        assert "RouterAI" in result.output

    def test_providers_with_invalid_provider(self, runner, mock_auth_path):
        """Test providers command with invalid provider."""
        result = runner.invoke(cli, ["providers", "--provider", "InvalidProvider"])

        assert result.exit_code == 0
        assert (
            "не найден" in result.output.lower() or "not found" in result.output.lower()
        )


class TestProviderClasses:
    """Tests for provider classes."""

    def test_routerai_provider_properties(self):
        """Test RouterAI provider properties."""
        from modelloader import RouterAIProvider

        provider = RouterAIProvider()
        assert provider.name == "RouterAI"
        assert provider.base_url == "https://routerai.ru/api/v1"

    def test_neuroapi_provider_properties(self):
        """Test NeuroAPI provider properties."""
        from modelloader import NeuroAPIProvider

        provider = NeuroAPIProvider()
        assert provider.name == "NeuroAPI"
        assert provider.base_url == "https://neuroapi.host/v1"

    def test_caila_provider_properties(self):
        """Test Caila provider properties."""
        from modelloader import CailaProvider

        provider = CailaProvider()
        assert provider.name == "Caila.io"
        assert provider.base_url == "https://caila.io/api/adapters/openai-direct"

    def test_agentplatform_provider_properties(self):
        """Test AgentPlatform provider properties."""
        from modelloader import AgentPlatformProvider

        provider = AgentPlatformProvider()
        assert provider.name == "AgentPlatform"
        assert provider.base_url == "https://litellm.tokengate.ru/v1"


class TestProviderIntegration:
    """Integration tests for provider functionality."""

    def test_get_api_key_returns_key(self, mock_auth_path):
        """Test that get_api_key returns the API key."""
        from modelloader import RouterAIProvider

        provider = RouterAIProvider()
        api_key = provider.get_api_key()

        assert api_key == "test-routerai-key"

    def test_get_api_key_no_auth_file(self):
        """Test get_api_key when auth file doesn't exist."""
        with patch("modelloader.os.path.expanduser") as mock_expand:
            mock_expand.return_value = "/nonexistent/path/auth.json"

            from modelloader import RouterAIProvider

            provider = RouterAIProvider()
            api_key = provider.get_api_key()

            assert api_key is None

    def test_fetch_models_success(self, mock_auth_path):
        """Test successful model fetching."""
        from modelloader import RouterAIProvider

        provider = RouterAIProvider()

        with patch.object(provider.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"id": "gpt-4"}, {"id": "gpt-3.5-turbo"}]
            }
            mock_get.return_value = mock_response

            models = provider.fetch_models()

            assert models is not None
            assert len(models) == 2
            assert models[0]["id"] == "gpt-4"

    def test_fetch_models_timeout(self, mock_auth_path):
        """Test model fetching with timeout error."""
        import requests

        from modelloader import RouterAIProvider

        provider = RouterAIProvider()

        with patch.object(provider.session, "get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Timeout")

            models = provider.fetch_models()

            assert models is None

    def test_fetch_models_request_exception(self, mock_auth_path):
        """Test model fetching with request exception."""
        import requests

        from modelloader import RouterAIProvider

        provider = RouterAIProvider()

        with patch.object(provider.session, "get") as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException("Error")

            models = provider.fetch_models()

            assert models is None


class TestCLIErrorHandling:
    """Tests for CLI error handling."""

    def test_invalid_command(self, runner):
        """Test that invalid command shows error."""
        result = runner.invoke(cli, ["invalid-command"])

        assert (
            result.exit_code != 0
            or "Error" in result.output
            or "Unknown" in result.output
        )

    def test_models_no_auth(self, runner):
        """Test models command when no auth is available."""
        with patch("modelloader.os.path.expanduser") as mock_expand:
            mock_expand.return_value = "/nonexistent/auth.json"

            result = runner.invoke(cli, ["models"])

            assert result.exit_code == 0
