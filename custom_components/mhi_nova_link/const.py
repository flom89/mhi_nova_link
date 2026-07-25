"""Constants for the MHI NovaLink integration."""

from typing import Final

DOMAIN: Final = "mhi_nova_link"

# Configuration keys
CONF_HOST: Final = "host"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_POLL_INTERVAL: Final = "poll_interval"

# Default values
DEFAULT_PORT: Final = 80
DEFAULT_UPDATE_INTERVAL: Final = 15
DEFAULT_USERNAME: Final = "user"
DEFAULT_POLL_INTERVAL: Final = 15

# Environment override for the coordinator poll interval
UPDATE_INTERVAL_ENV_VAR: Final = "MHI_NOVALINK_UPDATE_INTERVAL_SECONDS"
