# MHI Nova Link for Home Assistant

<img src="https://raw.githubusercontent.com/flom89/mhi_nova_link/main/custom_components/mhi_nova_link/brand/logo.png" alt="MHI Nova logo" width="320" />

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://github.com/flom89/mhi_nova_link/blob/main/LICENSE)
[![Latest Release](https://img.shields.io/github/v/release/flom89/mhi_nova_link?label=Release)](https://github.com/flom89/mhi_nova_link/releases)
[![Validate](https://github.com/flom89/mhi_nova_link/actions/workflows/main.yml/badge.svg)](https://github.com/flom89/mhi_nova_link/actions/workflows/main.yml)
[![Hassfest](https://github.com/flom89/mhi_nova_link/actions/workflows/hassfest.yml/badge.svg)](https://github.com/flom89/mhi_nova_link/actions/workflows/hassfest.yml)
[![Documentation](https://img.shields.io/badge/docs-wiki-0A66C2)](https://github.com/flom89/mhi_nova_link/wiki)
[![Open Issues](https://img.shields.io/github/issues/flom89/mhi_nova_link?label=issues)](https://github.com/flom89/mhi_nova_link/issues)

MHI Nova Link lets you control your Mitsubishi Heavy Industries system in Home Assistant when your setup uses a **CompTrol 4Web NOVA RC** gateway.

Current integration version: **2.3.5**

## Compatibility

Version 2.3.5 preserves the entity IDs and zone-level entity set from 2.3.3.
For zones with multiple indoor units, indoor-unit entities now use separate
Home Assistant devices linked to their zone. Zones with one indoor unit
continue to use the existing zone-level entities without additional duplicates.

## Hardware Reference

The integration is designed for installations using the CompTrol 4Web / 4WebNRC hardware family.

- Official product page: https://www.s-klima.de/shop/comptrol/comptrol-erweiterungsmodule/comptrol-4web-4webnrc.html

## What You Can Do

- Control temperature, mode, fan, swing, and power for your zones.
- See important status values from your zones and gateway.
- Use Home Assistant automations with climate, sensor, binary sensor, switch, and select entities.
- Complete setup directly in the Home Assistant UI.
- Reauthenticate easily if credentials change.
- Use with self-signed gateway certificates (automatic fingerprint handling is supported).
- Configure automatic restore of the previous operating state after operation lock / external cooling is released.
- Keep diagnostics safer with sensitive values redacted.
- Use the integration in English, German, Italian, Spanish, or French.

## Supported Platforms

- Climate
- Sensor
- Binary sensor
- Switch
- Select

## Requirements

- Home Assistant with custom integrations support.
- A reachable CompTrol 4Web NOVA RC gateway on your local network.
- A dedicated gateway account for Home Assistant.

## Installation

### HACS

If this integration is not yet in the default HACS store for your installation, add it as a custom repository first:

1. Open HACS.
2. Add this repository as a custom repository:
   - URL: `https://github.com/flom89/mhi_nova_link`
   - Category: `Integration`
3. Search for **MHI Nova Link** and install.
4. Restart Home Assistant.

Once available in the default HACS store, steps 2 (custom repository) can be skipped.

## First-Time Setup (In Home Assistant)

After installation:

1. Go to **Settings -> Devices & Services**.
2. Select **Add Integration**.
3. Search for **MHI Nova Link**.
4. Enter:
   - Hostname or IP address of your gateway
   - Username
   - Password
   - Optional SSL SHA256 fingerprint

Tip:
If you leave fingerprint empty and your gateway uses a self-signed certificate, the integration can detect and save the fingerprint automatically.

## Entity Overview

- **Climate**: one per zone
- **Sensors**: zone temperatures, setpoints, mode/fan states, time-series diagnostics, gateway software version
- **Binary sensors**: running, availability, compressor/defrost activity, notifications, gateway GPIO states, update availability
- **Selects**: louver and vane positions
- **Switches**: 3D auto mode, gateway GPIO outputs (Betriebssperre / operational lock, Externe Kühlung / external cooling)

## Diagnostics

The integration provides diagnostics export in Home Assistant. Sensitive values (host, credentials, TLS fingerprint, anonymous telemetry ID) are automatically redacted.

## Troubleshooting

- **Cannot connect**: verify gateway address, HTTPS availability, and credentials.
- **TLS fingerprint error**: update the fingerprint in options or clear it to let auto-pinning run again.
- **Missing/partial entities**: verify gateway permissions and reload the integration.
- **Reauthentication requested**: complete the reauth flow from the integration card.
- **Restore behavior after lock release unclear**: check the diagnostic sensor **Restore status** on the gateway device.

Restore status quick guide:

- `writeback_scheduled`: restore queued after lock/cooling release.
- `writeback_first_try`: first writeback started.
- `validated_after_first_try`: restore succeeded after first writeback.
- `writeback_retry`: second writeback attempt started.
- `validated_after_retry`: restore succeeded after retry.
- `skipped_user_interaction_before_first_try` or `skipped_user_interaction_before_recheck`: restore skipped because user changed values in HA UI.
- `failed_after_retry`: restore still mismatched after retry.
- `error`: unexpected restore exception.

Timing model:

- First writeback starts after 10 seconds.
- Recheck runs 5 seconds later.
- Retry runs only if mismatch persists and no newer user input was detected.

## Important Note for Operation Lock / External Cooling

Depending on your installation and wiring, certain gateway control switches can affect whether cooling/heating operation is allowed.

If you use operation lock behavior (for example utility-control setups), review the detailed guidance in the wiki before creating automations.

## Documentation

For complete user guides, setup walkthroughs, troubleshooting, and updates, see the wiki:

https://github.com/flom89/mhi_nova_link/wiki

## Contributing

See [CONTRIBUTING.md](https://github.com/flom89/mhi_nova_link/blob/main/CONTRIBUTING.md).

## License

GPL-3.0. See [LICENSE](https://github.com/flom89/mhi_nova_link/blob/main/LICENSE).
