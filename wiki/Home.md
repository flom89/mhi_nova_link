# MHI Nova Link – Übersicht

![MHI Nova Logo](../custom_components/mhi_nova_link/brand/logo.png)

**MHI Nova Link** ist eine benutzerdefinierte [Home Assistant](https://www.home-assistant.io/)-Integration, die Mitsubishi Heavy Industries (MHI) Klimaanlagen über das **CompTrol 4Web NOVA RC**-Gateway einbindet. Die Kommunikation erfolgt verschlüsselt über eine lokale HTTPS-Verbindung – ohne Cloud-Abhängigkeit.

> ⚠️ Diese Integration ist experimentell. Nutzung auf eigene Gefahr. Es sind keine Karten oder GUI-Elemente enthalten.

---

## Hauptfeatures

| Feature | Beschreibung |
|---|---|
| Lokale HTTPS-Verbindung | Kommuniziert direkt mit dem Gateway im Heimnetzwerk via SSL/TLS |
| Automatisches TLS-Fingerprint-Pinning | Erkennt und pinnt selbstsignierte Gateway-Zertifikate automatisch |
| Climate-Entitäten | Steuert Temperatur, Betriebsmodus und Lüfter pro Zone |
| Sensor-Entitäten | Raumtemperatur, Sollwert, Außentemperatur, Kompressor-Werte u. v. m. |
| Binary Sensor-Entitäten | Digital-IO-Zustände, Kompressor-/Abtaustatus, Gatewaywarnungen |
| Select-Entitäten | Lamellen- und Schwenklamellenposition |
| Switch-Entitäten | 3D Auto-Modus |
| Mehrsprachig | Übersetzungen für Englisch, Deutsch, Italienisch, Spanisch und Französisch |
| Config Flow & Options Flow | Einfache Einrichtung und Anpassung direkt über die HA-Oberfläche |
| HACS-kompatibel | Kann als Custom Repository über HACS installiert werden |

---

## Zielgruppe & Anwendungsfälle

- **Heimautomatisierungs-Enthusiasten**, die MHI-Klimaanlagen vollständig in Home Assistant integrieren möchten.
- **Gebäudemanager**, die mehrere Klimazonen zentral überwachen und steuern wollen.
- **Entwickler**, die eine lokale, datenschutzfreundliche Alternative zu Cloud-basierten Herstellerlösungen suchen.

Die Integration richtet sich an alle, die ein **CompTrol 4Web NOVA RC**-Gateway von STULZ S-Klima betreiben und dessen Klimazonen über Home Assistant automatisieren wollen.

---

## Weitere Wiki-Seiten

- [Erste Schritte (Getting Started)](Getting-Started.md)
- [Architektur & Projektstruktur](Architecture.md)
- [Entwickler-Guide (Contributing)](Contributing.md)
- [Troubleshooting & FAQ](Troubleshooting.md)
