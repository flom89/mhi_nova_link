"""Set up the NOVA_RC integration."""

import logging
import uuid
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import CannotConnect, InvalidAuth, InvalidCertificate, async_login_with_autopin
from .const import (
    ANALYTICS_ANONYMOUS_ID_KEY,
    CONF_ANALYTICS_OPT_IN,
    CONF_SSL_FINGERPRINT,
    CONF_TIME_SERIES_POLL_INTERVAL,
    DEFAULT_TIME_SERIES_POLL_INTERVAL,
)
from .const import (
    DOMAIN as DOMAIN,
)
from .coordinator import NovaRcDataUpdateCoordinator
from .telemetry import async_send_analytics_ping

_LOGGER = logging.getLogger(__name__)

type NovaRcConfigEntry = ConfigEntry["NovaRcRuntimeData"]


@dataclass(slots=True)
class NovaRcRuntimeData:
    """Runtime data stored on each config entry."""

    coordinator: NovaRcDataUpdateCoordinator


PLATFORMS: tuple[Platform, ...] = (
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
)


async def async_setup_entry(hass: HomeAssistant, entry: NovaRcConfigEntry) -> bool:
    """Set up a config entry."""
    expected_title = f"CompTrol 4Web NOVA RC ({entry.data[CONF_HOST]})"
    if entry.title != expected_title:
        hass.config_entries.async_update_entry(entry, title=expected_title)

    session = async_get_clientsession(hass)
    username = entry.options.get(CONF_USERNAME, entry.data[CONF_USERNAME])
    password = entry.options.get(CONF_PASSWORD, entry.data[CONF_PASSWORD])
    ssl_fingerprint = entry.options.get(
        CONF_SSL_FINGERPRINT,
        entry.data.get(CONF_SSL_FINGERPRINT),
    )
    try:
        api, discovered_fingerprint = await async_login_with_autopin(
            host=entry.data[CONF_HOST],
            session=session,
            username=username,
            password=password,
            ssl_fingerprint=ssl_fingerprint,
            time_series_poll_interval=entry.options.get(
                CONF_TIME_SERIES_POLL_INTERVAL,
                DEFAULT_TIME_SERIES_POLL_INTERVAL,
            ),
        )
    except InvalidAuth as err:
        raise ConfigEntryNotReady("Authentication failed") from err
    except InvalidCertificate as err:
        raise ConfigEntryNotReady(
            "TLS certificate validation failed. Configure ssl_fingerprint for self-signed certificates."
        ) from err
    except CannotConnect as err:
        raise ConfigEntryNotReady(f"Unable to reach gateway: {err}") from err

    if discovered_fingerprint:
        _LOGGER.warning(
            "Automatically pinned TLS fingerprint for NOVA_RC gateway %s",
            entry.data[CONF_HOST],
        )
        updated_data = dict(entry.data)
        updated_data[CONF_SSL_FINGERPRINT] = discovered_fingerprint
        hass.config_entries.async_update_entry(entry, data=updated_data)

    coordinator = NovaRcDataUpdateCoordinator(hass=hass, api=api, entry=entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        raise ConfigEntryNotReady("Unable to initialize coordinator") from err

    entry.runtime_data = NovaRcRuntimeData(coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    opt_in = entry.options.get(CONF_ANALYTICS_OPT_IN, entry.data.get(CONF_ANALYTICS_OPT_IN))
    anonymous_id = entry.options.get(
        ANALYTICS_ANONYMOUS_ID_KEY,
        entry.data.get(ANALYTICS_ANONYMOUS_ID_KEY),
    )
    if opt_in and not anonymous_id:
        anonymous_id = str(uuid.uuid4())
        updated_data = dict(entry.data)
        updated_data[ANALYTICS_ANONYMOUS_ID_KEY] = anonymous_id
        hass.config_entries.async_update_entry(entry, data=updated_data)
    if opt_in and anonymous_id:
        hass.async_create_task(async_send_analytics_ping(hass, anonymous_id))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: NovaRcConfigEntry) -> bool:
    """Remove a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
