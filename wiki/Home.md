# MHI Nova Link – Overview

![MHI Nova Logo](../custom_components/mhi_nova_link/brand/logo.png)

**MHI Nova Link** is a custom [Home Assistant](https://www.home-assistant.io/) integration that connects Mitsubishi Heavy Industries (MHI) air conditioners via a **CompTrol 4Web NOVA RC** gateway. All communication is encrypted over a local HTTPS connection — no cloud dependency required.

> ⚠️ This integration is experimental. Use at your own risk. No cards or GUI elements are included.

---

## Key Features

| Feature | Description |
|---|---|
| Local HTTPS connection | Communicates directly with the gateway on the local network via SSL/TLS |
| Automatic TLS fingerprint pinning | Discovers and pins self-signed gateway certificates automatically |
| Climate entities | Controls temperature, operation mode, and fan speed per zone |
| Sensor entities | Room temperature, setpoint, outdoor temperature, compressor values, and more |
| Binary sensor entities | Digital I/O states, compressor/defrost status, gateway alerts |
| Select entities | Air guide louver and swing louver position |
| Switch entities | 3D Auto mode |
| Multilingual | Translations for English, German, Italian, Spanish, and French |
| Config Flow & Options Flow | Easy setup and configuration directly from the HA UI |
| HACS-compatible | Can be installed as a custom repository via HACS |

---

## Target Audience & Use Cases

- **Home automation enthusiasts** who want to fully integrate MHI air conditioners into Home Assistant.
- **Building managers** who need centralised monitoring and control of multiple climate zones.
- **Developers** looking for a local, privacy-friendly alternative to manufacturer cloud solutions.

This integration is intended for anyone operating a **CompTrol 4Web NOVA RC** gateway by STULZ S-Klima and wanting to automate their climate zones through Home Assistant.

---

> **Deutsch / German:** MHI Nova Link ist eine benutzerdefinierte Home Assistant-Integration für Mitsubishi Heavy Industries Klimaanlagen über das CompTrol 4Web NOVA RC-Gateway. Die Kommunikation erfolgt lokal über HTTPS – ohne Cloud-Abhängigkeit.

---

## Wiki Pages

- [Getting Started](Getting-Started.md)
- [Architecture & Project Structure](Architecture.md)
- [Developer Guide (Contributing)](Contributing.md)
- [Troubleshooting & FAQ](Troubleshooting.md)
