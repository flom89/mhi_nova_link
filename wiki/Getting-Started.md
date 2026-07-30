# Getting Started

This page covers everything you need to install and configure **MHI Nova Link** in Home Assistant.

> **Deutsch:** Diese Seite beschreibt Installation und Konfiguration von MHI Nova Link in Home Assistant.

---

## System Requirements

| Requirement | Details |
|---|---|
| Home Assistant | Current release with custom integration support |
| Python | ≥ 3.13 (provided by Home Assistant) |
| Gateway | CompTrol 4Web NOVA RC, reachable on the local network via HTTPS |
| Gateway user account | A dedicated user account on the gateway for Home Assistant |
| HACS *(optional)* | Recommended for easy installation and future updates |

The integration has **no additional Python runtime dependencies** beyond Home Assistant Core (`aiohttp` is used from HA itself).

---

## Installation

### Option A – HACS (recommended)

1. Open HACS in Home Assistant.
2. Navigate to **Integrations** → **Custom Repositories**.
3. Add the repository:
   - **URL:** `https://github.com/flom89/mhi_nova_link`
   - **Category:** Integration
4. Search for **MHI Nova Link** in HACS and click **Install**.
5. Restart Home Assistant.

### Option B – Manual Installation

1. Download this repository (ZIP or `git clone`).
2. Copy the `custom_components/mhi_nova_link` folder into your Home Assistant `custom_components` directory:
   ```
   <config>/
   └── custom_components/
       └── mhi_nova_link/
   ```
3. Restart Home Assistant.

---

## Configuration

### Step 1 – Create a gateway user

Create a dedicated user for Home Assistant on the CompTrol 4Web NOVA RC. Do **not** use the gateway's administrator credentials.

### Step 2 – Add the integration

1. In Home Assistant, navigate to **Settings → Devices & Services**.
2. Click **Add Integration** and search for **MHI Nova Link**.
3. Fill in the setup form:

| Field | Description | Required |
|---|---|---|
| `host` | IP address or hostname of the gateway | ✅ |
| `username` | Gateway account username | ✅ |
| `password` | Gateway account password | ✅ |
| `ssl_fingerprint` | SHA256 fingerprint of the TLS certificate | ❌ |

> **SSL Fingerprint note:** If left empty, the integration automatically discovers and pins the fingerprint of the gateway's self-signed certificate.

### Step 3 – Adjust options (optional)

After setup, the following options can be changed at any time under **Settings → Devices & Services → MHI Nova Link → Configure**:

| Option | Default | Description |
|---|---|---|
| `poll_interval` | `15` seconds | Polling interval for zone data (ZoneQueries) |
| `time_series_poll_interval` | `60` seconds | Polling interval for time-series data |
| `ssl_fingerprint` | – | Manually set or override the SHA256 fingerprint |
| `username` | – | Update the gateway username |
| `password` | – | Update the gateway password |

### Environment Variables (advanced)

For scenarios without UI configuration (e.g. Docker, CI), polling intervals can also be set via environment variables:

| Variable | Description |
|---|---|
| `NOVA_RC_UPDATE_INTERVAL_SECONDS` | Zone query polling interval in seconds |
| `NOVA_RC_TIME_SERIES_UPDATE_INTERVAL_SECONDS` | Time-series polling interval in seconds |
| `MHI_NOVALINK_UPDATE_INTERVAL_SECONDS` | Legacy alias for `NOVA_RC_UPDATE_INTERVAL_SECONDS` |
| `MHI_NOVALINK_TIME_SERIES_UPDATE_INTERVAL_SECONDS` | Legacy alias for the time-series interval variable |

---

## Starting the Application

The integration starts automatically after Home Assistant restarts. No separate start command is required.

To manually reload the integration, go to **Settings → Devices & Services → MHI Nova Link → ⋮ → Reload**.

---

## Next Steps

- [Architecture & Project Structure](Architecture.md) – How is the code structured?
- [Developer Guide](Contributing.md) – How to contribute changes
- [Troubleshooting & FAQ](Troubleshooting.md) – Help with common problems
