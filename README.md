# MHI Nova Link for Home Assistant

![MHI Nova logo](custom_components/mhi_nova_link/brand/logo.png)

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)

This repository folder contains a custom Home Assistant integration for using Mitsubishi Heavy Industries Air Conditioners connected to a CompTrol 4Web NOVA RC via Home Assistant.

## Features

- Connects to a CompTrol 4Web NOVA RC gateway over the local network using SSL connection.
- Exposes relevant climate, sensor, select, switch, and binary sensor entities.
- Supports config flow and options flow for easy integration and maintenance.
- Includes translation for English, German, Italian, Spanish, and French.
- Supports automatic TLS fingerprint pinning for self-signed gateway certificates.
- Optional anonymous installation telemetry (opt-in) to help monitor integration adoption.
- Exposes gateway software information, including installed version and update availability.

## Requirements

- A reachable CompTrol 4Web NOVA RC gateway in your local network.
- A dedicated gateway user account for Home Assistant.
- Home Assistant with support for custom integrations.

## Installation

Create a user on the CompTrol 4Web NOVA RC for this integration. The credentials are stored in Home Assistant.

### Manual installation

1. Copy the `mhi_nova_link` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from Settings -> Devices & Services.

### HACS / Custom Repository

If you use HACS, add this repository as a custom repository:

- Repository URL: [https://github.com/flom89/mhi_nova_link](https://github.com/flom89/mhi_nova_link)
- Category: Integration

Then search for MHI Nova Link in HACS and install it.

## Configuration

During setup, enter:

- Gateway IP address or hostname.
- Username and password for the CompTrol user.
- Optional SSL fingerprint.

### TLS and SSL fingerprint behavior

- The integration connects over HTTPS.
- For self-signed certificates, the integration can automatically discover and pin the certificate fingerprint.
- You can also set or override the fingerprint manually in the integration options.

### Anonymous telemetry (opt-in)

- Telemetry is disabled by default and only sent when explicitly enabled during setup/options.
- A ping is sent on integration setup with: integration version, Home Assistant version, and a random anonymous ID.
- The payload contains no host, username, device names, zone names, or sensor values.

## Entities

The integration provides:

- Climate entities per zone.
- Zone-level sensors for temperature, setpoint, mode, fan state, and time-series values.
- Gateway binary sensors for Digital IO states.
- Gateway info entities for software version and update availability.

## Troubleshooting

- TLS certificate validation failed:
	- Verify gateway host/IP and certificate.
	- Open integration options and set a valid SHA256 fingerprint if needed.
- Cannot connect:
	- Verify gateway reachability and credentials.
	- Confirm HTTPS endpoint access in local network.
- No entities or incomplete data:
	- Check user permissions on the CompTrol gateway.
	- Reload the integration from Home Assistant settings.
- Telemetry not visible in logs:
	- Enable debug logging for `custom_components.mhi_nova_link`.
	- If analytics are not opted in, no telemetry ping is sent.
	- Rejected telemetry writes are logged as warnings with the HTTP status.

Enable debug logging in `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.mhi_nova_link: debug
```

## Development

The integration is tested through Home Assistant's integration test suite.

From this repository root, run:

```bash
pytest -q custom_components/mhi_nova_link/tests
```

## Restriction

Please consider reviewing the terms and conditions of STULZ S-Klima regarding permitted usage of CompTrol 4Web NOVA RC.

## License

This project is licensed under the GNU General Public License v3.0.

See the full license text in LICENSE.

## Notes

This custom integration is experimental and may cause damage; use is entirely at your own risk. There are no cards or GUI elements included. Use your preferred ones.
