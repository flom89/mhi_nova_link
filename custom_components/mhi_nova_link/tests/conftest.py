"""Shared pytest configuration and fixtures for all NOVA_RC test suites.

Layout
------
tests/
  conftest.py          ← you are here (shared fixtures)
  unit/                ← pure-Python logic, no HA instance, no network
  integration/         ← component wiring with mocked HTTP + HA stubs
  functional/          ← smoke / contract / translation checks
"""

from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# Ensure the custom_components package is importable from every test module.
# ---------------------------------------------------------------------------

_INTEGRATION_DIR = Path(__file__).resolve().parents[1]
_CONFIG_DIR = _INTEGRATION_DIR.parent.parent

if str(_CONFIG_DIR) not in sys.path:
    sys.path.insert(0, str(_CONFIG_DIR))


# ---------------------------------------------------------------------------
# Shared stubs
# ---------------------------------------------------------------------------


def make_coordinator(
    zones: list[dict] | None = None,
    gpios: dict | None = None,
    gateway_update: dict | None = None,
    host: str = "gateway.local",
) -> SimpleNamespace:
    """Return a minimal coordinator stub suitable for entity tests.

    Parameters
    ----------
    zones:
        List of zone dicts. Defaults to one empty zone with zoneId=1.
    gpios:
        Gateway GPIO function-to-bool mapping.
    gateway_update:
        Gateway software update information dict.
    host:
        API host string used for unique_id generation.
    """
    return SimpleNamespace(
        data=zones if zones is not None else [{"zoneId": 1}],
        gpios=gpios or {},
        gateway_update=gateway_update or {},
        config_entry=SimpleNamespace(domain="mhi_nova_link", entry_id="test-entry-id"),
        api=SimpleNamespace(host=host),
        last_update_success=True,
        async_add_listener=lambda callback: lambda: None,
        async_request_refresh=AsyncMock(),
    )


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def coordinator() -> SimpleNamespace:
    """Provide a default coordinator stub with one empty zone."""
    return make_coordinator()


@pytest.fixture
def mock_api() -> SimpleNamespace:
    """Provide a fully mocked API client stub."""
    return SimpleNamespace(
        host="gateway.local",
        async_login=AsyncMock(return_value=True),
        async_get_zones=AsyncMock(return_value=[]),
        async_get_notifications=AsyncMock(return_value={}),
        async_get_gpios=AsyncMock(return_value={}),
        async_get_gateway_update_information=AsyncMock(return_value={}),
        async_set_zone_state=AsyncMock(return_value=True),
        async_get_tls_fingerprint=AsyncMock(return_value="aa" * 32),
    )
