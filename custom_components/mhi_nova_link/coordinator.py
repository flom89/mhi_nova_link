"""Coordinate periodic data updates for NOVA_RC."""

import asyncio
import logging
import os
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
)

_LOGGER = logging.getLogger(__name__)

GPIO_SOURCE_SYSTEM_STOP = "SYSTEM_STOP"
GPIO_SOURCE_FREE_COOLING = "FREE_COOLING"
_RESTORE_STORE_VERSION = 1
_RESTORE_VALIDATION_DELAY_SECONDS = 6


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

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch the latest zone data from the GraphQL gateway."""
        await self._async_ensure_restore_state_loaded()
        try:
            data, notifications, gpios_payload, gateway_update = await asyncio.gather(
                self.api.async_get_zones(),
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
        return data

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

    async def async_restore_after_release(self, source: str) -> None:
        """Restore previously saved zone state after a lock source is released."""
        if not self._restore_enabled_for_source(source):
            return

        await self._async_ensure_restore_state_loaded()
        snapshot = self._restore_state.get("snapshots", {}).get(source)
        if not isinstance(snapshot, dict):
            return

        if self._snapshot_is_expired(snapshot):
            _LOGGER.debug("Skipping restore for %s because snapshot is expired", source)
            await self._async_clear_snapshot(source)
            return

        await self._async_apply_snapshot(snapshot)
        self._schedule_restore_validation(source, snapshot)

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

    def _schedule_restore_validation(self, source: str, snapshot: dict[str, Any]) -> None:
        """Schedule delayed restore validation and one retry if needed."""
        task = self._restore_validation_tasks.get(source)
        if task is not None and not task.done():
            task.cancel()

        self._restore_validation_tasks[source] = self.hass.async_create_task(
            self._async_validate_restore(source, snapshot)
        )

    async def _async_validate_restore(self, source: str, snapshot: dict[str, Any]) -> None:
        """Validate restored values and retry once when values drift."""
        try:
            await asyncio.sleep(_RESTORE_VALIDATION_DELAY_SECONDS)
            await self.async_request_refresh()

            if self._snapshot_matches_current_state(snapshot):
                return

            _LOGGER.warning(
                "Restore validation failed for %s, retrying snapshot apply once",
                source,
            )
            await self._async_apply_snapshot(snapshot)
            await asyncio.sleep(2)
            await self.async_request_refresh()
        except asyncio.CancelledError:
            raise
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("Restore validation error for %s: %s", source, err)
        finally:
            await self._async_clear_snapshot(source)

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

            for key in (
                "running",
                "operationMode",
                "fanSpeed",
                "louverPosition",
                "vanePosition",
                "flap3dAuto",
            ):
                if key in zone_snapshot and current_zone.get(key) != zone_snapshot.get(key):
                    return False

            if "setpoint" in zone_snapshot:
                current_setpoint = current_zone.get("setpoint")
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

        if not self._get_option(CONF_GPIO_RESTORE_ENABLED, DEFAULT_GPIO_RESTORE_ENABLED):
            return False

        if source == GPIO_SOURCE_SYSTEM_STOP:
            return bool(
                self._get_option(
                    CONF_GPIO_RESTORE_SYSTEM_STOP,
                    DEFAULT_GPIO_RESTORE_SYSTEM_STOP,
                )
            )

        return bool(
            self._get_option(
                CONF_GPIO_RESTORE_FREE_COOLING,
                DEFAULT_GPIO_RESTORE_FREE_COOLING,
            )
        )

    def _get_option(self, key: str, default: Any) -> Any:
        """Return a config entry option with a fallback default."""
        options = getattr(self.config_entry, "options", None)
        if not isinstance(options, dict):
            return default
        return options.get(key, default)


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
