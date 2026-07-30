# Entwickler-Guide (Contributing)

Diese Seite beschreibt, wie du eine lokale Entwicklungsumgebung einrichtest, den Code-Stil einhältst und Beiträge zum Projekt einreichst.

---

## Lokale Entwicklungsumgebung aufsetzen

### Voraussetzungen

- Python ≥ 3.13
- `pip` oder `uv` (empfohlen für schnelle Installationen)
- Git
- Eine laufende Home Assistant-Instanz (für manuelle Tests)

### Repository klonen

```bash
git clone https://github.com/flom89/mhi_nova_link.git
cd mhi_nova_link
```

### Abhängigkeiten installieren

Die Integration selbst hat keine zusätzlichen Python-Laufzeitabhängigkeiten. Für Tests werden Home Assistant und `pytest` benötigt:

```bash
pip install homeassistant pytest pytest-asyncio pytest-homeassistant-custom-component
```

Alternativ mit `uv`:

```bash
uv pip install homeassistant pytest pytest-asyncio pytest-homeassistant-custom-component
```

### Integration für die Entwicklung einbinden

Kopiere (oder verknüpfe) den Ordner `custom_components/mhi_nova_link` in das `custom_components`-Verzeichnis deiner Home Assistant-Instanz und starte HA neu.

---

## Tests ausführen

Die Testsuite befindet sich in `custom_components/mhi_nova_link/tests/`. Führe alle Tests aus dem Repository-Root aus:

```bash
pytest -q custom_components/mhi_nova_link/tests
```

Für ausführliche Ausgabe:

```bash
pytest -v custom_components/mhi_nova_link/tests
```

### Testdateien

| Datei | Inhalt |
|---|---|
| `test_smoke.py` | Grundlegende Smoke-Tests (Integration lädt korrekt) |
| `test_sensor_entities.py` | Sensor-Entitäten, Skalierung, Zustandslogik |
| `test_quality_flow.py` | Config Flow, Options Flow, Fehlerbehandlung |

---

## Coding-Standards

- **Sprache:** Python 3.13+, strenge Typisierung (`from typing import Final`, Type Hints überall)
- **Asynchronität:** Alle I/O-Operationen sind `async`/`await`-basiert (aiohttp)
- **Logging:** Verwende das modulspezifische Logger-Objekt (`_LOGGER = logging.getLogger(__name__)`); keine `print`-Statements
- **Konstanten:** Alle wiederverwendeten Strings und Werte gehören in `const.py` als `Final`
- **Fehlerbehandlung:** Verwende die spezifischen Exceptions aus `api.py` (`CannotConnect`, `InvalidAuth`, `InvalidCertificate`)
- **Entitäten:** Neue Entitäten erben von der Basisklasse in `entity.py`
- **Übersetzungen:** Jede neue UI-sichtbare Zeichenkette muss in `strings.json` und alle Sprachdateien unter `translations/` aufgenommen werden
- **Keine zusätzlichen Abhängigkeiten** ohne ausdrückliche Begründung – `requirements.txt` soll leer bleiben

### Stil-Empfehlungen

- Folge dem [Home Assistant-Coding-Style](https://developers.home-assistant.io/docs/development_guidelines)
- Verwende `ruff` als Linter/Formatter (falls im Projekt konfiguriert)
- Halte Funktionen kurz und fokussiert auf eine Aufgabe

---

## Git-Workflow

### Branches

| Branch-Typ | Schema | Beispiel |
|---|---|---|
| Feature | `feature/<kurzbeschreibung>` | `feature/add-humidity-sensor` |
| Bugfix | `fix/<kurzbeschreibung>` | `fix/tls-fingerprint-validation` |
| Dokumentation | `docs/<kurzbeschreibung>` | `docs/update-wiki` |

### Commit-Nachrichten

Schreibe prägnante, aussagekräftige Commit-Nachrichten im Imperativ:

```
Add compressor power sensor derived from current and frequency
Fix TLS fingerprint normalization for uppercase hex input
Update German translations for options flow labels
```

### Pull-Request-Regeln

1. **Fork** das Repository und erstelle einen Branch von `main`.
2. Stelle sicher, dass **alle Tests grün** sind (`pytest -q`).
3. Beschreibe im PR-Body:
   - **Was** wurde geändert und **warum**
   - Betroffene Entitäten oder Konfigurationsfelder
   - Ggf. Testabdeckung
4. Referenziere verwandte Issues mit `Fixes #<issue-nr>` oder `Closes #<issue-nr>`.
5. Der Code muss **review-bereit** sein – keine WIP-Commits im finalen PR.

### Sicherheit

Melde Sicherheitslücken **nicht** als öffentliche Issues. Nutze stattdessen den [GitHub Security Advisory](https://github.com/flom89/mhi_nova_link/security/advisories/new)-Mechanismus. Weitere Details in [SECURITY.md](../SECURITY.md).

---

## Neue Entitäten hinzufügen

1. Erstelle die Entitätslogik in der passenden Plattformdatei (`sensor.py`, `binary_sensor.py` etc.) oder lege eine neue Datei an.
2. Registriere die Entität in `__init__.py` unter den Plattformen.
3. Füge den Entitätsnamen und -zustände in `strings.json` und alle `translations/*.json`-Dateien ein.
4. Ergänze einen Test in `tests/test_sensor_entities.py` oder einer passenden Testdatei.
5. Aktualisiere `CHANGELOG.md` unter `[Unreleased] → Added`.
