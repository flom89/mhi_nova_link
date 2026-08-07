"""Define constants used by the MHI Nova Link integration."""

from typing import Final

DOMAIN: Final = "mhi_nova_link"
MANUFACTURER: Final = "STULZ GmbH"
MODEL: Final = "CompTrol 4Web NOVA RC"

# Configuration keys
CONF_HOST: Final = "host"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_SSL_FINGERPRINT: Final = "ssl_fingerprint"
CONF_POLL_INTERVAL: Final = "poll_interval"
CONF_TIME_SERIES_POLL_INTERVAL: Final = "time_series_poll_interval"
CONF_GPIO_RESTORE_ENABLED: Final = "gpio_restore_enabled"
CONF_GPIO_RESTORE_VALIDITY_MINUTES: Final = "gpio_restore_validity_minutes"
CONF_GPIO_RESTORE_SYSTEM_STOP: Final = "gpio_restore_system_stop"
CONF_GPIO_RESTORE_FREE_COOLING: Final = "gpio_restore_free_cooling"

# Default values
DEFAULT_POLL_INTERVAL: Final = 15
DEFAULT_TIME_SERIES_POLL_INTERVAL: Final = 60
DEFAULT_GPIO_RESTORE_ENABLED: Final = False
DEFAULT_GPIO_RESTORE_VALIDITY_MINUTES: Final = 120
DEFAULT_GPIO_RESTORE_SYSTEM_STOP: Final = True
DEFAULT_GPIO_RESTORE_FREE_COOLING: Final = True

# Analytics / telemetry
CONF_ANALYTICS_OPT_IN: Final = "analytics_opt_in"
ANALYTICS_ANONYMOUS_ID_KEY: Final = "analytics_anonymous_id"
_SUPABASE_URL: Final = "https://tqjcumkijngqjhbhvhld.supabase.co"
# Publishable key - safe to embed in client code (access is restricted by RLS).
ANALYTICS_SUPABASE_KEY: Final = "sb_publishable_dmay8xixSiT1VcJNyjEGoQ_Mmgujb8M"
ANALYTICS_PING_URL: Final = f"{_SUPABASE_URL}/rest/v1/install_pings"

# Environment override for the coordinator poll interval
UPDATE_INTERVAL_ENV_VAR: Final = "NOVA_RC_UPDATE_INTERVAL_SECONDS"
TIME_SERIES_UPDATE_INTERVAL_ENV_VAR: Final = "NOVA_RC_TIME_SERIES_UPDATE_INTERVAL_SECONDS"
