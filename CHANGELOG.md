# Changelog

All notable changes to this project are documented in this file.

### Added
- Added a separate timeseries polling interval option (`time_series_poll_interval`).
- Added cooling/heating temperature boundary sensors (min/max) per zone.
- Added indoor-unit sensors (temperature, setpoint, operation mode, fan speed) for zones with multiple indoor units.
- Added broader regression coverage for sensor/select/switch/binary-sensor setup and option handling.

### Changed
- Time-series fetching is now throttled and cached per zone, decoupled from zone query polling.
- Polling option labels are now clearer in the UI: `ZoneQueries Polling Interval` and `Timeseries Polling Interval`.
- Zone-level mode/fan/indoor-temperature sensors now use zone query values only (no TS fallback).
- Compressor activity now falls back to compressor frequency when direct TS active state is unavailable.
- Select and switch platform setup now validates zone IDs and supports awaitable entity registration.
- TS-derived entity labels are consistently prefixed with `TS_` in translation assets.

### Removed
- Removed obsolete zone-level TS filter reminder binary sensor to avoid duplicate diagnostics.
- Removed obsolete translation keys for the retired zone-level TS filter reminder sensor.

### Fixed
- Avoided duplicate indoor-unit entities by deduplicating indoor unit IDs during setup.
- Improved enum/token normalization for TS boolean parsing (including localized and templated values).
- Updated static-analysis compatibility and import/exception hygiene in touched modules.
