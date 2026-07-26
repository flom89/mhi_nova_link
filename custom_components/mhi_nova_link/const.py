"""Define constants used by the NOVA_RC integration."""

from typing import Final

DOMAIN: Final = "mhi_nova_link"

# Configuration keys
CONF_HOST: Final = "host"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_SSL_FINGERPRINT: Final = "ssl_fingerprint"
CONF_POLL_INTERVAL: Final = "poll_interval"

# Default values
DEFAULT_POLL_INTERVAL: Final = 15

# Environment override for the coordinator poll interval
UPDATE_INTERVAL_ENV_VAR: Final = "NOVA_RC_UPDATE_INTERVAL_SECONDS"
LEGACY_UPDATE_INTERVAL_ENV_VAR: Final = "MHI_NOVALINK_UPDATE_INTERVAL_SECONDS"
