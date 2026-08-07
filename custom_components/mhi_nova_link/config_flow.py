"""Define the config and options flow for NOVA_RC."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    CannotConnect,
    InvalidAuth,
    InvalidCertificate,
    async_login_with_autopin,
    normalize_ssl_fingerprint,
)
from .const import (
    ANALYTICS_ANONYMOUS_ID_KEY,
    CONF_ANALYTICS_OPT_IN,
    CONF_GPIO_RESTORE_ENABLED,
    CONF_GPIO_RESTORE_FREE_COOLING,
    CONF_GPIO_RESTORE_SYSTEM_STOP,
    CONF_GPIO_RESTORE_VALIDITY_MINUTES,
    CONF_POLL_INTERVAL,
    CONF_SSL_FINGERPRINT,
    CONF_TIME_SERIES_POLL_INTERVAL,
    DEFAULT_GPIO_RESTORE_ENABLED,
    DEFAULT_GPIO_RESTORE_FREE_COOLING,
    DEFAULT_GPIO_RESTORE_SYSTEM_STOP,
    DEFAULT_GPIO_RESTORE_VALIDITY_MINUTES,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_TIME_SERIES_POLL_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_USERNAME, default=""): str,
        vol.Optional(CONF_PASSWORD, default=""): str,
        vol.Optional(CONF_SSL_FINGERPRINT, default=""): str,
    }
)


class NovaRcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NOVA_RC."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._pending_entry_data: dict[str, Any] = {}
        self._reauth_entry: config_entries.ConfigEntry | None = None

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NovaRcOptionsFlow:
        """Create the options flow for this integration."""
        return NovaRcOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                ssl_fingerprint = normalize_ssl_fingerprint(user_input.get(CONF_SSL_FINGERPRINT))
            except ValueError:
                errors["base"] = "invalid_ssl_fingerprint_format"
                ssl_fingerprint = None
            if not errors:
                session = async_get_clientsession(self.hass)
                try:
                    _, auto_fingerprint = await async_login_with_autopin(
                        host=user_input[CONF_HOST],
                        session=session,
                        username=user_input.get(CONF_USERNAME, ""),
                        password=user_input.get(CONF_PASSWORD, ""),
                        ssl_fingerprint=ssl_fingerprint,
                    )
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except InvalidCertificate:
                    errors["base"] = "invalid_ssl_fingerprint"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected error during config flow")
                    errors["base"] = "unknown"
                else:
                    if auto_fingerprint:
                        ssl_fingerprint = auto_fingerprint

                if not errors:
                    await self.async_set_unique_id(user_input[CONF_HOST])
                    self._abort_if_unique_id_configured()

                    entry_data = dict(user_input)
                    if ssl_fingerprint:
                        entry_data[CONF_SSL_FINGERPRINT] = ssl_fingerprint
                    else:
                        entry_data.pop(CONF_SSL_FINGERPRINT, None)

                    self._pending_entry_data = entry_data
                    return await self.async_step_analytics()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_analytics(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask whether the user wants to share anonymous usage analytics."""
        if user_input is not None:
            entry_data = dict(self._pending_entry_data)
            if user_input.get(CONF_ANALYTICS_OPT_IN, False):
                entry_data[CONF_ANALYTICS_OPT_IN] = True
                entry_data[ANALYTICS_ANONYMOUS_ID_KEY] = str(uuid.uuid4())
            else:
                entry_data[CONF_ANALYTICS_OPT_IN] = False

            host = entry_data[CONF_HOST]
            return self.async_create_entry(
                title=f"CompTrol 4Web NOVA RC ({host})",
                data=entry_data,
            )

        return self.async_show_form(
            step_id="analytics",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_ANALYTICS_OPT_IN, default=False): bool,
                }
            ),
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle reauthentication requests."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm reauthentication with updated credentials."""
        errors: dict[str, str] = {}
        if self._reauth_entry is None:
            return self.async_abort(reason="reauth_unsuccessful")

        default_username = self._reauth_entry.options.get(
            CONF_USERNAME,
            self._reauth_entry.data.get(CONF_USERNAME, ""),
        )
        default_password = self._reauth_entry.options.get(
            CONF_PASSWORD,
            self._reauth_entry.data.get(CONF_PASSWORD, ""),
        )
        default_fingerprint = self._reauth_entry.options.get(
            CONF_SSL_FINGERPRINT,
            self._reauth_entry.data.get(CONF_SSL_FINGERPRINT, ""),
        )

        if user_input is not None:
            try:
                ssl_fingerprint = normalize_ssl_fingerprint(user_input.get(CONF_SSL_FINGERPRINT))
            except ValueError:
                errors["base"] = "invalid_ssl_fingerprint_format"
            else:
                session = async_get_clientsession(self.hass)
                reauth_password = user_input.get(CONF_PASSWORD, "")
                try:
                    _, auto_fingerprint = await async_login_with_autopin(
                        host=self._reauth_entry.data[CONF_HOST],
                        session=session,
                        username=user_input.get(CONF_USERNAME, ""),
                        **{CONF_PASSWORD: reauth_password},
                        ssl_fingerprint=ssl_fingerprint,
                    )
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except InvalidCertificate:
                    errors["base"] = "invalid_ssl_fingerprint"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected error during reauthentication")
                    errors["base"] = "unknown"
                else:
                    updated_data = dict(self._reauth_entry.data)
                    updated_data[CONF_USERNAME] = user_input.get(CONF_USERNAME, "")
                    updated_data[CONF_PASSWORD] = user_input.get(CONF_PASSWORD, "")
                    if auto_fingerprint:
                        ssl_fingerprint = auto_fingerprint
                    if ssl_fingerprint:
                        updated_data[CONF_SSL_FINGERPRINT] = ssl_fingerprint
                    else:
                        updated_data.pop(CONF_SSL_FINGERPRINT, None)

                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry,
                        data=updated_data,
                    )
                    await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_USERNAME, default=default_username): str,
                    vol.Optional(CONF_PASSWORD, default=default_password): str,
                    vol.Optional(CONF_SSL_FINGERPRINT, default=default_fingerprint): str,
                }
            ),
            errors=errors,
        )


