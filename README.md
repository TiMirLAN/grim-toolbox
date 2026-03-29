[![Build extip-rust](https://github.com/TiMirLAN/grim-toolbox/actions/workflows/extip-rust.yml/badge.svg)](https://github.com/TiMirLAN/grim-toolbox/actions/workflows/extip-rust.yml)

# grim-toolbox

A collection of CLI tools and utilities for various tasks.

## Projects

### apps/extip-python

CLI service for polybar to show external IP address.

- **Language**: Python 3.13+
- **Build System**: Moon + uv
- **Documentation**: [apps/extip-python/README.md](apps/extip-python/README.md)

### apps/extip-rust

Rust implementation of extip.

- **Language**: Rust
- **Build System**: Cargo
- **Installation (Arch Linux)**:

  With yay:

  ```bash
  yay -U --noconfirm "https://github.com/TiMirLAN/grim-toolbox/releases/download/extip-v<VERSION>/extip-rust-<VERSION>-1-x86_64.pkg.tar.zst"
  ```

  Replace `<VERSION>` with the latest version from `apps/extip-rust/Cargo.toml`.

### scripts/modelloader

CLI tool for managing and loading models from various LLM providers through OpenAI-compatible APIs.

- **Language**: Python 3.14+
- **Documentation**: [scripts/modelloader/README.md](scripts/modelloader/README.md)

**Supported Providers:**
- RouterAI
- NeuroAPI
- Caila.io
- AgentPlatform

## Quick Start

### Using Moon

```bash
# Run a task defined in moon.yml
moon run <task>
moon run <project>:<task>

# Build all projects
moon build

# Test all projects
moon test
```

### Using uv Directly

```bash
# Install dependencies
uv sync

# Run a script
uv run <command>
```

## Requirements

- Python 3.14+ (for modelloader)
- Python 3.13+ (for extip-python)
- Rust (for extip-rust)
- [Moon](https://moonrepo.dev) v2.0.4+
- [uv](https://github.com/astral-sh/uv) v0.10.9+

## Development

### Linting & Type Checking

```bash
# Run ruff linter
ruff check .
ruff check --fix .

# Run ruff formatter
ruff format .

# Run mypy type checker
mypy <module>
```

### Running All Checks

```bash
# Moon test suite
moon test

# Or manually
ruff check . && ruff format --check . && mypy .
```

## License

See individual project licenses for details.
