# Architecture & Project Structure

This page describes the repository layout, the core components of the integration, and the data flow between the gateway and Home Assistant.

> **Deutsch:** Diese Seite beschreibt den Aufbau des Repositories, die Kernkomponenten und den Datenfluss zwischen Gateway und Home Assistant.

---

## Repository Structure

```
mhi_nova_link/
├── custom_components/
│   └── mhi_nova_link/           # Main integration package
│       ├── __init__.py          # Entry point: integration setup & teardown
│       ├── api.py               # HTTPS/GraphQL client for the NOVA RC gateway
│       ├── binary_sensor.py     # Binary sensor entities
│       ├── climate.py           # Climate entities (per-zone control)
│       ├── config_flow.py       # Config Flow & Options Flow (HA UI setup)
│       ├── const.py             # Constants & configuration keys
│       ├── coordinator.py       # DataUpdateCoordinator (periodic polling)
│       ├── entity.py            # Shared base class for all entities
│       ├── graphql.py           # GraphQL queries and mutations
│       ├── helpers.py           # Utility functions
│       ├── icons.json           # Entity icons
│       ├── manifest.json        # HA integration manifest (domain, version, IoT class)
│       ├── pyproject.toml       # Build configuration (setuptools)
│       ├── requirements.txt     # Python dependencies (empty – no extra deps)
│       ├── select.py            # Select entities (louvers)
│       ├── sensor.py            # Sensor entities (temperature, compressor, etc.)
│       ├── strings.json         # UI strings (English, base translation)
│       ├── switch.py            # Switch entities (3D Auto)
│       ├── brand/               # Brand assets (logo)
│       ├── translations/        # Localisations
│       │   ├── de.json          # German / Deutsch
│       │   ├── en.json          # English
│       │   ├── es.json          # Spanish / Español
│       │   ├── fr.json          # French / Français
│       │   └── it.json          # Italian / Italiano
│       └── tests/               # Integration tests
│           ├── __init__.py
│           ├── test_quality_flow.py
│           ├── test_sensor_entities.py
│           └── test_smoke.py
├── wiki/                        # This wiki documentation
├── CHANGELOG.md                 # Version history
├── LICENSE                      # GNU GPL v3.0
├── README.md                    # Quick-start documentation
├── SECURITY.md                  # Security policy
└── hacs.json                    # HACS metadata
```

---

## Technologies & Frameworks

| Technology | Purpose |
|---|---|
| **Home Assistant Core** | Integration platform, lifecycle, entity registry |
| **Python ≥ 3.13** | Implementation language |
| **aiohttp** | Asynchronous HTTP client for HTTPS communication with the gateway |
| **GraphQL** | Query protocol of the CompTrol 4Web NOVA RC gateway |
| **voluptuous** | Schema validation for Config/Options Flow |
| **pytest** | Test framework |
| **HACS** | Distribution and management of the custom integration |

---

## Component Overview

```
┌─────────────────────────────────────────────────────┐
│                   Home Assistant                     │
│                                                      │
│  ┌──────────────┐    ┌──────────────────────────┐   │
│  │  Config Flow  │    │  DataUpdateCoordinator   │   │
│  │ (config_flow) │    │    (coordinator.py)      │   │
│  └──────┬───────┘    └────────────┬─────────────┘   │
│         │                         │ periodic         │
│         │                         │ polling          │
│  ┌──────▼─────────────────────────▼─────────────┐   │
│  │            NovaRcApiClient (api.py)           │   │
│  │   • async_login()                            │   │
│  │   • async_get_zones()                        │   │
│  │   • async_get_time_series()                  │   │
│  │   • async_get_gpios()                        │   │
│  │   • async_get_notifications()                │   │
│  │   • async_get_gateway_update_information()   │   │
│  │   • async_set_zone_patch()                   │   │
│  └──────────────────────┬────────────────────────┘  │
│                          │ HTTPS + GraphQL            │
└──────────────────────────┼────────────────────────────┘
                           │
           ┌───────────────▼──────────────┐
           │  CompTrol 4Web NOVA RC        │
           │  (local gateway)              │
           └───────────────────────────────┘
```

---

## Data Flow

1. **Setup:** The Config Flow (`config_flow.py`) collects the host, username, password, and optional SSL fingerprint. The `NovaRcApiClient` performs a login call to validate the connection. For unknown self-signed certificates the fingerprint is discovered and stored automatically.

2. **Initialisation:** `__init__.py` creates the `NovaRcApiClient` and the `NovaRcDataUpdateCoordinator`. All platform modules (`climate`, `sensor`, `binary_sensor`, `select`, `switch`) register their entities with the coordinator.

3. **Polling – ZoneQueries:** The coordinator fetches data at the configured interval (`poll_interval`, default 15 s):
   - `async_get_zones()` – zone states (temperature, setpoint, mode, etc.)
   - `async_get_notifications()` – active system notifications
   - `async_get_gpios()` – Digital I/O states
   - `async_get_gateway_update_information()` – gateway software version & update status

4. **Polling – Timeseries:** Time-series data is fetched separately and throttled (`time_series_poll_interval`, default 60 s). Results are cached per zone to avoid redundant requests.

5. **Control:** Write operations (e.g. setpoint change, mode switch) are sent to the gateway as GraphQL mutations via `async_set_zone_patch()`.

6. **Entities:** Each entity inherits from the shared base class (`entity.py`) and consumes data provided by the coordinator.

---

## IoT Class

The integration is classified as **`local_polling`**: it actively polls the gateway on the local network and does not depend on any external cloud services.

---

## Entity Overview

| Platform | Example entities |
|---|---|
| `climate` | Climate zone (temperature, mode, fan speed) |
| `sensor` | Room temperature, setpoint, outdoor temperature, compressor frequency, current, power, gateway software version, temperature limits |
| `binary_sensor` | Compressor active, defrosting active, gateway update available, active notifications, Digital I/O states |
| `select` | Air guide louver, swing louver |
| `switch` | 3D Auto |
