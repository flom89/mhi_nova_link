# MHI Nova Link for Home Assistant

![MHI Nova logo](custom_components/mhi_nova_link/brand/logo.png)

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)

MHI Nova Link is a custom Home Assistant integration for Mitsubishi Heavy Industries systems connected through a **CompTrol 4Web NOVA RC** gateway.

## Features

- Local HTTPS communication with NOVA RC gateways.
- Config flow, options flow, and reauthentication support.
- Automatic TLS fingerprint pinning (TOFU) for self-signed certificates.
- Zone climate control entities (mode, fan, swing, setpoint, on/off).
- Zone and gateway sensors, binary sensors, switches, and selects.
- Safe diagnostics export with sensitive fields redacted.
- Optional anonymous telemetry (strictly opt-in).
- Translations: English, German, Italian, Spanish, French.

## Supported Platforms

- `climate`
- `sensor`
- `binary_sensor`
- `switch`
- `select`

## Requirements

- Home Assistant with custom integrations support.
- A reachable CompTrol 4Web NOVA RC gateway on your local network.
- A dedicated gateway account for Home Assistant.

## Installation

### HACS

1. Open HACS.
2. Add this repository as a custom repository:
   - URL: `https://github.com/flom89/mhi_nova_link`
   - Category: `Integration`
3. Search for **MHI Nova Link** and install.
4. Restart Home Assistant.

### Manual

1. Copy `/custom_components/mhi_nova_link` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration**.
4. Search for **MHI Nova Link**.

## Configuration

During setup:

- Hostname or IP address
- Username
- Password
- Optional SSL SHA256 fingerprint

If no fingerprint is provided and the gateway uses a self-signed certificate, the integration can auto-discover and pin the certificate fingerprint on first connection.

## Entity Overview

- **Climate**: one per zone
- **Sensors**: zone temperatures, setpoints, mode/fan states, time-series diagnostics, gateway software version
- **Binary sensors**: running, availability, compressor/defrost activity, notifications, gateway GPIO states, update availability
- **Selects**: louver and vane positions
- **Switches**: 3D auto mode, gateway GPIO outputs (Betriebssperre, Externe Kühlung)

## Diagnostics

The integration provides diagnostics export in Home Assistant. Sensitive values (host, credentials, TLS fingerprint, anonymous telemetry ID) are automatically redacted.

## Troubleshooting

- **Cannot connect**: verify gateway address, HTTPS availability, and credentials.
- **TLS fingerprint error**: update the fingerprint in options or clear it to let auto-pinning run again.
- **Missing/partial entities**: verify gateway permissions and reload the integration.
- **Reauthentication requested**: complete the reauth flow from the integration card.

Enable debug logging:

```yaml
logger:
  default: warning
  logs:
    custom_components.mhi_nova_link: debug
```

## Development

From repository root:

```bash
pip install homeassistant pytest pytest-asyncio ruff mypy
ruff check custom_components/mhi_nova_link
mypy custom_components/mhi_nova_link
pytest -q custom_components/mhi_nova_link/tests
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

GPL-3.0. See [LICENSE](LICENSE).
