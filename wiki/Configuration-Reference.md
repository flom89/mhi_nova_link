# Configuration Reference

## Initial setup fields

- **Host**: IP address or hostname of the NOVA RC gateway
- **Username** / **Password**: gateway credentials
- **SSL fingerprint** (optional): SHA256 fingerprint

Fingerprint format accepted:

- 64 hex characters
- Upper/lower case allowed
- `:` separators allowed (they are normalized)

## Options flow

Open **Settings → Devices & Services → MHI Nova Link → Configure**.

Available options:

- **ZoneQueries Polling Interval** (`poll_interval`, default: `15s`)
- **Timeseries Polling Interval** (`time_series_poll_interval`, default: `60s`)
- **SSL fingerprint**
- **Username**
- **Password**

## Environment variable overrides

For advanced/self-managed deployments:

- `NOVA_RC_UPDATE_INTERVAL_SECONDS`
- `MHI_NOVALINK_UPDATE_INTERVAL_SECONDS` (legacy)
- `NOVA_RC_TIME_SERIES_UPDATE_INTERVAL_SECONDS`
- `MHI_NOVALINK_TIME_SERIES_UPDATE_INTERVAL_SECONDS` (legacy)

Values must be positive integers (seconds). Invalid values are ignored and defaults are used.
