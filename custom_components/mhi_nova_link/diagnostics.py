"""Diagnostics support for MHI Nova Link."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import NovaRcConfigEntry
from .const import ANALYTICS_ANONYMOUS_ID_KEY, CONF_SSL_FINGERPRINT

_REDACT_CONFIG: set[str] = {
    "host",
    "username",
    "password",
    CONF_SSL_FINGERPRINT,
    ANALYTICS_ANONYMOUS_ID_KEY,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry | NovaRcConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = getattr(getattr(entry, "runtime_data", None), "coordinator", None)
    gateway_update: dict[str, Any] = {}
    gpios: dict[str, Any] = {}
    zone_count = 0

    if coordinator is not None:
        gateway_update = dict(coordinator.gateway_update)
        gpios = dict(coordinator.gpios)
        zone_count = len(coordinator.data or [])

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), _REDACT_CONFIG),
            "options": async_redact_data(dict(entry.options), _REDACT_CONFIG),
        },
        "runtime": {
            "zone_count": zone_count,
            "gateway_update": gateway_update,
            "gpios": gpios,
        },
    }
