# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added
- Added a separate timeseries polling interval option (`time_series_poll_interval`).
- Added cooling and heating temperature boundary sensors (min/max) per zone.
- Added indoor-unit sensors (temperature, setpoint, operation mode, fan speed) for zones with multiple indoor units.
- Added compressor current and derived compressor power sensors.
- Added broader regression coverage for sensor, select, switch, binary sensor, config flow, and climate command behavior.

### Changed
- Time-series fetching is now throttled and cached per zone, decoupled from zone query polling.
- Polling option labels were clarified in the UI (`ZoneQueries Polling Interval`, `Timeseries Polling Interval`).
- Zone-level mode, fan, and indoor-temperature sensors now rely on zone payload values only (no TS fallback).
- Select and switch setup now validates zone IDs and supports awaitable entity registration.
- Coordinator startup refresh now handles expected coordinator exceptions explicitly.

### Fixed
- Compressor frequency sensor values are now scaled correctly by dividing raw values by 10.
- Compressor active state now falls back to compressor frequency when direct TS active state is unavailable.
- Duplicate indoor-unit entities are prevented by deduplicating indoor unit IDs during setup.
- Enum/token normalization for TS boolean parsing was improved (including localized and templated values).
- Removed a no-op `else: pass` branch from the config flow.
- Manifest dependency metadata now matches the current aiohttp-based implementation.

### Removed
- Removed obsolete zone-level TS filter reminder binary sensor and its translation keys.
- Removed unused OutdoorUnit reverse-engineering query paths and schema fallback code.
- Removed unused module-level logger declarations in platform modules.
