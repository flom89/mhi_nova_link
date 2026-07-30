# Erste Schritte (Getting Started)

Diese Seite beschreibt alle notwendigen Schritte, um **MHI Nova Link** in Home Assistant zu installieren und zu konfigurieren.

---

## Systemvoraussetzungen

| Voraussetzung | Details |
|---|---|
| Home Assistant | Aktuelle Version mit Unterstützung für Custom Integrations |
| Python | ≥ 3.13 (wird von Home Assistant bereitgestellt) |
| Gateway | CompTrol 4Web NOVA RC, im lokalen Netzwerk erreichbar via HTTPS |
| Gateway-Benutzer | Dediziertes Benutzerkonto auf dem Gateway für Home Assistant |
| HACS *(optional)* | Empfohlen für einfache Installation und Updates |

Die Integration hat **keine zusätzlichen Python-Abhängigkeiten** außerhalb des Home Assistant Core (`aiohttp` wird aus HA genutzt).

---

## Installation

### Option A – HACS (empfohlen)

1. Öffne HACS in Home Assistant.
2. Navigiere zu **Integrationen** → **Benutzerdefinierte Repositories**.
3. Füge das Repository hinzu:
   - **URL:** `https://github.com/flom89/mhi_nova_link`
   - **Kategorie:** Integration
4. Suche in HACS nach **MHI Nova Link** und klicke auf **Installieren**.
5. Starte Home Assistant neu.

### Option B – Manuelle Installation

1. Lade dieses Repository herunter (ZIP oder `git clone`).
2. Kopiere den Ordner `custom_components/mhi_nova_link` in dein Home Assistant `custom_components`-Verzeichnis.
   ```
   <config>/
   └── custom_components/
       └── mhi_nova_link/
   ```
3. Starte Home Assistant neu.

---

## Konfiguration

### Schritt 1 – Benutzer auf dem Gateway anlegen

Erstelle auf dem CompTrol 4Web NOVA RC einen dedizierten Benutzer für Home Assistant. Verwende **keine** Administrator-Zugangsdaten des Gateways.

### Schritt 2 – Integration hinzufügen

1. Navigiere in Home Assistant zu **Einstellungen → Geräte & Dienste**.
2. Klicke auf **Integration hinzufügen** und suche nach **MHI Nova Link**.
3. Fülle das Einrichtungsformular aus:

| Feld | Beschreibung | Pflichtfeld |
|---|---|---|
| `host` | IP-Adresse oder Hostname des Gateways | ✅ |
| `username` | Benutzername des Gateway-Kontos | ✅ |
| `password` | Passwort des Gateway-Kontos | ✅ |
| `ssl_fingerprint` | SHA256-Fingerabdruck des TLS-Zertifikats | ❌ |

> **Hinweis zum SSL-Fingerabdruck:** Wird das Feld leer gelassen, versucht die Integration, den Fingerabdruck des selbstsignierten Zertifikats automatisch zu ermitteln und zu pinnen.

### Schritt 3 – Optionen anpassen (optional)

Nach der Einrichtung können folgende Optionen jederzeit unter **Einstellungen → Geräte & Dienste → MHI Nova Link → Konfigurieren** geändert werden:

| Option | Standard | Beschreibung |
|---|---|---|
| `poll_interval` | `15` Sekunden | Abfrageintervall für Zonen-Daten (ZoneQueries) |
| `time_series_poll_interval` | `60` Sekunden | Abfrageintervall für Zeitreihendaten (Timeseries) |
| `ssl_fingerprint` | – | SHA256-Fingerabdruck manuell setzen oder überschreiben |
| `username` | – | Benutzername aktualisieren |
| `password` | – | Passwort aktualisieren |

### Umgebungsvariablen (fortgeschritten)

Für Szenarien ohne UI-Konfiguration (z. B. Docker, CI) können die Polling-Intervalle auch über Umgebungsvariablen gesetzt werden:

| Variable | Beschreibung |
|---|---|
| `NOVA_RC_UPDATE_INTERVAL_SECONDS` | Abfrageintervall für Zonen-Daten in Sekunden |
| `NOVA_RC_TIME_SERIES_UPDATE_INTERVAL_SECONDS` | Abfrageintervall für Zeitreihendaten in Sekunden |
| `MHI_NOVALINK_UPDATE_INTERVAL_SECONDS` | Legacy-Alias für `NOVA_RC_UPDATE_INTERVAL_SECONDS` |
| `MHI_NOVALINK_TIME_SERIES_UPDATE_INTERVAL_SECONDS` | Legacy-Alias für die Zeitreihen-Intervallvariable |

---

## Anwendung starten

Die Integration wird nach dem Neustart von Home Assistant automatisch gestartet. Es sind keine separaten Startbefehle erforderlich.

Um die Integration manuell neu zu laden, gehe zu **Einstellungen → Geräte & Dienste → MHI Nova Link → ⋮ → Neu laden**.

---

## Nächste Schritte

- [Architektur & Projektstruktur](Architecture.md) – Wie ist der Code aufgebaut?
- [Entwickler-Guide](Contributing.md) – Eigene Änderungen beitragen
- [Troubleshooting & FAQ](Troubleshooting.md) – Hilfe bei Problemen
