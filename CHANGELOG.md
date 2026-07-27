# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

### Added
- Options flow now supports updating gateway username and password after setup.
- Added gateway software/update entities and richer diagnostics.
- Added targeted GetZone polling after zone startup to fetch airflow positions reliably.
- Added regression tests for startup airflow polling stop conditions.
- Added TLS fingerprint auto-discovery and pinning fallback for self-signed certificates.

### Changed
- Reworked airflow value behavior: louver/vane values are no longer read from time-series fallback.
- Polling loop now stops immediately when airflow values are present and clamps sleep to remaining timeout.
- Indoor capacity sensor unit updated to kW.
- Indoor capacity values are normalized from deci-kW to kW (e.g., 15.0 -> 1.5 kW).
- Integration display naming updated to CompTrol 4Web NOVA RC where applicable.

### Fixed
- Fixed locale translation issues and synchronized translation assets.
- Improved SSL and authentication error handling around GraphQL calls.
- Improved startup consistency for zone state refreshes after turning systems on.
