# Installation and Setup

## Prerequisites

- A reachable **CompTrol 4Web NOVA RC** gateway on your LAN
- A dedicated gateway user account for Home Assistant
- Home Assistant with support for custom integrations

## Install via HACS (recommended)

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository:
   - URL: `https://github.com/flom89/mhi_nova_link`
   - Category: `Integration`
3. Search for **MHI Nova Link** and install.
4. Restart Home Assistant.

## Manual installation

1. Copy `/custom_components/mhi_nova_link` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Add the integration in Home Assistant

1. Go to **Settings → Devices & Services**.
2. Click **Add Integration**.
3. Search for **MHI Nova Link**.
4. Enter:
   - Gateway host (IP or hostname)
   - Username
   - Password
   - Optional SSL fingerprint

On success, a config entry named `CompTrol 4Web NOVA RC (<host>)` is created.

## TLS / SSL behavior

- Connection is always HTTPS.
- If the gateway uses a public-trust certificate, no fingerprint is usually needed.
- If the gateway uses a self-signed certificate and no fingerprint is provided, the integration tries to read and pin the certificate fingerprint automatically.
- You can override the fingerprint in integration options at any time.
