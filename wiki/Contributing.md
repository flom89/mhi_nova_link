# Developer Guide (Contributing)

This page describes how to set up a local development environment, follow the code style, and submit contributions to the project.

> **Deutsch:** Diese Seite beschreibt die lokale Entwicklungsumgebung, Code-Standards und den Git-Workflow für Beiträge zum Projekt.

---

## Setting Up a Local Development Environment

### Prerequisites

- Python ≥ 3.14
- `pip` or `uv` (recommended for faster installs)
- Git
- A running Home Assistant instance (for manual testing)

### Clone the repository

```bash
git clone https://github.com/flom89/mhi_nova_link.git
cd mhi_nova_link
```

### Install dependencies

The integration itself has no additional Python runtime dependencies. Tests require Home Assistant and pytest:

```bash
pip install homeassistant pytest pytest-asyncio pytest-homeassistant-custom-component
```

Or with `uv`:

```bash
uv pip install homeassistant pytest pytest-asyncio pytest-homeassistant-custom-component
```

### Link the integration for development

Copy (or symlink) the `custom_components/mhi_nova_link` folder into the `custom_components` directory of your Home Assistant instance and restart HA.

---

## Running Tests

The test suite is located in `custom_components/mhi_nova_link/tests/`. Run all tests from the repository root:

```bash
pytest -q custom_components/mhi_nova_link/tests
```

For verbose output:

```bash
pytest -v custom_components/mhi_nova_link/tests
```

### Test files

| File | Contents |
|---|---|
| `test_smoke.py` | Basic smoke tests (integration loads correctly) |
| `test_sensor_entities.py` | Sensor entities, value scaling, state logic |
| `test_quality_flow.py` | Config Flow, Options Flow, error handling |
| `test_telemetry.py` | Telemetry behavior and logging paths |

For quick quality checks before pushing:

```bash
pytest -q custom_components/mhi_nova_link/tests
ruff check custom_components/mhi_nova_link
```

---

## Coding Standards

- **Language:** Python 3.14+, strict typing (`from typing import Final`, type hints everywhere)
- **Async:** All I/O operations use `async`/`await` (aiohttp)
- **Logging:** Use the module-level logger (`_LOGGER = logging.getLogger(__name__)`); no `print` statements
- **Constants:** All reused strings and values belong in `const.py` as `Final`
- **Error handling:** Use the specific exceptions from `api.py` (`CannotConnect`, `InvalidAuth`, `InvalidCertificate`)
- **Entities:** New entities must inherit from the base class in `entity.py`
- **Translations:** Every new UI-visible string must be added to `strings.json` and all language files under `translations/`
- **No extra dependencies** without explicit justification — `requirements.txt` should remain empty

### Style recommendations

- Follow the [Home Assistant coding style](https://developers.home-assistant.io/docs/development_guidelines)
- Use `ruff` as linter/formatter where applicable
- Keep functions short and focused on a single responsibility

---

## Git Workflow

### Branch naming

| Branch type | Pattern | Example |
|---|---|---|
| Feature | `feature/<short-description>` | `feature/add-humidity-sensor` |
| Bug fix | `fix/<short-description>` | `fix/tls-fingerprint-validation` |
| Documentation | `docs/<short-description>` | `docs/update-wiki` |

### Commit messages

Write concise, descriptive commit messages in the imperative mood:

```
Add compressor power sensor derived from current and frequency
Fix TLS fingerprint normalisation for uppercase hex input
Update German translations for options flow labels
```

### Pull Request rules

1. **Fork** the repository and create a branch from `main`.
2. Make sure **all tests pass** (`pytest -q`).
3. Describe in the PR body:
   - **What** was changed and **why**
   - Affected entities or configuration fields
   - Test coverage added or updated
4. Reference related issues with `Fixes #<issue-number>` or `Closes #<issue-number>`.
5. The code must be **review-ready** — no WIP commits in the final PR.

### Security

Report security vulnerabilities **not** as public issues. Use the [GitHub Security Advisory](https://github.com/flom89/mhi_nova_link/security/advisories/new) mechanism instead. See [SECURITY.md](../SECURITY.md) for details.

---

## Adding New Entities

1. Implement the entity logic in the appropriate platform file (`sensor.py`, `binary_sensor.py`, etc.) or create a new file.
2. Register the entity in `__init__.py` under the relevant platforms.
3. Add the entity name and states to `strings.json` and all `translations/*.json` files.
4. Add a test in `tests/test_sensor_entities.py` or another suitable test file.
5. Update `CHANGELOG.md` under `[Unreleased] → Added`.
