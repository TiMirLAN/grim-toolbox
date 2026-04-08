# Agent Guidelines for grim-toolbox

This document provides guidelines for agents working in this repository.

## Project Overview

- **Build System**: Moon (v2.0.4+)
- **Package Manager**: uv (v0.10.9+)
- **GitHub CLI**: gh (v2.89.0+)
- **Python Version**: >=3.13 (extip-python), >=3.14 (modelloader)
- **Rust**: Required for extip-rust project
- **Workspace**: Multi-project in `apps/*` and `scripts/*`
- **Default Branch**: master
- **VCS Provider**: GitHub

## Projects

### apps/extip-python
- CLI service for polybar to show external IP address
- Language: Python 3.13+
- Build: Moon + uv

### apps/extip-rust
- Rust implementation of extip
- Language: Rust
- Build: Cargo

### scripts/modelloader
- CLI tool for managing and loading models from LLM providers
- Language: Python 3.14+
- Build: Moon + uv

## Build Commands

### Moon Workspace Commands

```bash
# Run a task for a specific project
moon run <project>:<task>

# Build all projects
moon build

# Test all projects
moon test

# Clean build artifacts
moon clean

# List all projects
moon list

# Show project graph
moon graph
```

### Moon Project Tasks

#### extip-python Tasks

| Task | Command | Description |
|------|---------|-------------|
| `run.service` | `moon run extip-python:run.service` | Run the external IP service (requires `.env`) |
| `run.client` | `moon run extip-python:run.client` | Run the client CLI (requires `.env`) |
| `lint` | `moon run extip-python:lint` | Run ruff linter with auto-fix |
| `format` | `moon run extip-python:format` | Run pre-commit hooks |
| `test` | `moon run extip-python:test` | Run pytest test suite |
| `clean.dist` | `moon run extip-python:clean.dist` | Remove `dist/` directory contents |
| `build` | `moon run extip-python:build` | Build the package (depends on `clean.dist`) |
| `version` | `moon run extip-python:version` | Show current version |
| `publish` | `moon run extip-python:publish` | Publish to devpi-wrkst index (requires `.env`, depends on `build`) |

**Environment Files:**
- `run.service`, `run.client`, `publish` tasks use `.env` file
- Copy `template.env` to `.env` and configure as needed

#### extip-rust Tasks

| Task | Command | Description |
|------|---------|-------------|
| `run.service` | `moon run extip-rust:run.service` | Run the external IP service |
| `run.client` | `moon run extip-rust:run.client` | Run the client CLI |
| `lint` | `moon run extip-rust:lint` | Run clippy with auto-fix |
| `format` | `moon run extip-rust:format` | Format code with rustfmt |
| `test` | `moon run extip-rust:test` | Run cargo test suite |
| `clean` | `moon run extip-rust:clean` | Clean cargo build artifacts |
| `build` | `moon run extip-rust:build` | Build release binary |
| `pkgbuild` | `moon run extip-rust:pkgbuild` | Build Arch Linux package (PKGBUILD) |
| `version` | `moon run extip-rust:version` | Show cargo version |
| `changelog` | `moon run extip-rust:changelog` | Generate changelog from last tag to HEAD |
| `release` | `moon run extip-rust:release` | Build, create changelog, commit, tag and push |

#### modelloader Tasks

| Task | Command | Description |
|------|---------|-------------|
| `run` | `moon run modelloader:run` | Run the modelloader CLI |
| `test` | `moon run modelloader:test` | Run pytest with required dependencies |

### Using uv Directly (Python projects)

```bash
# Navigate to project directory
cd apps/extip-python

# Install dependencies
uv sync

# Add a dependency
uv add <package>
uv add -d <package>  # dev dependency

# Run a script
uv run <command>

# Lock dependencies
uv lock

# Build the project
uv build

# Publish to index
uv publish --index <index-name>
```

### Using Cargo (Rust projects)

```bash
# Navigate to project directory
cd apps/extip-rust

# Build the project
cargo build --release

# Run the project
cargo run -- [args]

# Run tests
cargo test

# Format code
cargo fmt

# Lint code
cargo clippy --fix --allow-dirty

# Clean build artifacts
cargo clean
```

