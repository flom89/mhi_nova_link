# Changelog

All notable changes to this project are documented in this file.

## [2.0.0] - 2026-08-03

### Refactoring
- Migrated runtime state handling to `ConfigEntry.runtime_data`.
- Centralized gateway device metadata generation for sensor and binary sensor entities.
- Added explicit config-entry diagnostics support.

### Cleanup
- Removed unused helper logic (`get_dataset_option_label`).
- Removed legacy poll-interval environment variable compatibility paths.
- Removed duplicated gateway device-info dictionary construction.

### Home Assistant compliance
- Added diagnostics manifest capability and secure diagnostics output with redaction.
- Added reauthentication flow (`reauth` + `reauth_confirm`) to recover from credential drift.
- Kept coordinator-based update architecture while improving typed runtime integration access.

### Performance and stability
- Preserved concurrent coordinator fetch model while reducing setup-state indirection.
- Continued to avoid telemetry impact on integration startup by keeping failures non-fatal.

### Testing
- Updated regression tests for runtime-data architecture changes.
- Added diagnostics test coverage.
- Updated normalizer tests for removed legacy configuration paths.

### Documentation
- Rewrote `README.md` with current setup, troubleshooting, diagnostics, and platform details.
- Refreshed contribution and security documentation for the 2.0.0 release baseline.

## [1.2.2] - 2026-08-03

### Maintenance
- Bumped version to 1.2.2 to align with the v1.2.2 release tag.

## [1.2.1] - 2026-07-30

### Fixed
- Fixed telemetry startup crash by using Home Assistant's canonical version constant.
- Telemetry now logs rejected HTTP responses as warnings, including response details for easier diagnostics.

### Changed
- Updated README and wiki documentation with telemetry behavior, opt-in details, and troubleshooting guidance.

### Removed
- Removed tracked Python bytecode cache artifacts from version control.

### Maintenance
- Added `.gitignore` rules for `__pycache__`, Python bytecode, and common test/tool caches.

## [1.2.0] - 2026-07

### Added
- Opt-in anonymous telemetry via Supabase to help prioritise future development.
- Anonymous ID is generated on first setup and stored in the config entry; never linked to personal data.
- Telemetry can be disabled at runtime via the `MHI_NOVALINK_DISABLE_ANALYTICS` environment variable.

### Changed
- `CONF_TIME_SERIES_POLL_INTERVAL` is now configurable via the options flow.
- Improved error handling and logging for GraphQL responses.

## [1.1.0] - 2025

### Added
- Select entities for louver and vane position (`3D Auto` mode).
- Switch entities for per-zone system-stop and 3D Auto.
- Binary sensor entity for indoor unit running state.
- Binary sensor entity for gateway software update availability.
- Per-zone time-series data polling with configurable interval.
- `NOVA_RC_TIME_SERIES_UPDATE_INTERVAL_SECONDS` environment variable override.

### Changed
- Coordinator now fetches GPIO states, notifications, and gateway update info on every poll.
- Improved TLS fingerprint TOFU (Trust On First Use) with automatic persistence.

## [1.0.0] - 2025

### Added
- Initial release: Home Assistant custom integration for CompTrol 4Web NOVA RC gateway.
- Climate entity with HVAC mode, fan speed, setpoint, and louver position controls.
- Sensor entities for room temperature, setpoint, fan speed, and outdoor unit diagnostics.
- Binary sensors for compressor active, defrost active, and filter sign.
- Config and options flows with host/credentials/TLS fingerprint configuration.
- GraphQL client (`NovaRcApiClient`) for the NOVA RC gateway API.
- TLS fingerprint TOFU discovery for self-signed gateway certificates.
- HACS manifest, translations (EN/DE/IT/ES/FR), and SECURITY.md.