class NovaRcOptionsFlow(config_entries.OptionsFlow):
    """Handle NOVA_RC options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                ssl_fingerprint = normalize_ssl_fingerprint(user_input.get(CONF_SSL_FINGERPRINT))
            except ValueError:
                errors["base"] = "invalid_ssl_fingerprint_format"
            else:
                new_host = user_input[CONF_HOST]
                session = async_get_clientsession(self.hass)
                try:
                    _, auto_fingerprint = await async_login_with_autopin(
                        host=new_host,
                        session=session,
                        username=user_input.get(CONF_USERNAME, ""),
                        **{CONF_PASSWORD: user_input.get(CONF_PASSWORD, "")},
                        ssl_fingerprint=ssl_fingerprint,
                    )
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except InvalidCertificate:
                    errors["base"] = "invalid_ssl_fingerprint"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected error during options flow")
                    errors["base"] = "unknown"
                else:
                    if auto_fingerprint:
                        ssl_fingerprint = auto_fingerprint

                    entry_data = dict(user_input)
                    if ssl_fingerprint:
                        entry_data[CONF_SSL_FINGERPRINT] = ssl_fingerprint
                    else:
                        entry_data.pop(CONF_SSL_FINGERPRINT, None)
                    if entry_data.get(CONF_ANALYTICS_OPT_IN):
                        anonymous_id = self._config_entry.options.get(
                            ANALYTICS_ANONYMOUS_ID_KEY,
                            self._config_entry.data.get(ANALYTICS_ANONYMOUS_ID_KEY),
                        )
                        entry_data[ANALYTICS_ANONYMOUS_ID_KEY] = anonymous_id or str(uuid.uuid4())
                    else:
                        entry_data.pop(ANALYTICS_ANONYMOUS_ID_KEY, None)

                    # Persist the (possibly changed) host into entry.data
                    updated_data = dict(self._config_entry.data)
                    updated_data[CONF_HOST] = new_host
                    if ssl_fingerprint:
                        updated_data[CONF_SSL_FINGERPRINT] = ssl_fingerprint
                    else:
                        updated_data.pop(CONF_SSL_FINGERPRINT, None)
                    updated_data[CONF_USERNAME] = user_input.get(CONF_USERNAME, "")
                    updated_data[CONF_PASSWORD] = user_input.get(CONF_PASSWORD, "")

                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        title=f"CompTrol 4Web NOVA RC ({new_host})",
                        unique_id=new_host,
                        data=updated_data,
                    )

                    # Remove host/credentials from the options dict (they live in data)
                    options_data = {
                        k: v
                        for k, v in entry_data.items()
                        if k
                        not in (
                            CONF_HOST,
                            CONF_USERNAME,
                            CONF_PASSWORD,
                            CONF_SSL_FINGERPRINT,
                        )
                    }

                    return self.async_create_entry(title="", data=options_data)

        default_ssl_fingerprint = self._config_entry.options.get(
            CONF_SSL_FINGERPRINT,
            self._config_entry.data.get(CONF_SSL_FINGERPRINT, ""),
        )
        default_username = self._config_entry.options.get(
            CONF_USERNAME,
            self._config_entry.data.get(CONF_USERNAME, ""),
        )
        default_password = self._config_entry.options.get(
            CONF_PASSWORD,
            self._config_entry.data.get(CONF_PASSWORD, ""),
        )

        default_host = self._config_entry.data.get(CONF_HOST, "")

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=default_host,
                    ): str,
                    vol.Optional(
                        CONF_POLL_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_POLL_INTERVAL,
                            DEFAULT_POLL_INTERVAL,
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                    vol.Optional(
                        CONF_TIME_SERIES_POLL_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_TIME_SERIES_POLL_INTERVAL,
                            DEFAULT_TIME_SERIES_POLL_INTERVAL,
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                    vol.Optional(
                        CONF_GPIO_RESTORE_ENABLED,
                        default=self._config_entry.options.get(
                            CONF_GPIO_RESTORE_ENABLED,
                            DEFAULT_GPIO_RESTORE_ENABLED,
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_GPIO_RESTORE_VALIDITY_MINUTES,
                        default=self._config_entry.options.get(
                            CONF_GPIO_RESTORE_VALIDITY_MINUTES,
                            DEFAULT_GPIO_RESTORE_VALIDITY_MINUTES,
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                    vol.Optional(
                        CONF_GPIO_RESTORE_SYSTEM_STOP,
                        default=self._config_entry.options.get(
                            CONF_GPIO_RESTORE_SYSTEM_STOP,
                            DEFAULT_GPIO_RESTORE_SYSTEM_STOP,
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_GPIO_RESTORE_FREE_COOLING,
                        default=self._config_entry.options.get(
                            CONF_GPIO_RESTORE_FREE_COOLING,
                            DEFAULT_GPIO_RESTORE_FREE_COOLING,
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_SSL_FINGERPRINT,
                        default=default_ssl_fingerprint,
                    ): str,
                    vol.Optional(
                        CONF_USERNAME,
                        default=default_username,
                    ): str,
                    vol.Optional(
                        CONF_PASSWORD,
                        default=default_password,
                    ): str,
                    vol.Optional(
                        CONF_ANALYTICS_OPT_IN,
                        default=self._config_entry.options.get(
                            CONF_ANALYTICS_OPT_IN,
                            self._config_entry.data.get(CONF_ANALYTICS_OPT_IN, False),
                        ),
                    ): bool,
                }
            ),
            errors=errors,
        )
