"""Coordinate periodic data updates for NOVA_RC."""

import asyncio
import logging
import os
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, InvalidAuth, InvalidCertificate, NovaRcApiClient
from .const import (
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    LEGACY_UPDATE_INTERVAL_ENV_VAR,
    UPDATE_INTERVAL_ENV_VAR,
)

_LOGGER = logging.getLogger(__name__)


class NovaRcDataUpdateCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinate periodic data updates from the gateway."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: NovaRcApiClient,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator with the configured poll interval."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=_get_update_interval(entry),
        )
        self.api = api
        self.gpios: dict[str, bool] = {}
        self.gateway_update: dict[str, Any] = {}

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch the latest zone data from the GraphQL gateway."""
        try:
            data, notifications, gpios, gateway_update = await asyncio.gather(
                self.api.async_get_zones(),
                self.api.async_get_notifications(),
                self.api.async_get_gpios(),
                self.api.async_get_gateway_update_information(),
            )
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except InvalidCertificate as err:
            raise UpdateFailed(f"TLS certificate validation failed: {err}") from err
        except CannotConnect as err:
            raise UpdateFailed(f"Error loading NOVA_RC data: {err}") from err
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error while fetching NOVA_RC data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

        if notifications:
            for zone in data:
                zone["notifications"] = notifications

        self.gpios = gpios
        previous_installed_version = self.gateway_update.get("installed_version")
        self.gateway_update = gateway_update
        if (
            self.gateway_update.get("installed_version") is None
            and previous_installed_version is not None
        ):
            self.gateway_update["installed_version"] = previous_installed_version
        return data


def _get_update_interval(entry: Any | None) -> timedelta:
    """Return the configured coordinator update interval."""
    raw_value: Any = None

    if entry is not None and hasattr(entry, "options"):
        raw_value = entry.options.get(CONF_POLL_INTERVAL)

    if raw_value is None:
        raw_value = os.getenv(UPDATE_INTERVAL_ENV_VAR)
    if raw_value is None:
        raw_value = os.getenv(LEGACY_UPDATE_INTERVAL_ENV_VAR)

    if raw_value is None:
        return timedelta(seconds=DEFAULT_POLL_INTERVAL)

    try:
        interval = int(raw_value)
    except (TypeError, ValueError):
        _LOGGER.warning(
            "Ignoring invalid %s value %r; using %s seconds",
            CONF_POLL_INTERVAL,
            raw_value,
            DEFAULT_POLL_INTERVAL,
        )
        return timedelta(seconds=DEFAULT_POLL_INTERVAL)

    return timedelta(seconds=max(interval, 1))
