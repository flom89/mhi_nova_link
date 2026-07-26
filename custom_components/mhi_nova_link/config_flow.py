"""Define the config and options flow for NOVA_RC."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    CannotConnect,
    InvalidAuth,
    InvalidCertificate,
    NovaRcApiClient,
    normalize_ssl_fingerprint,
)
from .const import (
    CONF_POLL_INTERVAL,
    CONF_SSL_FINGERPRINT,
    DEFAULT_POLL_INTERVAL,
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
                ssl_fingerprint = normalize_ssl_fingerprint(
                    user_input.get(CONF_SSL_FINGERPRINT)
                )
            except ValueError:
                errors["base"] = "invalid_ssl_fingerprint_format"
                ssl_fingerprint = None
            if not errors:
                session = async_get_clientsession(self.hass)
                client = NovaRcApiClient(
                    host=user_input[CONF_HOST],
                    session=session,
                    ssl_fingerprint=ssl_fingerprint,
                )

                try:
                    await client.async_login(
                        username=user_input.get(CONF_USERNAME, ""),
                        password=user_input.get(CONF_PASSWORD, ""),
                    )
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except InvalidCertificate:
                    if ssl_fingerprint:
                        errors["base"] = "invalid_ssl_fingerprint"
                    else:
                        try:
                            auto_fingerprint = await client.async_get_tls_fingerprint()
                            fallback_client = NovaRcApiClient(
                                host=user_input[CONF_HOST],
                                session=session,
                                ssl_fingerprint=auto_fingerprint,
                            )
                            await fallback_client.async_login(
                                username=user_input.get(CONF_USERNAME, ""),
                                password=user_input.get(CONF_PASSWORD, ""),
                            )
                        except CannotConnect:
                            errors["base"] = "cannot_connect"
                        except InvalidAuth:
                            errors["base"] = "invalid_auth"
                        except InvalidCertificate:
                            errors["base"] = "invalid_ssl_fingerprint"
                        except Exception:  # pylint: disable=broad-except
                            _LOGGER.exception(
                                "Unexpected error during automatic TLS fingerprint setup"
                            )
                            errors["base"] = "unknown"
                        else:
                            ssl_fingerprint = auto_fingerprint
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected error during config flow")
                    errors["base"] = "unknown"
                else:
                    pass

                if not errors:
                    await self.async_set_unique_id(user_input[CONF_HOST])
                    self._abort_if_unique_id_configured()

                    entry_data = dict(user_input)
                    if ssl_fingerprint:
                        entry_data[CONF_SSL_FINGERPRINT] = ssl_fingerprint
                    else:
                        entry_data.pop(CONF_SSL_FINGERPRINT, None)

                    return self.async_create_entry(
                        title=f"CompTrol 4Web NOVA RC ({user_input[CONF_HOST]})",
                        data=entry_data,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
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
                ssl_fingerprint = normalize_ssl_fingerprint(
                    user_input.get(CONF_SSL_FINGERPRINT)
                )
            except ValueError:
                errors["base"] = "invalid_ssl_fingerprint_format"
            else:
                entry_data = dict(user_input)
                if ssl_fingerprint:
                    entry_data[CONF_SSL_FINGERPRINT] = ssl_fingerprint
                else:
                    entry_data.pop(CONF_SSL_FINGERPRINT, None)

                return self.async_create_entry(title="", data=entry_data)

        default_ssl_fingerprint = self._config_entry.options.get(
            CONF_SSL_FINGERPRINT,
            self._config_entry.data.get(CONF_SSL_FINGERPRINT, ""),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLL_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_POLL_INTERVAL,
                            DEFAULT_POLL_INTERVAL,
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                    vol.Optional(
                        CONF_SSL_FINGERPRINT,
                        default=default_ssl_fingerprint,
                    ): str,
                }
            ),
            errors=errors,
        )
