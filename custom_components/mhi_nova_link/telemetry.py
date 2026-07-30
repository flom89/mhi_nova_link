"""Send anonymous opt-in telemetry pings for the MHI Nova Link integration."""

import json
import logging
from pathlib import Path

from aiohttp import ClientError

from homeassistant.const import __version__ as HA_VERSION
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
    except OSError, json.JSONDecodeError, KeyError, TypeError:
        return "unknown"


async def async_send_analytics_ping(hass: HomeAssistant, anonymous_id: str) -> None:
    """Send a single anonymous telemetry ping.

    The payload contains only:
        - ``integration_version`` - the version declared in manifest.json
        - ``ha_version`` - the running Home Assistant version
        - ``anonymous_id`` - a random UUID generated at first setup; never
      linked to any personal data

    Any network or server error is logged and swallowed so this call never
    affects the integration's normal operation.
    """
    import os  # noqa: PLC0415

    if os.environ.get(_ENV_DISABLE_VAR):
        _LOGGER.debug("Telemetry disabled via environment variable")
        return

    integration_version = await hass.async_add_executor_job(_get_integration_version)
    payload = {
        "integration_version": integration_version,
        "ha_version": HA_VERSION,
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
            if 200 <= resp.status < 300:
                _LOGGER.debug("Telemetry ping sent (status %s)", resp.status)
                return

            response_preview = (await resp.text()).strip()[:500]
            _LOGGER.warning(
                "Telemetry ping rejected (status %s): %s",
                resp.status,
                response_preview or "<empty response>",
            )
    except ClientError, TimeoutError, OSError:
        _LOGGER.warning("Telemetry ping request failed (non-critical, ignored)")
