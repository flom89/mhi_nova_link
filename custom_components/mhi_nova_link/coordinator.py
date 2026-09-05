"""Coordinate periodic data updates for NOVA_RC."""

import asyncio
import logging
import os
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, InvalidAuth, InvalidCertificate, NovaRcApiClient
from .const import (
    CONF_GPIO_RESTORE_ENABLED,
    CONF_GPIO_RESTORE_FREE_COOLING,
    CONF_GPIO_RESTORE_SYSTEM_STOP,
    CONF_GPIO_RESTORE_VALIDITY_MINUTES,
    CONF_POLL_INTERVAL,
    DEFAULT_GPIO_RESTORE_ENABLED,
    DEFAULT_GPIO_RESTORE_FREE_COOLING,
    DEFAULT_GPIO_RESTORE_SYSTEM_STOP,
    DEFAULT_GPIO_RESTORE_VALIDITY_MINUTES,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    UPDATE_INTERVAL_ENV_VAR,
    ZONE_OFFLINE_DEBOUNCE_POLLS,
)

_LOGGER = logging.getLogger(__name__)

GPIO_SOURCE_SYSTEM_STOP = "SYSTEM_STOP"
GPIO_SOURCE_FREE_COOLING = "FREE_COOLING"
_RESTORE_STORE_VERSION = 1
_RESTORE_FIRST_WRITEBACK_DELAY_SECONDS = 10
_RESTORE_RECHECK_DELAY_SECONDS = 5
_RESTORE_POST_RETRY_VERIFY_DELAY_SECONDS = 2
_RESTORE_GATEWAY_VERIFY_ATTEMPTS = 2
_RESTORE_GATEWAY_VERIFY_RETRY_DELAY_SECONDS = 1


class NovaRcDataUpdateCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinate periodic data updates from the gateway."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: NovaRcApiClient,
        entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator with the configured poll interval."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=_get_update_interval(entry),
            config_entry=entry,
        )
        self.api = api
        self.config_entry = entry
        self._zone_cache: dict[int, dict[str, Any]] = {}
        self._zone_missing_streak: dict[int, int] = {}
        self.gpios: dict[str, bool] = {}
        self.gpio_active_high: dict[str, bool] = {}
        self.gateway_update: dict[str, Any] = {}
        store_key = (
            f"{DOMAIN}_restore_state_{entry.entry_id}" if entry else f"{DOMAIN}_restore_state"
        )
        self._restore_store: Store[dict[str, Any]] | None = None
        if hasattr(hass, "data") and hasattr(hass, "config"):
            self._restore_store = Store(
                hass,
                _RESTORE_STORE_VERSION,
                store_key,
            )
        self._restore_state: dict[str, Any] = {
            "snapshots": {
                GPIO_SOURCE_SYSTEM_STOP: None,
                GPIO_SOURCE_FREE_COOLING: None,
            }
        }
        self._restore_state_loaded = False
        self._restore_lock = asyncio.Lock()
        self._restore_validation_tasks: dict[str, asyncio.Task[None]] = {}
        self._time_series_enrichment_task: asyncio.Task[None] | None = None
        self._time_series_enrichment_generation = 0
        self._last_user_interaction_at: datetime | None = None
        self._restore_status_by_source: dict[str, dict[str, Any]] = {
            GPIO_SOURCE_SYSTEM_STOP: {"state": "idle"},
            GPIO_SOURCE_FREE_COOLING: {"state": "idle"},
        }
        self._restore_last_event: dict[str, Any] = {
            "source": None,
            "state": "idle",
            "updated_at": None,
        }

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch the latest zone data from the GraphQL gateway."""
        await self._async_ensure_restore_state_loaded()
        try:
            take_initial_zones = getattr(self.api, "take_initial_zones", None)
            initial_zones = take_initial_zones() if take_initial_zones else None
            zones_request = (
                asyncio.sleep(0, result=initial_zones)
                if initial_zones is not None
                else self.api.async_get_zones()
            )
            data, notifications, gpios_payload, gateway_update = await asyncio.gather(
                zones_request,
                self.api.async_get_notifications(),
                self.api.async_get_gpios(),
                self.api.async_get_gateway_update_information(),
            )
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except InvalidCertificate as err:
            raise UpdateFailed(f"TLS certificate validation failed: {err}") from err
        except CannotConnect as err:
            raise UpdateFailed(f"Error loading NOVA_RC data: {err}") from err
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error while fetching NOVA_RC data")
            raise UpdateFailed(f"Unexpected error: {err}") from err

        if notifications:
            for zone in data:
                zone["notifications"] = notifications

        gpios: dict[str, bool]
        gpio_active_high: dict[str, bool]
        if isinstance(gpios_payload, tuple):
            gpios, gpio_active_high = gpios_payload
        else:
            gpios = gpios_payload
            gpio_active_high = {}

        self.gpios = gpios
        self.gpio_active_high = gpio_active_high
        previous_installed_version = self.gateway_update.get("installed_version")
        self.gateway_update = gateway_update
        if (
            self.gateway_update.get("installed_version") is None
            and previous_installed_version is not None
        ):
            self.gateway_update["installed_version"] = previous_installed_version
        data = self._stabilize_zones(data)
        self._async_schedule_time_series_enrichment(data)
        return data

    def _stabilize_zones(self, zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Smooth out transient zone drop-outs reported by the gateway bus.

        The gateway occasionally reports a zone as briefly offline (either by
        omitting it from the response as an ``OfflineZone``, or by reporting
        ``available: False`` on it) for a single poll cycle even though the
        zone bus is otherwise healthy. Treating every such blip as a real
        outage caused zone entities to flap between their last known value
        and "unknown" every few seconds. A zone is only surfaced as
        unavailable once it has been missing/offline for several consecutive
        polls, and the last known-good payload keeps being served (marked
        unavailable) instead of disappearing entirely.
        """
        stabilized: list[dict[str, Any]] = []
        seen_zone_ids: set[int] = set()

        for zone in zones:
            zone_id = zone.get("zoneId")
            if not isinstance(zone_id, int):
                stabilized.append(zone)
                continue

            seen_zone_ids.add(zone_id)
            if zone.get("available") is False:
                stabilized.append(self._debounce_offline_zone(zone_id, zone))
                continue

            self._zone_missing_streak[zone_id] = 0
            self._zone_cache[zone_id] = zone
            stabilized.append(zone)

        for zone_id, cached in list(self._zone_cache.items()):
            if zone_id in seen_zone_ids:
                continue
            stabilized.append(self._debounce_offline_zone(zone_id, cached))

        return stabilized

    def _debounce_offline_zone(self, zone_id: int, fallback: dict[str, Any]) -> dict[str, Any]:
        """Return the payload to use for a zone reported missing/offline."""
        streak = self._zone_missing_streak.get(zone_id, 0) + 1
        self._zone_missing_streak[zone_id] = streak
        cached = self._zone_cache.get(zone_id, fallback)

        if streak < ZONE_OFFLINE_DEBOUNCE_POLLS:
            # Absorb the blip: keep reporting the last known-good data.
            return cached

        offline_zone = dict(cached)
        offline_zone["available"] = False
        self._zone_cache[zone_id] = offline_zone
        return offline_zone

    def _async_schedule_time_series_enrichment(self, zones: list[dict[str, Any]]) -> None:
        """Schedule optional historical data after the lightweight refresh completes."""
        if not hasattr(self.api, "async_enrich_time_series"):
            return
        self._time_series_enrichment_generation += 1
        if self._time_series_enrichment_task and not self._time_series_enrichment_task.done():
            self._time_series_enrichment_task.cancel()
        self._time_series_enrichment_task = self.hass.async_create_task(
            self._async_enrich_time_series(zones, self._time_series_enrichment_generation)
        )

    async def _async_enrich_time_series(self, zones: list[dict[str, Any]], generation: int) -> None:
        """Fetch historical data sequentially and publish it when complete."""
        try:
            await self.api.async_enrich_time_series(zones)
        except asyncio.CancelledError:
            raise
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Time-series enrichment failed")
            return

        if generation == self._time_series_enrichment_generation:
            self.async_set_updated_data(zones)

    @property
    def is_system_stop_active(self) -> bool:
        """Return whether operation lock is currently active."""
        active_high = self.gpio_active_high.get(GPIO_SOURCE_SYSTEM_STOP, True)
        return not active_high

    @property
    def is_user_control_locked(self) -> bool:
        """Return whether user write controls should be locked."""
        return self.is_system_stop_active

    async def async_capture_restore_snapshot(self, source: str) -> None:
        """Persist the current zone state for later restore."""
        if not self._restore_enabled_for_source(source):
            self._set_restore_status(source, state="restore_disabled")
            return

        await self._async_ensure_restore_state_loaded()

        zones_snapshot: list[dict[str, Any]] = []
        for zone in self.data:
            zone_id = zone.get("zoneId")
            if not isinstance(zone_id, int):
                continue

            snapshot_zone: dict[str, Any] = {"zoneId": zone_id}
            for key in (
                "running",
                "operationMode",
                "setpoint",
                "fanSpeed",
                "louverPosition",
                "vanePosition",
                "flap3dAuto",
            ):
                if key in zone:
                    snapshot_zone[key] = zone[key]

            zones_snapshot.append(snapshot_zone)

        if not zones_snapshot:
            self._set_restore_status(source, state="snapshot_empty")
            return

        snapshot = {
            "created_at": datetime.now(UTC).isoformat(),
            "source": source,
            "zones": zones_snapshot,
        }

        async with self._restore_lock:
            self._restore_state["snapshots"][source] = snapshot
            if self._restore_store is not None:
                await self._restore_store.async_save(self._restore_state)

        self._set_restore_status(
            source,
            state="snapshot_captured",
            zone_count=len(zones_snapshot),
        )

    async def async_restore_after_release(self, source: str) -> None:
        """Restore previously saved zone state after a lock source is released."""
        if not self._restore_enabled_for_source(source):
            self._set_restore_status(source, state="restore_disabled")
            return

        await self._async_ensure_restore_state_loaded()
        snapshot = self._restore_state.get("snapshots", {}).get(source)
        if not isinstance(snapshot, dict):
            self._set_restore_status(source, state="snapshot_missing")
            return

        if self._snapshot_is_expired(snapshot):
            _LOGGER.debug("Skipping restore for %s because snapshot is expired", source)
            self._set_restore_status(source, state="snapshot_expired")
            await self._async_clear_snapshot(source)
            return

        scheduled_at = datetime.now(UTC)
        self._set_restore_status(
            source,
            state="writeback_scheduled",
            first_try_delay_seconds=_RESTORE_FIRST_WRITEBACK_DELAY_SECONDS,
            recheck_delay_seconds=_RESTORE_RECHECK_DELAY_SECONDS,
        )
        self._schedule_restore_validation(source, snapshot, scheduled_at)

    def async_mark_user_interaction(self, action: str, *, emit_status: bool = True) -> None:
        """Record the timestamp of a user-triggered write command."""
        self._last_user_interaction_at = datetime.now(UTC)
        if not emit_status:
            return
        self._restore_last_event = {
            "source": self._restore_last_event.get("source"),
            "state": "user_interaction",
            "action": action,
            "updated_at": self._last_user_interaction_at.isoformat(),
        }
        self.async_update_listeners()

    @property
    def restore_diagnostics(self) -> dict[str, Any]:
        """Expose restore diagnostics for sensor/diagnostics consumers."""
        return {
            "last_event": self._restore_last_event,
            "last_user_interaction_at": (
                self._last_user_interaction_at.isoformat()
                if self._last_user_interaction_at is not None
                else None
            ),
            "timings": {
                "first_writeback_delay_seconds": _RESTORE_FIRST_WRITEBACK_DELAY_SECONDS,
                "recheck_delay_seconds": _RESTORE_RECHECK_DELAY_SECONDS,
                "post_retry_verify_delay_seconds": _RESTORE_POST_RETRY_VERIFY_DELAY_SECONDS,
            },
            "effective_restore_config": {
                "enabled": self._restore_is_enabled(),
                "system_stop_enabled": self._restore_system_stop_enabled(),
                "free_cooling_enabled": self._restore_free_cooling_enabled(),
                "validity_minutes": self._get_option(
                    CONF_GPIO_RESTORE_VALIDITY_MINUTES,
                    DEFAULT_GPIO_RESTORE_VALIDITY_MINUTES,
                ),
            },
            "sources": self._restore_status_by_source,
        }

    async def _async_ensure_restore_state_loaded(self) -> None:
        """Load restore state from persistent storage once."""
        if self._restore_state_loaded:
            return

        async with self._restore_lock:
            if self._restore_state_loaded:
                return

            if self._restore_store is None:
                self._restore_state_loaded = True
                return

            loaded = await self._restore_store.async_load()
            if isinstance(loaded, dict):
                snapshots = loaded.get("snapshots")
                if isinstance(snapshots, dict):
                    loaded.setdefault("snapshots", {})
                    loaded["snapshots"].setdefault(GPIO_SOURCE_SYSTEM_STOP, None)
                    loaded["snapshots"].setdefault(GPIO_SOURCE_FREE_COOLING, None)
                    self._restore_state = loaded

            self._restore_state_loaded = True

    async def _async_clear_snapshot(self, source: str) -> None:
        """Delete persisted snapshot for a source."""
        async with self._restore_lock:
            self._restore_state["snapshots"][source] = None
            if self._restore_store is not None:
                await self._restore_store.async_save(self._restore_state)

    def _snapshot_is_expired(self, snapshot: dict[str, Any]) -> bool:
        """Return whether the snapshot exceeded the configured validity window."""
        created_at = snapshot.get("created_at")
        if not isinstance(created_at, str):
            return True

        try:
            created_time = datetime.fromisoformat(created_at)
        except ValueError:
            return True

        if created_time.tzinfo is None:
            created_time = created_time.replace(tzinfo=UTC)

        validity_minutes = self._get_option(
            CONF_GPIO_RESTORE_VALIDITY_MINUTES,
            DEFAULT_GPIO_RESTORE_VALIDITY_MINUTES,
        )
        max_age = timedelta(minutes=max(int(validity_minutes), 1))
        return datetime.now(UTC) - created_time > max_age

    async def _async_apply_snapshot(self, snapshot: dict[str, Any]) -> bool:
        """Apply a saved snapshot to all zones."""
        zones = snapshot.get("zones")
        if not isinstance(zones, list):
            return False

        all_ok = True
        for zone_snapshot in zones:
            if not isinstance(zone_snapshot, dict):
                continue

            zone_id = zone_snapshot.get("zoneId")
            if not isinstance(zone_id, int):
                continue

            patch_args: dict[str, Any] = {}
            if "running" in zone_snapshot:
                patch_args["running"] = zone_snapshot["running"]
            if "operationMode" in zone_snapshot:
                patch_args["operation_mode"] = zone_snapshot["operationMode"]
            if "setpoint" in zone_snapshot:
                patch_args["setpoint"] = zone_snapshot["setpoint"]
            if "fanSpeed" in zone_snapshot:
                patch_args["fan_speed"] = zone_snapshot["fanSpeed"]
            if "louverPosition" in zone_snapshot:
                patch_args["louver_position"] = zone_snapshot["louverPosition"]
            if "vanePosition" in zone_snapshot:
                patch_args["vane_position"] = zone_snapshot["vanePosition"]
            if "flap3dAuto" in zone_snapshot:
                patch_args["flap3d_auto"] = zone_snapshot["flap3dAuto"]

            if not patch_args:
                continue

            current_zone = next(
                (
                    zone
                    for zone in self.data
                    if isinstance(zone, dict) and zone.get("zoneId") == zone_id
                ),
                None,
            )
            patch_args["wait_for_airflow_after_start"] = bool(
                patch_args.get("running") is True
                and isinstance(current_zone, dict)
                and not current_zone.get("running", False)
            )

            result = await self.api.async_set_zone_state(zone_id, **patch_args)
            all_ok = all_ok and result

        await self.async_request_refresh()
        return all_ok

    def _schedule_restore_validation(
        self,
        source: str,
        snapshot: dict[str, Any],
        scheduled_at: datetime,
    ) -> None:
        """Schedule delayed restore validation and one retry if needed."""
        task = self._restore_validation_tasks.get(source)
        if task is not None and not task.done():
            task.cancel()

        self._restore_validation_tasks[source] = self.hass.async_create_task(
            self._async_validate_restore(source, snapshot, scheduled_at)
        )

    async def _async_validate_restore(
        self,
        source: str,
        snapshot: dict[str, Any],
        scheduled_at: datetime,
    ) -> None:
        """Apply delayed restore, then validate and retry once when values drift."""
        try:
            await asyncio.sleep(_RESTORE_FIRST_WRITEBACK_DELAY_SECONDS)
            if self._has_user_interaction_since(scheduled_at):
                _LOGGER.debug(
                    "Skipping restore writeback for %s because of user interaction",
                    source,
                )
                self._set_restore_status(source, state="skipped_user_interaction_before_first_try")
                return

            self._set_restore_status(source, state="writeback_first_try")
            await self._async_apply_snapshot(snapshot)

            await asyncio.sleep(_RESTORE_RECHECK_DELAY_SECONDS)
            if self._has_user_interaction_since(scheduled_at):
                _LOGGER.debug(
                    "Skipping restore retry for %s because of user interaction",
                    source,
                )
                self._set_restore_status(source, state="skipped_user_interaction_before_recheck")
                return

            await self.async_request_refresh()

            if self._snapshot_matches_current_state(snapshot):
                _LOGGER.debug(
                    "Restore validation successful for %s after first writeback",
                    source,
                )
                self._set_restore_status(
                    source, state="validated_after_first_try", matched_via="coordinator"
                )
                return

            if await self._async_snapshot_matches_gateway_state(snapshot):
                _LOGGER.debug(
                    "Restore validation for %s confirmed by zone queries after first writeback",
                    source,
                )
                self._set_restore_status(
                    source, state="validated_after_first_try", matched_via="zone_query"
                )
                await self.async_request_refresh()
                return

            _LOGGER.warning(
                "Restore validation failed for %s, retrying snapshot apply once",
                source,
            )
            self._set_restore_status(source, state="writeback_retry")
            await self._async_apply_snapshot(snapshot)
            await asyncio.sleep(_RESTORE_POST_RETRY_VERIFY_DELAY_SECONDS)
            await self.async_request_refresh()

            if self._snapshot_matches_current_state(snapshot):
                _LOGGER.debug(
                    "Restore validation successful for %s after retry",
                    source,
                )
                self._set_restore_status(
                    source, state="validated_after_retry", matched_via="coordinator"
                )
                return

            if await self._async_snapshot_matches_gateway_state(snapshot):
                _LOGGER.debug(
                    "Restore validation for %s confirmed by zone queries after retry",
                    source,
                )
                self._set_restore_status(
                    source, state="validated_after_retry", matched_via="zone_query"
                )
                await self.async_request_refresh()
                return

            _LOGGER.warning(
                "Restore validation still failing for %s after retry",
                source,
            )
            self._set_restore_status(source, state="failed_after_retry")
        except asyncio.CancelledError:
            raise
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Restore validation error for %s: %s", source, err)
            self._set_restore_status(source, state="error", error=str(err))
        finally:
            await self._async_clear_snapshot(source)

    def _has_user_interaction_since(self, marker: datetime) -> bool:
        """Return whether a user-triggered write happened after the marker."""
        return (
            self._last_user_interaction_at is not None and self._last_user_interaction_at > marker
        )

    def _set_restore_status(self, source: str, *, state: str, **extra: Any) -> None:
        """Update restore status diagnostics for one source."""
        updated_at = datetime.now(UTC).isoformat()
        status = {
            "state": state,
            "updated_at": updated_at,
            **extra,
        }
        self._restore_status_by_source[source] = status
        self._restore_last_event = {
            "source": source,
            "state": state,
            "updated_at": updated_at,
            **extra,
        }
        self.async_update_listeners()

    async def _async_snapshot_matches_gateway_state(self, snapshot: dict[str, Any]) -> bool:
        """Check snapshot against fresh per-zone GetZone responses."""
        zones = snapshot.get("zones")
        if not isinstance(zones, list):
            return False

        for attempt in range(_RESTORE_GATEWAY_VERIFY_ATTEMPTS):
            all_match = True

            for zone_snapshot in zones:
                if not isinstance(zone_snapshot, dict):
                    continue

                zone_id = zone_snapshot.get("zoneId")
                if not isinstance(zone_id, int):
                    return False

                zone = await self.api.async_get_zone(zone_id)
                if not isinstance(zone, dict) or not self._zone_matches_snapshot(
                    zone, zone_snapshot
                ):
                    all_match = False
                    break

            if all_match:
                return True

            if attempt < _RESTORE_GATEWAY_VERIFY_ATTEMPTS - 1:
                await asyncio.sleep(_RESTORE_GATEWAY_VERIFY_RETRY_DELAY_SECONDS)

        return False

    def _snapshot_matches_current_state(self, snapshot: dict[str, Any]) -> bool:
        """Check whether current coordinator data matches a saved snapshot."""
        zones = snapshot.get("zones")
        if not isinstance(zones, list):
            return False

        by_zone_id = {
            zone.get("zoneId"): zone
            for zone in self.data
            if isinstance(zone, dict) and isinstance(zone.get("zoneId"), int)
        }

        for zone_snapshot in zones:
            if not isinstance(zone_snapshot, dict):
                continue
            zone_id = zone_snapshot.get("zoneId")
            if not isinstance(zone_id, int):
                return False

            current_zone = by_zone_id.get(zone_id)
            if not isinstance(current_zone, dict):
                return False
            if not self._zone_matches_snapshot(current_zone, zone_snapshot):
                return False

        return True

    def _zone_matches_snapshot(self, zone: dict[str, Any], zone_snapshot: dict[str, Any]) -> bool:
        """Return whether one zone payload matches one snapshot payload."""
        for key in (
            "running",
            "operationMode",
            "fanSpeed",
            "louverPosition",
            "vanePosition",
            "flap3dAuto",
        ):
            if key in zone_snapshot and zone.get(key) != zone_snapshot.get(key):
                return False

        if "setpoint" in zone_snapshot:
            current_setpoint = zone.get("setpoint")
            saved_setpoint = zone_snapshot.get("setpoint")
            if (
                not isinstance(current_setpoint, (int, float))
                or not isinstance(saved_setpoint, (int, float))
                or abs(float(current_setpoint) - float(saved_setpoint)) > 0.2
            ):
                return False

        return True

    def _restore_enabled_for_source(self, source: str) -> bool:
        """Return whether restore should run for the given lock source."""
        if source not in (GPIO_SOURCE_SYSTEM_STOP, GPIO_SOURCE_FREE_COOLING):
            return False

        if not self._restore_is_enabled():
            return False

        if source == GPIO_SOURCE_SYSTEM_STOP:
            return self._restore_system_stop_enabled()

        return self._restore_free_cooling_enabled()

    def _restore_is_enabled(self) -> bool:
        """Return whether restore is globally enabled."""
        return self._coerce_bool_option(
            self._get_option(CONF_GPIO_RESTORE_ENABLED, DEFAULT_GPIO_RESTORE_ENABLED),
            DEFAULT_GPIO_RESTORE_ENABLED,
        )

    def _restore_system_stop_enabled(self) -> bool:
        """Return whether restore is enabled for system-stop releases."""
        return self._coerce_bool_option(
            self._get_option(
                CONF_GPIO_RESTORE_SYSTEM_STOP,
                DEFAULT_GPIO_RESTORE_SYSTEM_STOP,
            ),
            DEFAULT_GPIO_RESTORE_SYSTEM_STOP,
        )

    def _restore_free_cooling_enabled(self) -> bool:
        """Return whether restore is enabled for free-cooling releases."""
        return self._coerce_bool_option(
            self._get_option(
                CONF_GPIO_RESTORE_FREE_COOLING,
                DEFAULT_GPIO_RESTORE_FREE_COOLING,
            ),
            DEFAULT_GPIO_RESTORE_FREE_COOLING,
        )

    @staticmethod
    def _coerce_bool_option(value: Any, default: bool) -> bool:
        """Convert persisted option values to booleans safely."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off", ""}:
                return False
            return default
        if isinstance(value, (int, float)):
            return bool(value)
        if value is None:
            return default
        return bool(value)

    def _get_option(self, key: str, default: Any) -> Any:
        """Return a config entry option with a fallback default."""
        options = getattr(self.config_entry, "options", None)
        if isinstance(options, Mapping) and key in options:
            return options[key]

        data = getattr(self.config_entry, "data", None)
        if isinstance(data, Mapping) and key in data:
            return data[key]

        return default


def _get_update_interval(entry: Any | None) -> timedelta:
    """Return the configured coordinator update interval."""
    raw_value: Any = None

    if entry is not None and hasattr(entry, "options"):
        raw_value = entry.options.get(CONF_POLL_INTERVAL)

    if raw_value is None:
        raw_value = os.getenv(UPDATE_INTERVAL_ENV_VAR)

    if raw_value is None:
        return timedelta(seconds=DEFAULT_POLL_INTERVAL)

    try:
        interval = int(raw_value)
    except (TypeError, ValueError):
        _LOGGER.warning(
            "Ignoring invalid %s value %r; using %s seconds",
            CONF_POLL_INTERVAL,
            raw_value,
            DEFAULT_POLL_INTERVAL,
        )
        return timedelta(seconds=DEFAULT_POLL_INTERVAL)

    return timedelta(seconds=max(interval, 1))
