# Model Loader Script

A Python CLI tool for managing and loading models from various LLM providers through OpenAI-compatible APIs.

## Overview

The modelloader script provides a unified interface to fetch and manage models from multiple LLM providers:

- **RouterAI** - https://routerai.ru/api/v1
- **NeuroAPI** - https://neuroapi.host/v1
- **Caila.io** - https://caila.io/api/adapters/openai-direct
- **AgentPlatform** - https://litellm.tokengate.ru/v1

## Prerequisites

- Python 3.14+
- API keys for the providers (stored in `~/.local/share/opencode/auth.json`)

## Installation

The script uses [uv](https://github.com/astral-sh/uv) for dependency management. Dependencies are automatically installed when running through Moon.

## Usage

### Running the Script

```bash
# Using Moon (recommended)
moon run modelloader:run [COMMAND] [OPTIONS]

# Or directly with uv
uv run modelloader.py [COMMAND] [OPTIONS]
```

### Commands

#### `models` - List Models

Display models from all providers or filter by specific provider.

```bash
# List models from all providers
moon run modelloader:run -- models

# List models from specific provider
moon run modelloader:run -- models --provider RouterAI

# Save models to data directory
moon run modelloader:run -- models --dump

# Output models in JSON format
moon run modelloader:run -- models --json

# Combined options
moon run modelloader:run -- models --dump --json --provider RouterAI
```

**Options:**
- `--provider`: Filter models by provider (RouterAI, NeuroAPI, Caila.io, AgentPlatform)
- `--dump`: Save models to JSON files in the `data` directory
- `--json`: Output models in JSON format to stdout

#### `providers` - Provider Information

Display information about available providers.

```bash
# Show information about all providers
moon run modelloader:run -- providers

# Show information about specific provider
moon run modelloader:run -- providers --provider RouterAI

# Output provider info in JSON format
moon run modelloader:run -- providers --json
```

**Options:**
- `--provider`: Filter by specific provider
- `--json`: Output provider information in JSON format

### Authentication

The script expects API keys to be stored in `~/.local/share/opencode/auth.json` with the following structure:

```json
{
  "routerai": {
    "key": "your-routerai-api-key"
  },
  "neuroapis": {
    "key": "your-neuroapi-api-key"
  },
  "caila-oai": {
    "key": "your-caila-api-key"
  },
  "agentplatform": {
    "key": "your-agentplatform-api-key"
  }
}
```

### Output Examples

#### Models Command (Default)

```
--- Получаем модели от RouterAI ---
✓ Модели сохранены в RouterAI.models.json
Первые 3 модели (RouterAI):
[{'id': 'model1', 'object': 'model'}, ...]

--- Получаем модели от NeuroAPI ---
⚠️ Список моделей пуст для NeuroAPI

==================================================
ФИНАЛЬНЫЙ ОТЧЁТ
==================================================
RouterAI: Найдено моделей: 5
NeuroAPI: Список пуст
Caila.io: Ошибка/Нет данных
AgentPlatform: Найдено моделей: 3
```

#### Models Command (JSON Output)

```bash
moon run modelloader:run -- models --json
```

```json
{
  "RouterAI": [
    {"id": "model1", "object": "model"},
    {"id": "model2", "object": "model"}
  ],
  "NeuroAPI": "Список пуст",
  "Caila.io": "Ошибка/Нет данных",
  "AgentPlatform": [
    {"id": "model3", "object": "model"}
  ]
}
```

#### Providers Command (JSON Output)

```bash
moon run modelloader:run -- providers --json
```

```json
{
  "RouterAI": {
    "name": "RouterAI",
    "base_url": "https://routerai.ru/api/v1",
    "api_key": "Доступен"
  },
  "NeuroAPI": {
    "name": "NeuroAPI",
    "base_url": "https://neuroapi.host/v1",
    "api_key": "Не найден"
  },
  "Caila.io": {
    "name": "Caila.io",
    "base_url": "https://caila.io/api/adapters/openai-direct",
    "api_key": "Доступен"
  },
  "AgentPlatform": {
    "name": "AgentPlatform",
    "base_url": "https://litellm.tokengate.ru/v1",
    "api_key": "Доступен"
  }
}
```

### File Structure

```
scripts/modelloader/
├── modelloader.py          # Main script
├── moon.yaml              # Moon configuration
├── data/                  # Directory for dumped JSON files (created automatically)
│   ├── RouterAI.models.json
│   ├── NeuroAPI.models.json
│   ├── Cailaio.models.json
│   └── AgentPlatform.models.json
└── README.md              # This file
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**: Ensure your API keys are correctly stored in `~/.local/share/opencode/auth.json`
2. **Network Errors**: Check your internet connection and provider API endpoints
3. **Permission Errors**: Ensure the script has write permissions for the data directory

### Error Messages

- `❌ Ошибка при получении моделей от [provider]`: Network or API error occurred
- `⚠️ Список моделей пуст для [provider]`: Provider returned no models
- `Провайдер '[name]' не найден`: Invalid provider name specified

## Development

### Dependencies

The script requires:
- `requests`: For HTTP requests to provider APIs
- `click`: For CLI interface

Dependencies are managed through the script's shebang and uv.

### Adding New Providers

To add a new provider:

1. Create a new class extending `BaseProvider`
2. Set the `NAME`, `BASE_URL`, and `AUTH_OPENJSON_ID` attributes
3. Add the provider to the lists in both `models()` and `providers()` functions

### Contributing

1. Follow the existing code style and naming conventions
2. Add appropriate documentation for new features
3. Test with all available providers when making changes

## License

This script is part of the grim-toolbox project. Please refer to the main project license for details.