### Running Single Tests

```bash
# For extip-python
cd apps/extip-python
pytest tests/test_utils.py::TestClass::test_method
pytest tests/test_utils.py -k "test_name"
uv run pytest tests/test_utils.py::test_function

# For modelloader
cd scripts/modelloader
uv run --with pytest --with click --with requests pytest tests/ -v
```

### Linting & Type Checking

```bash
# For extip-python
cd apps/extip-python
uv run ruff check --fix
uv run pre-commit run -c ./.pre-commit-config.yaml

# For modelloader
cd scripts/modelloader
ruff check .
ruff check --fix .
ruff format .

# For extip-rust
cd apps/extip-rust
cargo clippy --fix --allow-dirty
cargo fmt
```

### Running All Checks

```bash
# Moon test suite
moon test

# For extip-python
cd apps/extip-python
uv run pytest

# For modelloader
cd scripts/modelloader
uv run --with pytest --with click --with requests pytest tests/ -v

# For extip-rust
cd apps/extip-rust
cargo test
```

## Using GitHub CLI (gh)

GitHub CLI is used for GitHub-related operations including issues, pull requests, releases, and workflows.

```bash
# Authenticate with GitHub
gh auth login

# Check authenticated status
gh auth status

# Create a pull request
gh pr create --title "Title" --body "Description"

# List pull requests
gh pr list

# View pull request
gh pr view <pr-number>

# Create a release
gh release create <tag> --title "Release Title" --notes "Release notes"

# List releases
gh release list
```

### Running GitHub Actions Workflows

```bash
# List available workflows
gh workflow list

# Run a workflow manually
gh workflow run <workflow-name>

# Run workflow with inputs
gh workflow run <workflow-name> -f field=value -f another=value

# Run workflow from specific branch/tag
gh workflow run <workflow-name> --ref <branch-or-tag>

# View recent workflow runs
gh run list

# View runs for a specific workflow
gh run list --workflow=<workflow-name>

# View run status and logs
gh run view <run-id>

# View run logs (full log output)
gh run view <run-id> --log

# Download workflow artifacts
gh run download <run-id>

# Rerun a failed workflow
gh run rerun <run-id>

# Cancel a running workflow
gh run cancel <run-id>

# Wait for workflow to complete (exit with code)
gh run view <run-id> --exit-status && echo "Success" || echo "Failed"
```

**Example workflows in this repo:**
- `extip-rust.yml` - Build and test extip-rust
- `modelloader.yml` - Test modelloader

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
grim-toolbox/
├── apps/                    # Application projects
│   ├── extip-python/        # Python CLI for external IP service
│   │   ├── src/extip/       # Source code
│   │   ├── tests/           # Test files
│   │   ├── pyproject.toml   # Project configuration
│   │   ├── moon.yml         # Moon build config
│   │   └── README.md
│   └── extip-rust/          # Rust implementation
│       ├── src/             # Rust source code
│       ├── Cargo.toml       # Rust project config
│       ├── moon.yml         # Moon build config
│       └── PKGBUILD         # Arch Linux package build
├── scripts/                 # Standalone scripts
│   └── modelloader/         # Model loader CLI tool
│       ├── modelloader.py   # Main script
│       ├── tests/           # Test files
│       ├── moon.yaml        # Moon build config
│       └── README.md
├── .github/
│   └── workflows/           # GitHub Actions workflows
├── .moon/
│   └── workspace.yml        # Moon workspace configuration
├── AGENTS.md                # This file
└── README.md                # Project overview
```

### Configuration Files

When creating new configuration files:

- `pyproject.toml`: Define project metadata, dependencies, and tools (Python projects)
- `Cargo.toml`: Define Rust project metadata and dependencies (Rust projects)
- `moon.yml` / `moon.yaml`: Per-project build configuration
- `.pre-commit-config.yaml`: Pre-commit hooks configuration (extip-python)
- Use ruff for both linting and formatting (Python projects)
- Use clippy and rustfmt for Rust projects

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
