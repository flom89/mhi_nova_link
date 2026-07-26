# MHI Nova Link for Home Assistant

![MHI Nova logo](custom_components/mhi_nova_link/brand/logo.png)

![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/License-PolyForm%20Noncommercial%201.0.0-red)

This repository folder contains a custom Home Assistant integration for using Mitsubishi Heavy Industries Air Conditioners connected to a CompTrol 4Web NOVA RC via Home Assistant.

## Features

- Connects to a CompTrol 4Web NOVA RC gateway over the local network using SSL connection.
- Exposes relevant climate, sensor, select, switch, and binary sensor entities.
- Supports config flow and options flow for easy integration and maintenance.
- Includes translation for English, German, Italian, Spanish, and French.
- Supports automatic TLS fingerprint pinning for self-signed gateway certificates.
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

## Development

The integration is tested through Home Assistant's integration test suite.

From this repository root, run:

```bash
pytest -q custom_components/mhi_nova_link/tests
```

## Restriction

Please consider reviewing the terms and conditions of STULZ S-Klima regarding permitted usage of CompTrol 4Web NOVA RC.

## License

This project is licensed under PolyForm Noncommercial 1.0.0.

- Non-commercial use, modification, and sharing are permitted.
- Commercial use is not permitted without separate permission from the copyright holder.

See the full license text in LICENSE.

## Notes

This custom integration is experimental and may cause damage; use is entirely at your own risk. There are no cards or GUI elements included. Use your preferred ones.
