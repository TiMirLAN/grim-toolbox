# extip-rust

CLI service for polybar to show external IP address. Rust implementation with Unix socket communication.

## Features

- Fetches external IP from api.ipinfo.io
- Provides IP via Unix socket for polybar integration
- Automatic routing table monitoring for IP changes
- Caching disabled on errors - displays error status instead of stale data
- Support for custom output format templates

## Installation

### Arch Linux

Manually from GitHub releases:

```bash
curl -L -o /tmp/extip-rust.pkg.tar.zst "https://github.com/TiMirLAN/grim-toolbox/releases/download/extip-v2.0.4/extip-rust-2.0.4-1-x86_64.pkg.tar.zst"
sudo pacman -U /tmp/extip-rust.pkg.tar.zst
```

### Build from source

```bash
cargo build --release
sudo install -Dm755 target/release/extip-rust /usr/bin/extip-rust
```

## Usage

### Service

Start the service:

```bash
extip-rust service
```

With custom token (optional):

```bash
extip-rust service --token YOUR_TOKEN
```

View help:

```bash
extip-rust service --help
```

### Client

Get current IP:

```bash
extip-rust client
```

Custom output format:

```bash
extip-rust client -i "{info.country} - {info.ip}"
```

Error format:

```bash
extip-rust client -e "{error_type}"
```

## Polybar Integration

1. Add to polybar config:

```ini
[module/extip]
type = custom/script
exec = extip-rust client
interval = 30
```

2. The service must be running in the background:

```bash
extip-rust service &
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EXTIP_INFO_FORMAT` | Output format for IP info | `{info.asn} {info.ip}` |
| `EXTIP_ERROR_FORMAT` | Output format for errors | `{error_type}` |
| `EXTIP_LOG_FILE` | Path to log file | `~/.local/share/extip/client.log` |

### Format Placeholders

Available placeholders for `info_format`:

- `{info.ip}` - External IP address
- `{info.asn}` - ASN (e.g., AS15169)
- `{info.as_name}` - ASN name (e.g., Google LLC)
- `{info.as_domain}` - ASN domain (e.g., google.com)
- `{info.country_code}` - Country code (e.g., US)
- `{info.country}` - Country name (e.g., United States)
- `{info.continent_code}` - Continent code (e.g., NA)
- `{info.continent}` - Continent name (e.g., North America)

Available placeholders for `error_format`:

- `{error_type}` - Error type (e.g., "No Internet", "Timeout", "Response Error")
- `{message}` - Full error message

## Error Types

| Type | Description |
|------|-------------|
| Response Error | HTTP status error (4xx, 5xx) |
| Timeout | Request timed out |
| No Internet | Connection refused / no network |
| Request Error | Invalid request |
| Network Error | Other network errors |
| Parse Error | JSON parsing failed |

## Systemd Service

Install the systemd service:

```bash
sudo cp extip.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable extip.service
sudo systemctl start extip.service
```

## Development

```bash
# Run tests
cargo test

# Build
cargo build

# Format
cargo fmt

# Lint
cargo clippy --fix --allow-dirty
```

### Release (using Moon)

```bash
# Generate changelog
moon run extip-rust:changelog

# Full release (check, build, changelog, commit, tag, push)
moon run extip-rust:release
```

The changelog is generated from commits since the last release tag using opencode for AI-powered analysis.

## License

MIT
