"""Send anonymous opt-in telemetry pings for the MHI Nova Link integration."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import homeassistant
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import ANALYTICS_PING_URL, ANALYTICS_SUPABASE_KEY

_LOGGER = logging.getLogger(__name__)

# Environment variable that disables telemetry at runtime (useful for CI/tests).
_ENV_DISABLE_VAR = "MHI_NOVALINK_DISABLE_ANALYTICS"


def _get_integration_version() -> str:
    """Return the version string from the integration manifest."""
    manifest_path = Path(__file__).parent / "manifest.json"
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))["version"]
    except Exception:  # pylint: disable=broad-except
        return "unknown"


async def async_send_analytics_ping(hass: HomeAssistant, anonymous_id: str) -> None:
    """Send a single anonymous telemetry ping.

    The payload contains only:
    - ``integration_version`` – the version declared in manifest.json
    - ``ha_version`` – the running Home Assistant version
    - ``anonymous_id`` – a random UUID generated at first setup; never
      linked to any personal data

    Any network or server error is silently swallowed so this call never
    affects the integration's normal operation.
    """
    import os  # noqa: PLC0415

    if os.environ.get(_ENV_DISABLE_VAR):
        _LOGGER.debug("Telemetry disabled via environment variable")
        return

    integration_version = await hass.async_add_executor_job(_get_integration_version)
    payload = {
        "integration_version": integration_version,
        "ha_version": homeassistant.__version__,
        "anonymous_id": anonymous_id,
    }
    try:
        session = async_get_clientsession(hass)
        headers = {
            "apikey": ANALYTICS_SUPABASE_KEY,
            "Authorization": f"Bearer {ANALYTICS_SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        async with session.post(
            ANALYTICS_PING_URL,
            json=payload,
            headers=headers,
            timeout=10,
        ) as resp:
            _LOGGER.debug(
                "Telemetry ping sent (status %s)", resp.status
            )
    except Exception:  # pylint: disable=broad-except
        _LOGGER.debug("Telemetry ping failed (non-critical, ignored)")
