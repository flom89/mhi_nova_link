# Changelog

All notable changes to this project are documented in this file.

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
