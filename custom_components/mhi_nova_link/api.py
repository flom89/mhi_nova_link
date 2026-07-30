"""Provide the NOVA_RC GraphQL API client."""

import asyncio
import binascii
from datetime import UTC, datetime, timedelta
import hashlib
import logging
import os
import ssl
from typing import Any
from urllib.parse import urlsplit

import aiohttp
from aiohttp import client_exceptions as aiohttp_exceptions

from .const import (
    DEFAULT_TIME_SERIES_POLL_INTERVAL,
    LEGACY_TIME_SERIES_UPDATE_INTERVAL_ENV_VAR,
    TIME_SERIES_UPDATE_INTERVAL_ENV_VAR,
)
from .graphql import (
    GET_GPIOS_QUERY,
    GET_NOTIFICATIONS_QUERY,
    GET_TIME_SERIES_QUERY,
    GET_UPDATE_CLOUD_SETTINGS_QUERY,
    GET_ZONE_QUERY,
    GET_ZONES_QUERY,
    SET_ZONE_PATCH_MUTATION,
)

DEFAULT_TIME_SERIES_DATASET_IDS = {
    "iu_room_air_temperature",
    "louver_position",
    "operation_mode",
    "operation_stop",
    "fan_speed",
    "setpoint",
    "flap_3d_auto",
    "filter_sign",
    "compressor_active",
    "defrosting_active",
    "iu_indication_required_frequency",
    "vane_position",
    "ou_indication_super_heat",
    "ou_indication_low_pressure",
    "ou_indication_high_pressure",
    "ou_indication_comp_bottom_temp",
    "ou_indication_discharge_temp",
    "ou_indication_heat_exch2_temp_high_site",
    "ou_indication_heat_exch2_temp_low_site",
    "ou_indication_heat_exch1_temp_high_site",
    "ou_indication_heat_exch1_temp_low_site",
    "ou_indication_air_temp",
    "ou_indication_sensor_sw",
    "ou_indication_fan_speed_level",
    "ou_indication_total_running_hours",
    "ou_indication_eev1",
    "ou_indication_eev2",
    "ou_indication_compressor_frequency",
    "ou_indication_comp_current",
    "ou_indication_protection_state_comp",
    "iu_indication_eev1",
    "iu_indication_heat_exch3_temp_low_site",
    "iu_indication_heat_exch2_temp_high_site",
    "iu_indication_heat_exch1_temp_low_site",
    "iu_indication_capacity",
    "iu_indication_fan_speed_rpm",
    "iu_indication_total_running_hours",
}

TIME_SERIES_LOOKBACK = timedelta(days=30)
TIME_SERIES_POINT_COUNT = 100

_LOGGER = logging.getLogger(__name__)


class CannotConnect(Exception):
    """Raised when the gateway cannot be reached."""


class InvalidAuth(Exception):
    """Raised when authentication fails."""


class InvalidCertificate(Exception):
    """Raised when TLS certificate validation fails."""


def normalize_ssl_fingerprint(value: str | None) -> str | None:
    """Normalize a SHA256 fingerprint to lowercase hex without separators."""
    if value is None:
        return None

    compact = value.replace(":", "").replace(" ", "").lower()
    if not compact:
        return None
    if len(compact) != 64:
        raise ValueError("Fingerprint must contain exactly 64 hex characters")

    try:
        int(compact, 16)
    except ValueError as err:
        raise ValueError(
            "Fingerprint must be a valid hexadecimal SHA256 value"
        ) from err

    return compact


def _raise_if_auth_rejected(status: int, response_text: str, operation: str) -> None:
    """Raise InvalidAuth for HTTP auth failures."""
    if status in (401, 403):
        _LOGGER.error(
            "Authentication error in %s (%s): %s", operation, status, response_text
        )
        raise InvalidAuth("Authentication rejected.")


