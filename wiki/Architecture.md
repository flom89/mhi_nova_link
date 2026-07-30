# Architektur & Projektstruktur

Diese Seite beschreibt den Aufbau des Repositories, die Kernkomponenten der Integration und den Datenfluss zwischen Gateway und Home Assistant.

---

## Repository-Struktur

```
mhi_nova_link/
├── custom_components/
│   └── mhi_nova_link/           # Haupt-Integrationspaket
│       ├── __init__.py          # Einstiegspunkt: Setup & Teardown der Integration
│       ├── api.py               # HTTPS/GraphQL-Client für das NOVA RC-Gateway
│       ├── binary_sensor.py     # Binary Sensor-Entitäten
│       ├── climate.py           # Climate-Entitäten (Steuerung pro Zone)
│       ├── config_flow.py       # Config Flow & Options Flow (HA-UI-Einrichtung)
│       ├── const.py             # Konstanten & Konfigurationsschlüssel
│       ├── coordinator.py       # DataUpdateCoordinator (zyklisches Polling)
│       ├── entity.py            # Gemeinsame Basisklasse für alle Entitäten
│       ├── graphql.py           # GraphQL-Abfragen und Mutationen
│       ├── helpers.py           # Hilfsfunktionen
│       ├── icons.json           # Entitäts-Icons
│       ├── manifest.json        # HA-Integrationsmanifest (Domain, Version, IoT-Klasse)
│       ├── pyproject.toml       # Build-Konfiguration (setuptools)
│       ├── requirements.txt     # Python-Abhängigkeiten (leer – keine extra deps)
│       ├── select.py            # Select-Entitäten (Lamellen)
│       ├── sensor.py            # Sensor-Entitäten (Temperatur, Kompressor etc.)
│       ├── strings.json         # UI-Texte (Englisch, Basis-Übersetzung)
│       ├── switch.py            # Switch-Entitäten (3D Auto)
│       ├── brand/               # Marken-Assets (Logo)
│       ├── translations/        # Lokalisierungen
│       │   ├── de.json          # Deutsch
│       │   ├── en.json          # Englisch
│       │   ├── es.json          # Spanisch
│       │   ├── fr.json          # Französisch
│       │   └── it.json          # Italienisch
│       └── tests/               # Integrationstests
│           ├── __init__.py
│           ├── test_quality_flow.py
│           ├── test_sensor_entities.py
│           └── test_smoke.py
├── wiki/                        # Diese Wiki-Dokumentation
├── CHANGELOG.md                 # Versionshistorie
├── LICENSE                      # GNU GPL v3.0
├── README.md                    # Kurzdokumentation
├── SECURITY.md                  # Sicherheitsrichtlinie
└── hacs.json                    # HACS-Metadaten
```

---

## Verwendete Technologien & Frameworks

| Technologie | Zweck |
|---|---|
| **Home Assistant Core** | Integrationsplattform, Lifecycle, Entitäts-Registry |
| **Python ≥ 3.13** | Implementierungssprache |
| **aiohttp** | Asynchroner HTTP-Client für HTTPS-Kommunikation mit dem Gateway |
| **GraphQL** | Abfrageprotokoll des CompTrol 4Web NOVA RC-Gateways |
| **voluptuous** | Schema-Validierung für Config/Options Flow |
| **pytest** | Test-Framework |
| **HACS** | Verwaltung und Verteilung der Custom Integration |

---

## Komponentenübersicht

```
┌─────────────────────────────────────────────────────┐
│                   Home Assistant                     │
│                                                      │
│  ┌──────────────┐    ┌──────────────────────────┐   │
│  │  Config Flow  │    │  DataUpdateCoordinator   │   │
│  │ (config_flow) │    │    (coordinator.py)      │   │
│  └──────┬───────┘    └────────────┬─────────────┘   │
│         │                         │ periodisches     │
│         │                         │ Polling          │
│  ┌──────▼─────────────────────────▼─────────────┐   │
│  │              NovaRcApiClient (api.py)         │   │
│  │   • async_login()                            │   │
│  │   • async_get_zones()                        │   │
│  │   • async_get_time_series()                  │   │
│  │   • async_get_gpios()                        │   │
│  │   • async_get_notifications()                │   │
│  │   • async_get_gateway_update_information()   │   │
│  │   • async_set_zone_patch()                   │   │
│  └──────────────────────┬────────────────────────┘  │
│                          │ HTTPS + GraphQL            │
└──────────────────────────┼─────────────────────────-─┘
                           │
           ┌───────────────▼──────────────┐
           │  CompTrol 4Web NOVA RC        │
           │  (lokales Gateway)            │
           └───────────────────────────────┘
```

---

## Datenfluss

1. **Einrichtung:** Der Config Flow (`config_flow.py`) nimmt Host, Benutzername, Passwort und optionalen SSL-Fingerabdruck entgegen. Der `NovaRcApiClient` führt einen Login-Aufruf durch, um die Verbindung zu validieren. Bei unbekannten selbstsignierten Zertifikaten wird der Fingerabdruck automatisch ermittelt und gespeichert.

2. **Initialisierung:** `__init__.py` erstellt den `NovaRcApiClient` und den `NovaRcDataUpdateCoordinator`. Alle Plattformmodule (`climate`, `sensor`, `binary_sensor`, `select`, `switch`) registrieren ihre Entitäten beim Coordinator.

3. **Polling (ZoneQueries):** Der Coordinator ruft im konfigurierten Intervall (`poll_interval`, Standard 15 s) folgende Endpunkte ab:
   - `async_get_zones()` – Zonenzustände (Temperatur, Sollwert, Modus etc.)
   - `async_get_notifications()` – aktive Systembenachrichtigungen
   - `async_get_gpios()` – Digital-IO-Zustände
   - `async_get_gateway_update_information()` – Gateway-Softwareversion & Update-Status

4. **Polling (Timeseries):** Zeitreihendaten werden separat und gedrosselt abgefragt (`time_series_poll_interval`, Standard 60 s). Die Daten werden pro Zone gecacht, um redundante Anfragen zu vermeiden.

5. **Steuerung:** Schreiboperationen (z. B. Sollwertänderung, Moduswechsel) werden über `async_set_zone_patch()` als GraphQL-Mutation an das Gateway gesendet.

6. **Entitäten:** Jede Entität erbt von der gemeinsamen Basisklasse (`entity.py`) und konsumiert die vom Coordinator bereitgestellten Daten.

---

## IoT-Klasse

Die Integration ist als **`local_polling`** klassifiziert: Sie fragt das Gateway aktiv und lokal ab und ist daher nicht auf externe Cloud-Dienste angewiesen.

---

## Entitäts-Übersicht

| Plattform | Beispiel-Entitäten |
|---|---|
| `climate` | Klimazone (Temperatur, Modus, Lüfterstufe) |
| `sensor` | Raumtemperatur, Sollwert, Außentemperatur, Kompressorfrequenz, Strom, Leistung, Gateway-Softwareversion, Temperaturgrenzen |
| `binary_sensor` | Kompressor aktiv, Abtauen aktiv, Gateway-Update verfügbar, Benachrichtigungen aktiv, Digital-IO-Zustände |
| `select` | Luftführungslamelle, Schwenklamelle |
| `switch` | 3D Auto |
