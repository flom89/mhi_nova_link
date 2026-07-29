"""Set up the NOVA_RC integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed

from .api import CannotConnect, InvalidAuth, InvalidCertificate, NovaRcApiClient
from .const import (
    CONF_SSL_FINGERPRINT,
    CONF_TIME_SERIES_POLL_INTERVAL,
    DEFAULT_TIME_SERIES_POLL_INTERVAL,
    DOMAIN,
)
from .coordinator import NovaRcDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: tuple[Platform, ...] = (
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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
    api = NovaRcApiClient(
        host=entry.data[CONF_HOST],
        session=session,
        ssl_fingerprint=ssl_fingerprint,
        time_series_poll_interval=entry.options.get(
            CONF_TIME_SERIES_POLL_INTERVAL,
            DEFAULT_TIME_SERIES_POLL_INTERVAL,
        ),
    )

    try:
        await api.async_login(
            username=username,
            password=password,
        )
    except InvalidAuth as err:
        raise ConfigEntryNotReady("Authentication failed") from err
    except InvalidCertificate as err:
        if ssl_fingerprint:
            raise ConfigEntryNotReady(
                "TLS certificate validation failed. Configure ssl_fingerprint for self-signed certificates."
            ) from err

        try:
            discovered_fingerprint = await api.async_get_tls_fingerprint()
            api = NovaRcApiClient(
                host=entry.data[CONF_HOST],
                session=session,
                ssl_fingerprint=discovered_fingerprint,
                time_series_poll_interval=entry.options.get(
                    CONF_TIME_SERIES_POLL_INTERVAL,
                    DEFAULT_TIME_SERIES_POLL_INTERVAL,
                ),
            )
            await api.async_login(
                username=username,
                password=password,
            )
        except InvalidAuth as retry_err:
            raise ConfigEntryNotReady("Authentication failed") from retry_err
        except InvalidCertificate as retry_err:
            raise ConfigEntryNotReady(
                "TLS certificate validation failed. Configure ssl_fingerprint for self-signed certificates."
            ) from retry_err
        except CannotConnect as retry_err:
            raise ConfigEntryNotReady(
                f"Unable to reach gateway: {retry_err}"
            ) from retry_err
        else:
            _LOGGER.warning(
                "Automatically pinned TLS fingerprint for NOVA_RC gateway %s",
                entry.data[CONF_HOST],
            )
            updated_data = dict(entry.data)
            updated_data[CONF_SSL_FINGERPRINT] = discovered_fingerprint
            hass.config_entries.async_update_entry(entry, data=updated_data)
    except CannotConnect as err:
        raise ConfigEntryNotReady(f"Unable to reach gateway: {err}") from err

    coordinator = NovaRcDataUpdateCoordinator(hass=hass, api=api, entry=entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed as err:
        raise ConfigEntryNotReady("Authentication failed") from err
    except UpdateFailed as err:
        raise ConfigEntryNotReady("Unable to initialize coordinator") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data = hass.data.get(DOMAIN)
        if domain_data is not None:
            domain_data.pop(entry.entry_id, None)
            if not domain_data:
                hass.data.pop(DOMAIN, None)

    return unload_ok
