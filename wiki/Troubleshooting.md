# Troubleshooting

## Cannot connect

- Verify gateway IP/hostname is reachable from Home Assistant.
- Confirm local network/firewall allows HTTPS to the gateway.
- Check the gateway user credentials.

## Authentication fails

- Verify username/password in integration options.
- Confirm the account is active and has required gateway permissions.

## TLS certificate validation failed

- If the gateway is self-signed, leave fingerprint empty on first setup so auto-pinning can run.
- If auto-pinning fails, retrieve the SHA256 cert fingerprint manually and set it in options.
- Ensure fingerprint is exactly 64 hex characters (colons allowed).

## Missing entities or partial data

- Reload the integration from Devices & Services.
- Confirm zones and indoor units are configured and online in the gateway.
- Wait for at least one full poll cycle (zone + time-series).

## Slow updates

- Reduce `poll_interval` and/or `time_series_poll_interval` in options.
- Keep intervals realistic to avoid overloading the gateway.

## Gateway update status not visible

- Ensure the gateway firmware exposes update information.
- Check Home Assistant logs for query failures from `custom_components.mhi_nova_link`.

## Collecting logs

1. In Home Assistant, set logger for `custom_components.mhi_nova_link` to debug.
2. Reproduce the issue.
3. Include relevant logs when opening a GitHub issue:
   - https://github.com/flom89/mhi_nova_link/issues
