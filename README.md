# MHI Nova for Home Assistant

![MHI Nova logo](custom_components/mhi_nova_link/brand/logo.png)

This repository folder contains a custom Home Assistant integration for MHI Nova gateways.

## Features

- Connects to a CompTrol Nova gateway over the local network
- Exposes climate, sensor, select, switch, and binary sensor entities
- Supports config flow and options flow
- Includes translation strings for the UI

## Installation

### Manual installation

1. Copy the `mhi_nova` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from Settings → Devices & Services.

### HACS / Custom Repository

If you use HACS, add this repository as a custom repository:

- Repository URL: https://github.com/flom89/mhiNova
- Category: Integration

Then search for "MHI Nova" in HACS and install it.

## Development

The integration is tested through Home Assistant’s integration test suite.

From the Home Assistant Core repository root, run:

```bash
python -m pytest -q tests/components/mhi_nova
```

## Notes

This folder is intended to be self-contained for use as a custom component, while still fitting into the Home Assistant Core test layout.
