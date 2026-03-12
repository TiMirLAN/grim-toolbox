# Agent Guidelines for grim-toolbox

This document provides guidelines for agents working in this repository.

## Project Overview

- **Build System**: Moon (v2.0.4)
- **Package Manager**: uv (v0.10.9)
- **Python Version**: >=3.14
- **Workspace**: Multi-project in `apps/*`
- **Default Branch**: master

## Build Commands

### Using Moon

```bash
# Run a task defined in moon.yml
moon run <task>
moon run <project>:<task>

# Build all projects
moon build

# Test all projects
moon test

# Clean build artifacts
moon clean
```

### Using uv Directly

```bash
# Install dependencies
uv sync

# Add a dependency
uv add <package>
uv add -d <package>  # dev dependency

# Run a script
uv run <command>

# Lock dependencies
uv lock
```

### Running Single Tests

```bash
# With pytest (if configured)
pytest tests/<test_file>.py::TestClass::test_method
pytest tests/<test_file>.py -k "test_name"

# With uv run
uv run pytest tests/test_example.py::test_function

# With Python directly
python -m pytest tests/test_example.py::test_function
```

### Linting & Type Checking

```bash
# Run ruff linter
ruff check .
ruff check --fix .

# Run ruff formatter
ruff format .

# Run mypy type checker
mypy <module>
mypy --strict <module>
```

### Running All Checks

```bash
# Moon test suite
moon test

# Or manually
ruff check . && ruff format --check . && mypy .
```

## Code Style Guidelines

### General Principles

- Keep code clean, simple, and readable
- Write self-documenting code with descriptive names
- Use type hints for all function signatures
- Handle errors explicitly and provide meaningful messages

### Imports

```python
# Standard library first, then third-party, then local
import json
import os
from typing import Dict, List, Optional

import requests
from requests import Session

from mypackage import MyClass
from mypackage.submodule import another_module
```

- Use absolute imports (no relative imports like `from . import`)
- Group imports by type (stdlib, third-party, local)
- Sort imports alphabetically within groups
- Use `from x import y` for clarity when only specific items are needed

### Formatting

- Use 4 spaces for indentation (no tabs)
- Maximum line length: 120 characters
- Use Black formatting (integrated via ruff)
- Add trailing commas for multi-line collections

### Naming Conventions

- **Functions/variables**: `snake_case` (e.g., `get_api_key`, `fetch_models`)
- **Classes**: `PascalCase` (e.g., `ModelFetcher`, `APIClient`)
- **Constants**: `SCREAMING_SNAKE_CASE` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT`)
- **Private methods**: prefix with underscore (e.g., `_private_method`)
- **Modules**: `snake_case` (e.g., `model_loader.py`)

### Type Hints

- Always include return types for functions
- Use `Optional[X]` instead of `X | None` for compatibility
- Use `Dict`, `List`, `Tuple` from typing (not builtins)
- Use `Any` sparingly; prefer specific types

```python
# Good
def get_api_key(provider_name: str) -> Optional[str]:
    ...

def fetch_models(url: str, headers: Dict[str, str]) -> List[Dict]:
    ...

# Avoid
def get_key(name):  # No type hints
    ...

def process(data):  # Too generic
    ...
```

### Error Handling

- Use specific exception types
- Provide meaningful error messages in Russian (project uses Russian comments)
- Log errors appropriately (print for scripts, logging for libraries)
- Return `None` or raise specific exceptions rather than using generic ones

```python
# Good
try:
    with open(auth_path, "r") as f:
        data = json.load(f)
except FileNotFoundError as e:
    print(f"Файл не найден: {e}")
    return None
except json.JSONDecodeError as e:
    print(f"Ошибка парсинга JSON: {e}")
    return None

# Avoid bare except
try:
    ...
except:  # Too broad
    ...
```

### Docstrings

- Use Google-style or NumPy-style docstrings
- Include description, args, returns, raises
- Write in Russian or English (be consistent)

```python
def fetch_models(provider: str) -> Optional[List[Dict]]:
    """Получает список моделей от провайдера.

    Args:
        provider: Название провайдера (например, "RouterAI").

    Returns:
        Список моделей или None в случае ошибки.

    Raises:
        RequestException: При ошибке сети.
    """
    ...
```

### Testing

- Place tests in `tests/` directory
- Use `pytest` as the test runner
- Name test files as `test_<module>.py`
- Use descriptive test function names: `test_function_name_scenario`

```python
def test_fetch_models_returns_list_on_success():
    """Test that fetch_models returns a list when API responds successfully."""
    ...
```

### File Organization

```
project/
├── apps/              # Application code
│   └── <app_name>/
│       ├── app.py
│       └── config.py
├── scripts/           # Standalone scripts
│   └── modelloader/
│       └── modelloader.py
├── tests/             # Test files
│   └── test_example.py
├── pyproject.toml     # Project configuration
├── moon.yml           # Moon build config
└── AGENTS.md          # This file
```

### Configuration Files

When creating new configuration files:

- `pyproject.toml`: Define project metadata, dependencies, and tools
- `moon.yml`: Per-project build configuration
- Use ruff for both linting and formatting

### Git Conventions

- Make meaningful commit messages
- Keep commits atomic and focused
- Run lint checks before committing
- Do not commit secrets or credentials

### Security

- Never hardcode API keys or passwords
- Use environment variables or secure credential stores
- Validate and sanitize all user inputs
- Follow principle of least privilege

### Commit Message Notation

This project uses a specific commit message notation system for clear categorization:

- **`+`** - for additions (new features, new files, new functionality)
- **`~`** - for changes (modifications to existing code, refactoring, updates)
- **`!`** - for bug fixes (error corrections, issue resolutions)

Examples:
- `+ add user authentication system` - Adding new authentication feature
- `~ refactor database connection logic` - Modifying existing database code
- `! fix memory leak in data processing` - Fixing a memory leak bug

This notation helps quickly identify the nature of changes and maintain a consistent commit history.
