"""Data update coordinator for MHI Nova / S-Klima."""

from datetime import timedelta
import logging
import os
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, InvalidAuth, SKlimaApiClient
from .const import (
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    UPDATE_INTERVAL_ENV_VAR,
)

_LOGGER = logging.getLogger(__name__)


class SKlimaDataUpdateCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinate periodic data updates from the gateway."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: SKlimaApiClient,
        entry: Any | None = None,
    ) -> None:
        """Initialize the coordinator with the configured poll interval."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=_get_update_interval(entry),
        )
        self.api = api

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch the latest zone data from the GraphQL gateway."""
        try:
            data = await self.api.async_get_zones()
            notifications = await self.api.async_get_notifications()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except CannotConnect as err:
            raise UpdateFailed(f"Fehler beim Laden der S-Klima Daten: {err}") from err
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error while fetching S-Klima data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

        if notifications:
            for zone in data:
                zone["notifications"] = notifications
        return data


def _get_update_interval(entry: Any | None) -> timedelta:
    """Return the configured coordinator update interval."""
    raw_value: Any = None

    if entry is not None and hasattr(entry, "options"):
        raw_value = entry.options.get(CONF_POLL_INTERVAL)

    if raw_value is None:
        raw_value = os.getenv(UPDATE_INTERVAL_ENV_VAR)

    if raw_value is None:
        return timedelta(seconds=DEFAULT_POLL_INTERVAL)

    try:
        interval = int(raw_value)
    except TypeError, ValueError:
        _LOGGER.warning(
            "Ignoring invalid %s value %r; using %s seconds",
            CONF_POLL_INTERVAL,
            raw_value,
            DEFAULT_POLL_INTERVAL,
        )
        return timedelta(seconds=DEFAULT_POLL_INTERVAL)

    return timedelta(seconds=max(interval, 1))