def _get_time_series_update_interval(configured_interval: Any) -> int:
    """Return the configured time-series update interval in seconds."""
    raw_value = configured_interval

    if raw_value is None:
        raw_value = os.getenv(TIME_SERIES_UPDATE_INTERVAL_ENV_VAR)
    if raw_value is None:
        raw_value = os.getenv(LEGACY_TIME_SERIES_UPDATE_INTERVAL_ENV_VAR)

    if raw_value is None:
        return DEFAULT_TIME_SERIES_POLL_INTERVAL

    try:
        interval = int(raw_value)
    except (TypeError, ValueError):
        _LOGGER.warning(
            "Ignoring invalid time-series update interval %r; using %s seconds",
            raw_value,
            DEFAULT_TIME_SERIES_POLL_INTERVAL,
        )
        return DEFAULT_TIME_SERIES_POLL_INTERVAL

    return max(interval, 1)


def _format_utc_timestamp(timestamp: datetime) -> str:
    """Return a GraphQL-friendly UTC timestamp string."""
    return (
        timestamp.astimezone(UTC)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def build_time_series_period(
    lookback: timedelta = TIME_SERIES_LOOKBACK,
) -> dict[str, str]:
    """Build a rolling time-series period ending at the current UTC time."""
    end = datetime.now(UTC)
    start = end - lookback
    return {
        "startDate": _format_utc_timestamp(start),
        "endDate": _format_utc_timestamp(end),
    }


def build_time_series_identifiers(zone: dict[str, Any]) -> list[dict[str, str]]:
    """Build a time-series identifier list for a zone and its indoor units."""
    zone_id = zone.get("zoneId")
    if zone_id is None:
        return []

    indoor_references = [f"/indoor_unit/{zone_id}"]
    for indoor_unit in zone.get("indoorUnits", []) or []:
        indoor_unit_id = indoor_unit.get("indoorUnitId")
        if indoor_unit_id is not None:
            indoor_references.append(f"/indoor_unit/{indoor_unit_id}")

    # Some gateways report the zone indoor unit in both places; deduplicate references.
    indoor_references = list(dict.fromkeys(indoor_references))

    identifiers: list[dict[str, str]] = []
    for dataset_id in sorted(DEFAULT_TIME_SERIES_DATASET_IDS):
        if dataset_id.startswith("ou_"):
            identifiers.append(
                {"reference": f"/outdoor_unit/{zone_id}", "id": dataset_id}
            )
            continue

        identifiers.extend(
            {"reference": reference, "id": dataset_id}
            for reference in indoor_references
        )

    return identifiers


def normalize_time_series_payload(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Normalize the time-series payload into a lookup keyed by dataset id."""
    datasets: dict[str, dict[str, Any]] = {}

    payload = data.get("data", {}).get("timeSeries", {})
    items = payload.get("dataSetsWithData") or payload.get("dataSets") or []
    if not isinstance(items, list):
        return datasets

    for item in items:
        if not isinstance(item, dict):
            continue
        dataset_id = item.get("id")
        if isinstance(dataset_id, str) and dataset_id:
            datasets[dataset_id] = item

    return datasets


def normalize_notifications_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize the notification payload into a simple dict for entity use."""
    notification = data.get("data", {}).get("notification", {})
    if not isinstance(notification, dict):
        return {}

    notifications = notification.get("notifications") or []
    active_notifications = [
        item
        for item in notifications
        if isinstance(item, dict) and item.get("active") is True
    ]

    errors = notification.get("errors") or []
    active_errors = [
        item
        for item in errors
        if isinstance(item, dict) and item.get("priority") is not None
    ]

    return {
        "notifications": active_notifications,
        "errors": active_errors,
        "notification_count": notification.get("notificationCount"),
        "sources": notification.get("sources"),
    }


def normalize_gpios_payload(data: dict[str, Any]) -> dict[str, bool]:
    """Normalize GPIO payload into a function-to-state mapping."""
    gpio = data.get("data", {}).get("gpio", {})
    if not isinstance(gpio, dict):
        return {}

    gpios = gpio.get("gpios") or []
    if not isinstance(gpios, list):
        return {}

    normalized: dict[str, bool] = {}
    for item in gpios:
        if not isinstance(item, dict):
            continue
        function = item.get("function")
        value = item.get("value")
        if isinstance(function, str) and function:
            normalized[function] = bool(value)

    return normalized


def normalize_zones_payload(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the zone payload for both list-style and single-zone responses."""
    xybus = data.get("data", {}).get("xybus", {})

    raw_zones = xybus.get("zones")
    if raw_zones is not None:
        zones = raw_zones
    else:
        zone = xybus.get("zone")
        zones = [zone] if zone else []

    return [
        z for z in zones if isinstance(z, dict) and z.get("__typename") == "XYBusZone"
    ]


def normalize_gateway_update_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize gateway software and update information for entity consumption."""
    payload = data.get("data", {})
    system = payload.get("system", {})
    information = system.get("information", {}) if isinstance(system, dict) else {}
    update = payload.get("update", {})
    cloud = update.get("cloud", {}) if isinstance(update, dict) else {}

    installed_version = (
        information.get("installedVersion", {}).get("asString")
        if isinstance(information, dict)
        else None
    )
    available_release = (
        cloud.get("availableSoftwareRelease", {}) if isinstance(cloud, dict) else {}
    )
    available_version = (
        available_release.get("version", {}).get("asString")
        if isinstance(available_release, dict)
        else None
    )
    settings = cloud.get("settings", {}) if isinstance(cloud, dict) else {}

    return {
        "installed_version": installed_version,
        "installed_bundle_description": information.get("installedBundleDescription")
        if isinstance(information, dict)
        else None,
        "installed_bundle_build": information.get("installedBundleBuild")
        if isinstance(information, dict)
        else None,
        "available_version": available_version,
        "update_available": bool(available_version),
        "automatic_check": settings.get("automaticCheck")
        if isinstance(settings, dict)
        else None,
        "automatic_install": settings.get("automaticInstall")
        if isinstance(settings, dict)
        else None,
    }


class NovaRcApiClient:
    """GraphQL client for NOVA_RC."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        ssl_fingerprint: str | None = None,
        time_series_poll_interval: int | None = DEFAULT_TIME_SERIES_POLL_INTERVAL,
    ) -> None:
        """Initialize the client."""
        self.host = host
        self.session = session

        clean_host = host.replace("https://", "").replace("http://", "").strip("/")
        base_url = f"https://{clean_host}"
        parsed = urlsplit(base_url)
        self._connect_host = parsed.hostname or clean_host
        self._connect_port = parsed.port or 443
        self.endpoint = f"{base_url}/graphql/"
        self.username: str | None = None
        self.password: str | None = None
        normalized_fingerprint = normalize_ssl_fingerprint(ssl_fingerprint)
        self._ssl_context: bool | aiohttp.Fingerprint = True
        if normalized_fingerprint:
            self._ssl_context = aiohttp.Fingerprint(
                binascii.unhexlify(normalized_fingerprint)
            )

        configured_ts_interval = _get_time_series_update_interval(
            time_series_poll_interval
        )
        self._time_series_update_interval = timedelta(seconds=configured_ts_interval)
        self._time_series_last_fetch: dict[int, datetime] = {}
        self._time_series_cache: dict[int, dict[str, Any]] = {}

    def _get_cached_time_series(self, zone_id: int) -> dict[str, Any] | None:
        """Return cached time-series payload for a zone."""
        return self._time_series_cache.get(zone_id)

    def _set_cached_time_series(
        self,
        zone_id: int,
        time_series_payload: dict[str, Any],
    ) -> None:
        """Persist normalized time-series payload for a zone."""
        self._time_series_cache[zone_id] = time_series_payload

    def _should_refresh_time_series(self, zone_id: int) -> bool:
        """Return whether time-series data should be refreshed for a zone."""
        last_fetch = self._time_series_last_fetch.get(zone_id)
        if last_fetch is None:
            return True

        return datetime.now(UTC) - last_fetch >= self._time_series_update_interval

    def _touch_time_series_fetch(self, zone_id: int) -> None:
        """Record the latest successful time-series fetch attempt time."""
        self._time_series_last_fetch[zone_id] = datetime.now(UTC)

    async def async_get_tls_fingerprint(self) -> str:
        """Return the SHA256 fingerprint of the gateway's presented TLS certificate."""
        # Use a minimal TLS context to avoid loading system trust stores in the event loop.
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        writer = None
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host=self._connect_host,
                    port=self._connect_port,
                    ssl=ssl_context,
                    server_hostname=self._connect_host,
                ),
                timeout=10,
            )
        except (OSError, TimeoutError) as err:
            raise CannotConnect(
                f"Unable to retrieve gateway certificate fingerprint: {err}"
            ) from err

        try:
            ssl_object = writer.get_extra_info("ssl_object")
            if ssl_object is None:
                raise CannotConnect(
                    "No TLS session established while reading certificate"
                )

            certificate = ssl_object.getpeercert(binary_form=True)
            if not certificate:
                raise CannotConnect("Gateway did not provide a TLS certificate")

            return hashlib.sha256(certificate).hexdigest()
        finally:
            writer.close()
            await writer.wait_closed()

    def _build_auth(self) -> aiohttp.BasicAuth | None:
        """Build auth credentials if username and password are available."""
        if self.username and self.password:
            return aiohttp.BasicAuth(self.username, self.password)
        return None

    @staticmethod
    def _zone_has_airflow_values(zone: dict[str, Any]) -> bool:
        """Return whether a zone already reports both airflow selector values."""
        return (
            zone.get("louverPosition") is not None
            and zone.get("vanePosition") is not None
        )

    @staticmethod
    def _build_headers() -> dict[str, str]:
        """Build standard GraphQL HTTP headers."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def async_login(self, username: str, password: str) -> bool:
        """Validate connectivity and store authentication credentials."""
        self.username = username
        self.password = password

        try:
            zones = await self.async_get_zones()
        except (CannotConnect, InvalidAuth, aiohttp.ClientError, ValueError) as err:
            _LOGGER.error("Connection setup failed: %s", err)
            raise

        _LOGGER.info(
            "Successfully connected to gateway. %d active zones found.",
            len(zones),
        )
        return True

    async def async_get_zones(self) -> list[dict[str, Any]]:
        """Fetch all active zones and their properties."""
        try:
            async with self.session.post(
                self.endpoint,
                json={
                    "query": GET_ZONES_QUERY,
                    "operationName": "GetZones",
                    "variables": {},
                },
                headers=self._build_headers(),
                auth=self._build_auth(),
                timeout=10,
                ssl=self._ssl_context,
            ) as response:
                text = await response.text()
                _raise_if_auth_rejected(response.status, text, "GetZones")

                if response.status != 200:
                    _LOGGER.error(
                        "GetZones returned HTTP error (%s): %s", response.status, text
                    )
                    raise CannotConnect(f"HTTP error: {response.status}")

                data = await response.json()
                if "errors" in data:
                    _LOGGER.error("GraphQL response error: %s", data["errors"])
                    raise CannotConnect("GraphQL query error")

                zones = normalize_zones_payload(data)
                for zone in zones:
                    await self._attach_time_series_data(zone)

                return zones

        except (
            aiohttp_exceptions.ServerFingerprintMismatch,
            aiohttp_exceptions.ClientConnectorCertificateError,
            aiohttp_exceptions.ClientConnectorSSLError,
        ) as err:
            raise InvalidCertificate("TLS certificate validation failed") from err
        except aiohttp.ClientError as err:
            raise CannotConnect(f"Connection error: {err}") from err
        except TimeoutError as err:
            raise CannotConnect("Timeout while fetching zones") from err

    async def async_get_zone(self, zone_id: int) -> dict[str, Any] | None:
        """Fetch one zone payload with full detail."""
        try:
            async with self.session.post(
                self.endpoint,
                json={
                    "query": GET_ZONE_QUERY,
                    "operationName": "GetZone",
                    "variables": {"zoneId": int(zone_id)},
                },
                headers=self._build_headers(),
                auth=self._build_auth(),
                timeout=10,
                ssl=self._ssl_context,
            ) as response:
                text = await response.text()
                _raise_if_auth_rejected(response.status, text, "GetZone")
                if response.status != 200:
                    _LOGGER.debug("GetZone failed for zone %s: %s", zone_id, text)
                    return None

                data = await response.json()
                if "errors" in data:
                    _LOGGER.debug(
                        "GetZone GraphQL errors for zone %s: %s",
                        zone_id,
                        data.get("errors"),
                    )
                    return None

                zone = data.get("data", {}).get("xybus", {}).get("zone")
                if isinstance(zone, dict) and zone.get("__typename") == "XYBusZone":
                    return zone
                return None

        except (
            aiohttp_exceptions.ServerFingerprintMismatch,
            aiohttp_exceptions.ClientConnectorCertificateError,
            aiohttp_exceptions.ClientConnectorSSLError,
        ) as err:
            raise InvalidCertificate("TLS certificate validation failed") from err
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.debug("GetZone request failed for zone %s: %s", zone_id, err)
            return None

    async def async_wait_for_zone_airflow_values(
        self,
        zone_id: int,
        timeout_seconds: int = 60,
        interval_seconds: int = 2,
    ) -> None:
        """Poll GetZone until airflow values are present or timeout is reached."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds

        while loop.time() < deadline:
            zone = await self.async_get_zone(zone_id)
            if zone and self._zone_has_airflow_values(zone):
                _LOGGER.debug("Airflow values became available for zone %s", zone_id)
                return

            remaining = deadline - loop.time()
            if remaining <= 0:
                break

            await asyncio.sleep(min(interval_seconds, remaining))

        _LOGGER.debug(
            "Airflow values were not available for zone %s after %s seconds",
            zone_id,
            timeout_seconds,
        )

    async def async_get_notifications(self) -> dict[str, Any]:
        """Fetch active gateway notifications and errors."""
        try:
            async with self.session.post(
                self.endpoint,
                json={
                    "query": GET_NOTIFICATIONS_QUERY,
                    "operationName": "GetNotifications",
                    "variables": {},
                },
                headers=self._build_headers(),
                auth=self._build_auth(),
                timeout=10,
                ssl=self._ssl_context,
            ) as response:
                text = await response.text()
                _raise_if_auth_rejected(response.status, text, "GetNotifications")
                if response.status != 200:
                    _LOGGER.debug("Notification query failed: %s", text)
                    return {}

                data = await response.json()
                if "errors" in data:
                    _LOGGER.debug("Notification query error: %s", data.get("errors"))
                    return {}

                return normalize_notifications_payload(data)

        except (
            aiohttp_exceptions.ServerFingerprintMismatch,
            aiohttp_exceptions.ClientConnectorCertificateError,
            aiohttp_exceptions.ClientConnectorSSLError,
        ) as err:
            raise InvalidCertificate("TLS certificate validation failed") from err
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.debug("Notification request failed: %s", err)
            return {}

    async def async_get_gpios(self) -> dict[str, bool]:
        """Fetch GPIO states for gateway-level binary indicators."""
        try:
            async with self.session.post(
                self.endpoint,
                json={
                    "query": GET_GPIOS_QUERY,
                    "operationName": "GetGpios",
                    "variables": {},
                },
                headers=self._build_headers(),
                auth=self._build_auth(),
                timeout=10,
                ssl=self._ssl_context,
            ) as response:
                text = await response.text()
                _raise_if_auth_rejected(response.status, text, "GetGpios")
                if response.status != 200:
                    _LOGGER.debug("GPIO query failed: %s", text)
                    return {}

                data = await response.json()
                if "errors" in data:
                    _LOGGER.debug("GPIO query error: %s", data.get("errors"))
                    return {}

                return normalize_gpios_payload(data)

        except (
            aiohttp_exceptions.ServerFingerprintMismatch,
            aiohttp_exceptions.ClientConnectorCertificateError,
            aiohttp_exceptions.ClientConnectorSSLError,
        ) as err:
            raise InvalidCertificate("TLS certificate validation failed") from err
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.debug("GPIO request failed: %s", err)
            return {}

    async def async_get_gateway_update_information(self) -> dict[str, Any]:
        """Fetch installed software version and cloud update availability."""
        try:
            async with self.session.post(
                self.endpoint,
                json={
                    "query": GET_UPDATE_CLOUD_SETTINGS_QUERY,
                    "operationName": "GetUpdateCloudSettings",
                    "variables": {},
                },
                headers=self._build_headers(),
                auth=self._build_auth(),
                timeout=10,
                ssl=self._ssl_context,
            ) as response:
                text = await response.text()
                _raise_if_auth_rejected(response.status, text, "GetUpdateCloudSettings")
                if response.status != 200:
                    _LOGGER.debug("Gateway update-info query failed: %s", text)
                    return {}

                data = await response.json()
                if "errors" in data:
                    _LOGGER.debug(
                        "Gateway update-info query error: %s", data.get("errors")
                    )
                    return {}

                return normalize_gateway_update_payload(data)

        except (
            aiohttp_exceptions.ServerFingerprintMismatch,
            aiohttp_exceptions.ClientConnectorCertificateError,
            aiohttp_exceptions.ClientConnectorSSLError,
        ) as err:
            raise InvalidCertificate("TLS certificate validation failed") from err
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.debug("Gateway update-info request failed: %s", err)
            return {}

    async def _attach_time_series_data(self, zone: dict[str, Any]) -> None:
        """Fetch and attach time-series datasets for a zone when supported by the gateway."""
        if not isinstance(zone, dict):
            return

        zone_id = zone.get("zoneId")
        if not isinstance(zone_id, int):
            return

        cached_payload = self._get_cached_time_series(zone_id)
        if not self._should_refresh_time_series(zone_id):
            if cached_payload is not None:
                zone["timeSeries"] = cached_payload
            return

        identifiers = build_time_series_identifiers(zone)
        if not identifiers:
            return

        requested_outdoor_ids = sorted(
            {
                identifier["id"]
                for identifier in identifiers
                if identifier.get("reference") == f"/outdoor_unit/{zone_id}"
                and isinstance(identifier.get("id"), str)
            }
        )

        payload = {
            "query": GET_TIME_SERIES_QUERY,
            "operationName": "GetData",
            "variables": {
                "count": TIME_SERIES_POINT_COUNT,
                "identifiers": identifiers,
                "period": build_time_series_period(),
            },
        }

        try:
            async with self.session.post(
                self.endpoint,
                json=payload,
                headers=self._build_headers(),
                auth=self._build_auth(),
                timeout=10,
                ssl=self._ssl_context,
            ) as response:
                text = await response.text()
                _raise_if_auth_rejected(response.status, text, "GetData")
                if response.status != 200:
                    _LOGGER.debug(
                        "Time-series query failed for zone %s: %s",
                        zone.get("zoneId"),
                        text,
                    )
                    if cached_payload is not None:
                        zone["timeSeries"] = cached_payload
                    return

                data = await response.json()
                if "errors" in data:
                    _LOGGER.debug(
                        "Time-series query error for zone %s: %s",
                        zone.get("zoneId"),
                        data.get("errors"),
                    )
                    if cached_payload is not None:
                        zone["timeSeries"] = cached_payload
                    return

                datasets = normalize_time_series_payload(data)
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    returned_outdoor_datasets = sorted(
                        f"{dataset.get('reference')}::{dataset_id}"
                        for dataset_id, dataset in datasets.items()
                        if isinstance(dataset, dict)
                        and isinstance(dataset.get("reference"), str)
                        and dataset["reference"].startswith("/outdoor_unit/")
                    )
                    outdoor_samples: list[dict[str, Any]] = []
                    identifiers_with_data: list[str] = []
                    for dataset_id, dataset in datasets.items():
                        if not isinstance(dataset, dict):
                            continue
                        if dataset.get("reference") != f"/outdoor_unit/{zone_id}":
                            continue
                        points = dataset.get("data")
                        if not isinstance(points, list) or not points:
                            continue

                        last_point = next(
                            (
                                point
                                for point in reversed(points)
                                if isinstance(point, dict)
                            ),
                            None,
                        )
                        if last_point is None:
                            continue

                        identifiers_with_data.append(dataset_id)
                        outdoor_samples.append(
                            {
                                "id": dataset_id,
                                "points": len(points),
                                "lastTimestamp": last_point.get("timestamp"),
                                "lastValue": last_point.get("value"),
                            }
                        )

                    identifiers_without_data = sorted(
                        set(requested_outdoor_ids) - set(identifiers_with_data)
                    )
                    _LOGGER.debug(
                        "Time-series outdoor datasets for zone %s requested=%s returned=%s",
                        zone_id,
                        requested_outdoor_ids,
                        returned_outdoor_datasets,
                    )
                    _LOGGER.debug(
                        "Time-series outdoor datasets with data for zone %s identifiers=%s samples=%s missing_data=%s",
                        zone_id,
                        sorted(identifiers_with_data),
                        outdoor_samples,
                        identifiers_without_data,
                    )

                if datasets:
                    payload = {"dataSets": list(datasets.values())}
                    zone["timeSeries"] = payload
                    self._set_cached_time_series(zone_id, payload)

                self._touch_time_series_fetch(zone_id)

        except (
            aiohttp_exceptions.ServerFingerprintMismatch,
            aiohttp_exceptions.ClientConnectorCertificateError,
            aiohttp_exceptions.ClientConnectorSSLError,
        ) as err:
            raise InvalidCertificate("TLS certificate validation failed") from err
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.debug(
                "Time-series request failed for zone %s: %s", zone.get("zoneId"), err
            )
            if cached_payload is not None:
                zone["timeSeries"] = cached_payload

    async def async_set_zone_state(
        self,
        zone_id: int,
        running: bool | None = None,
        setpoint: float | None = None,
        operation_mode: str | None = None,
        fan_speed: str | None = None,
        louver_position: str | None = None,
        vane_position: str | None = None,
        flap3d_auto: bool | None = None,
        wait_for_airflow_after_start: bool = False,
    ) -> bool:
        """Change settings for a specific zone via a patch mutation."""
        patch_data: dict[str, Any] = {}
        if running is not None:
            patch_data["running"] = running
        if setpoint is not None:
            patch_data["setpoint"] = float(setpoint)
        if operation_mode is not None:
            patch_data["operationMode"] = operation_mode
        if fan_speed is not None:
            patch_data["fanSpeed"] = fan_speed
        if louver_position is not None:
            patch_data["louverPosition"] = louver_position
        if vane_position is not None:
            patch_data["vanePosition"] = vane_position
        if flap3d_auto is not None:
            patch_data["flap3dAuto"] = flap3d_auto

        if not patch_data:
            return True

        payload = {
            "query": SET_ZONE_PATCH_MUTATION,
            "operationName": "PatchZone",
            "variables": {
                "zoneId": int(zone_id),
                "patch": patch_data,
            },
        }

        try:
            async with self.session.post(
                self.endpoint,
                json=payload,
                headers=self._build_headers(),
                auth=self._build_auth(),
                timeout=10,
                ssl=self._ssl_context,
            ) as response:
                text = await response.text()
                _raise_if_auth_rejected(response.status, text, "PatchZone")

                if response.status != 200:
                    _LOGGER.error(
                        "Mutation returned HTTP error (%s): %s", response.status, text
                    )
                    return False

                response_json = await response.json()
                if "errors" in response_json:
                    _LOGGER.error("Mutation GraphQL error: %s", response_json["errors"])
                    return False

                job = (
                    response_json.get("data", {})
                    .get("xybus", {})
                    .get("zone", {})
                    .get("patch", {})
                )
                _LOGGER.debug(
                    "Patch job started for zone %s (data: %s): %s",
                    zone_id,
                    patch_data,
                    job,
                )

                if running is True and wait_for_airflow_after_start:
                    await self.async_wait_for_zone_airflow_values(zone_id)

                return True

        except (
            aiohttp_exceptions.ServerFingerprintMismatch,
            aiohttp_exceptions.ClientConnectorCertificateError,
            aiohttp_exceptions.ClientConnectorSSLError,
        ) as err:
            raise InvalidCertificate("TLS certificate validation failed") from err
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            _LOGGER.error("Failed to send mutation for zone %s: %s", zone_id, err)
            return False
