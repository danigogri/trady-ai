# Trady.AI

Universal Deterministic Financial Intelligence Infrastructure.

## Quick Start

```bash
# Install the package in development mode with dev dependencies
pip install -e ".[dev]"

# Verify the installation
trady-ai --help
```

## Directory Structure

```
src/trady_ai/
├── __init__.py          # Package entry point, exposes __version__
├── adapters/            # Platform Integration (Fase 2)
├── cli/                 # CLI commands (Click group)
├── config/              # Centralized settings (pydantic-settings)
├── core/                # Deterministic Core (Fase 1)
├── db/                  # SQLite database (sqlite-utils)
├── governance/          # Governance Hardening (Fase 7)
├── reflection/          # Reflection Systems (Fase 4)
├── security/            # Secrets validation, file permissions
└── strategies/          # Strategy Infrastructure (Fase 3)
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
└── integration/         # Integration tests
```

## CLI Commands

```bash
# Show help
trady-ai --help

# Show system status and configuration
trady-ai status

# Analyze a market (placeholder)
trady-ai analyze --market btc
```

## Environment Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### Security Warning

**Never commit `.env` to version control.** The `.env` file contains sensitive
configuration (API keys, secrets) and is explicitly excluded via `.gitignore`.
Always use `.env.example` as the template for documentation purposes only.

## Development

```bash
# Run tests with coverage
pytest

# Lint with ruff
ruff check .

# Type check with mypy
mypy src/
```
