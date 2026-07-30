"""Define constants used by the NOVA_RC integration."""

from typing import Final

DOMAIN: Final = "mhi_nova_link"

# Configuration keys
CONF_HOST: Final = "host"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_SSL_FINGERPRINT: Final = "ssl_fingerprint"
CONF_POLL_INTERVAL: Final = "poll_interval"
CONF_TIME_SERIES_POLL_INTERVAL: Final = "time_series_poll_interval"

# Default values
DEFAULT_POLL_INTERVAL: Final = 15
DEFAULT_TIME_SERIES_POLL_INTERVAL: Final = 60

# Analytics / telemetry
CONF_ANALYTICS_OPT_IN: Final = "analytics_opt_in"
ANALYTICS_ANONYMOUS_ID_KEY: Final = "analytics_anonymous_id"
# Replace this URL with your own analytics endpoint before deploying.
ANALYTICS_PING_URL: Final = (
    "https://analytics.mhi-nova-link.dev/ping"
)

# Environment override for the coordinator poll interval
UPDATE_INTERVAL_ENV_VAR: Final = "NOVA_RC_UPDATE_INTERVAL_SECONDS"
LEGACY_UPDATE_INTERVAL_ENV_VAR: Final = "MHI_NOVALINK_UPDATE_INTERVAL_SECONDS"
TIME_SERIES_UPDATE_INTERVAL_ENV_VAR: Final = (
    "NOVA_RC_TIME_SERIES_UPDATE_INTERVAL_SECONDS"
)
LEGACY_TIME_SERIES_UPDATE_INTERVAL_ENV_VAR: Final = (
    "MHI_NOVALINK_TIME_SERIES_UPDATE_INTERVAL_SECONDS"
)
