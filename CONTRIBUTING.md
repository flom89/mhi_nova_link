# Contributing to MHI Nova Link

Thank you for your interest in contributing! This document explains how to get started, run tests, and submit changes.

## Development Setup

### Prerequisites

- Python ≥ 3.12
- A working Home Assistant development environment (optional, required for manual testing)

### Install dependencies

```bash
pip install homeassistant pytest pytest-asyncio ruff mypy
```

### Running tests

All tests live in `custom_components/mhi_nova_link/tests/`.

```bash
# Run the full test suite from the repository root
pytest -q custom_components/mhi_nova_link/tests

# Run a specific test file
pytest custom_components/mhi_nova_link/tests/test_api_normalizers.py -v
```

## Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
# Check for issues
ruff check custom_components/mhi_nova_link/

# Auto-fix import ordering and safe fixable issues
ruff check --fix custom_components/mhi_nova_link/
```

## Type Checking

```bash
mypy custom_components/mhi_nova_link/
```

## CI

GitHub Actions runs on every push and pull request:

- **test** — installs dependencies and runs `pytest`
- **lint** — runs `ruff check`
- **type-check** — runs `mypy`
- **validate-hacs** — runs HACS validation
- **validate (hassfest)** — runs Home Assistant hassfest

All checks must pass before a PR can be merged.

## Pull Request Process

1. Fork the repository and create a feature branch from `main`.
2. Make your changes with clear, focused commits.
3. Add or update tests for any changed behaviour. New features must include tests.
4. Ensure all CI checks pass locally before pushing.
5. Open a pull request targeting `main`. Fill out the PR description explaining what changed and why.
6. A maintainer will review and may request changes before merging.

## Branching

- `main` — stable, release-ready code
- Feature branches: `feature/<short-description>` or `fix/<short-description>`

## Versioning

This project follows [Semantic Versioning](https://semver.org/). The version must be kept in sync across:

- `custom_components/mhi_nova_link/manifest.json` (`version` field)
- `custom_components/mhi_nova_link/pyproject.toml` (`version` field)
- `CHANGELOG.md` (new section at the top)

For architecture changes, ensure:

- Config entry runtime state is stored in `ConfigEntry.runtime_data`.
- Diagnostics output redacts sensitive values before export.
- Any new async code avoids blocking I/O on the event loop.

A GitHub Actions release workflow (`release.yml`) validates this consistency on every tag push.

## Security

Please do **not** open public issues for security vulnerabilities. Follow the process described in [SECURITY.md](SECURITY.md).
