"""API client for the MHI NovaLink GraphQL gateway."""

import logging
from typing import Any

import aiohttp

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
    "ou_indication_protection_state_comp",
    "iu_indication_eev1",
    "iu_indication_heat_exch3_temp_low_site",
    "iu_indication_heat_exch2_temp_high_site",
    "iu_indication_heat_exch1_temp_low_site",
    "iu_indication_capacity",
    "iu_indication_fan_speed_rpm",
    "iu_indication_total_running_hours",
}

_LOGGER = logging.getLogger(__name__)

# GraphQL query to read all zones, including the richer gateway detail fields.
GET_ZONES_QUERY = """
query GetZones {
  xybus {
    zones {
      ... on XYBusZone {
        ...Zone
        __typename
      }
      ... on OfflineZone {
        ...ZoneOffline
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment Zone on XYBusZone {
  __typename
  zoneId
  available
  displayName
  name
  indoorUnitCount
  newIndoorUnitCount
  indoorUnits {
    indoorUnitId
    displayName
    name
    isNew
    unitNoMain
    unitNoSub
    state {
      running
      roomAirTemperature
      operationMode
      fanSpeed
      setpoint
      __typename
    }
    __typename
  }
  sequencingState {
    alarm
    __typename
  }
  error {
    maintenanceCount
    criticalCount
    __typename
  }
  controllingMode
  controllingModeChangeProgress
  unitNoMain
  unitNoSub
  setpoint
  roomAirTemperature
  running
  operationMode
  operationModePermission {
    auto
    cooling
    heating
    dry
    __typename
  }
  temperatureRangeEnable
  temperatureRangeCooling {
    lower
    upper
    __typename
  }
  temperatureRangeHeating {
    lower
    upper
    __typename
  }
  fanSpeed
  louverPosition
  vanePosition
  flap3dAuto
  manualOperationTimeout {
    totalSeconds
    __typename
  }
  manualOperationDurationSec
  controlProgram
}

fragment ZoneOffline on OfflineZone {
  __typename
  zoneId
}
"""

GET_INDOOR_UNIT_QUERY = """
query GetIndoorUnit($indoorUnitId: Int!) {
  xybus {
    indoorUnit(indoorUnitId: $indoorUnitId) {
      indoorUnitId
      name
      displayName
      isNew
      unitNoMain
      unitNoSub
      state {
        running
        roomAirTemperature
        operationMode
        fanSpeed
        setpoint
        __typename
      }
      controllingMode
      controlProgram
      manualOperationDurationSec
      __typename
    }
  }
}
"""

GET_NOTIFICATIONS_QUERY = """
query GetNotifications {
  notification {
    notifications(filter: {} orders: [{ by: NOTIFICATION_ID, direction: ASC }] page: { limit: 20, offset: 0 }) {
      notificationId
      confirmedBy
      creationDate
      confirmationDate
      error
      priority
      active
      source
    }
    errors(onlyActive: true) {
      name
      code
      description(language: \"en\")
      priority
    }
    notificationCount(filter: {})
    sources
  }
}
"""

# GraphQL mutation to change zone settings.
SET_ZONE_PATCH_MUTATION = """
mutation PatchZone($zoneId: Int!, $patch: ZonePatch!) {
  xybus {
    zone(zoneId: $zoneId) {
      patch(patch: $patch) {
        ...JobFragment
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment JobFragment on Job {
  id
  done
  cancelled
  exception
  result {
    ... on SmtpServerResponseResult {
      message
      code
      __typename
    }
    ... on SmtpSendTestEmailResult {
      error
      __typename
    }
    ... on Notification {
      confirmedBy {
        username
        userId
        fullName
        __typename
      }
      confirmationDate
      __typename
    }
    __typename
  }
  __typename
}
"""


class CannotConnect(Exception):
    """Raised when the gateway cannot be reached."""


class InvalidAuth(Exception):
    """Raised when authentication fails."""


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


def normalize_indoor_unit_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize the direct indoor-unit payload into a simple dict."""
    xybus = data.get("data", {}).get("xybus", {})
    indoor_unit = xybus.get("indoorUnit")
    if not isinstance(indoor_unit, dict):
        return {}

    state = indoor_unit.get("state") or {}
    if isinstance(state, dict):
        normalized_state = dict(state)
        normalized_state.setdefault(
            "roomAirTemperature", indoor_unit.get("roomAirTemperature")
        )
        normalized_state.setdefault("running", indoor_unit.get("running"))
        normalized_state.setdefault("operationMode", indoor_unit.get("operationMode"))
        normalized_state.setdefault("fanSpeed", indoor_unit.get("fanSpeed"))
        normalized_state.setdefault("setpoint", indoor_unit.get("setpoint"))
        indoor_unit = dict(indoor_unit)
        indoor_unit["state"] = normalized_state

    return indoor_unit


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


class SKlimaApiClient:
    """GraphQL client for MHI NovaLink."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self.host = host
        self.session = session

        clean_host = host.replace("https://", "").replace("http://", "").strip("/")
        self.endpoint = f"https://{clean_host}/graphql/"
        self.username: str | None = None
        self.password: str | None = None

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
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        auth = (
            aiohttp.BasicAuth(self.username, self.password)
            if self.username and self.password
            else None
        )

        try:
            async with self.session.post(
                self.endpoint,
                json={
                    "query": GET_ZONES_QUERY,
                    "operationName": "GetZones",
                    "variables": {},
                },
                headers=headers,
                auth=auth,
                timeout=10,
                ssl=False,
            ) as response:
                text = await response.text()

                if response.status in (401, 403):
                    _LOGGER.error("Auth-Fehler (%s): %s", response.status, text)
                    raise InvalidAuth("Authentication rejected.")

                if response.status != 200:
                    _LOGGER.error(
                        "GetZones returned HTTP error (%s): %s", response.status, text
                    )
                    raise CannotConnect(f"HTTP Fehler: {response.status}")

                data = await response.json()

                if "errors" in data:
                    _LOGGER.error("GraphQL-Antwort Fehler: %s", data["errors"])
                    raise CannotConnect("GraphQL query error")

                zones = normalize_zones_payload(data)
                for zone in zones:
                    await self._attach_time_series_data(zone)

                return zones

        except aiohttp.ClientError as err:
            raise CannotConnect(f"Connection error: {err}") from err

    async def async_get_indoor_unit(self, indoor_unit_id: int) -> dict[str, Any]:
        """Fetch a single indoor unit directly using a dedicated GraphQL query."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        auth = (
            aiohttp.BasicAuth(self.username, self.password)
            if self.username and self.password
            else None
        )

        try:
            async with self.session.post(
                self.endpoint,
                json={
                    "query": GET_INDOOR_UNIT_QUERY,
                    "operationName": "GetIndoorUnit",
                    "variables": {"indoorUnitId": indoor_unit_id},
                },
                headers=headers,
                auth=auth,
                timeout=10,
                ssl=False,
            ) as response:
                text = await response.text()

                if response.status in (401, 403):
                    _LOGGER.error("Auth-Fehler (%s): %s", response.status, text)
                    raise InvalidAuth("Authentication rejected.")

                if response.status != 200:
                    _LOGGER.error(
                        "GetIndoorUnit returned HTTP error (%s): %s",
                        response.status,
                        text,
                    )
                    raise CannotConnect(f"HTTP Fehler: {response.status}")

                data = await response.json()

                if "errors" in data:
                    _LOGGER.error("GraphQL-Antwort Fehler: %s", data["errors"])
                    raise CannotConnect("GraphQL query error")

                return normalize_indoor_unit_payload(data)

        except aiohttp.ClientError as err:
            raise CannotConnect(f"Connection error: {err}") from err

    async def async_get_notifications(self) -> dict[str, Any]:
        """Fetch active gateway notifications and errors."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        auth = (
            aiohttp.BasicAuth(self.username, self.password)
            if self.username and self.password
            else None
        )

        try:
            async with self.session.post(
                self.endpoint,
                json={
                    "query": GET_NOTIFICATIONS_QUERY,
                    "operationName": "GetNotifications",
                    "variables": {},
                },
                headers=headers,
                auth=auth,
                timeout=10,
                ssl=False,
            ) as response:
                text = await response.text()
                if response.status != 200:
                    _LOGGER.debug("Notification query failed: %s", text)
                    return {}

                data = await response.json()
                if "errors" in data:
                    _LOGGER.debug("Notification query error: %s", data.get("errors"))
                    return {}

                return normalize_notifications_payload(data)
        except aiohttp.ClientError as err:
            _LOGGER.debug("Notification request failed: %s", err)
            return {}

    async def _attach_time_series_data(self, zone: dict[str, Any]) -> None:
        """Fetch and attach time-series datasets for a zone when supported by the gateway."""
        if not isinstance(zone, dict):
            return

        identifiers = build_time_series_identifiers(zone)
        if not identifiers:
            return

        payload = {
            "query": """
query GetData($count: Int!, $identifiers: [DataSetIdentifier!]!, $period: DateTimeIntervalInput!) {
  timeSeries {
    dataSetsWithData(count: $count, identifiers: $identifiers, period: $period) {
      ...DataSet
      data {
        ... on NumericalTuple {
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment DataSet on DataSet {
  id
  reference
  source
  data {
    timestamp
    value
    __typename
  }
  options {
    ... on NumericalOptions {
      ...NumericalOptions
      __typename
    }
    ... on EnumeratedOptions {
      ...EnumeratedOptions
      __typename
    }
    __typename
  }
  __typename
}

fragment NumericalOptions on NumericalOptions {
  __typename
  suffix
  process
  precision
  curve
  factor
  divisor
}

fragment EnumeratedOptions on EnumeratedOptions {
  __typename
  options {
    label
    color
    value
    __typename
  }
}
""",
            "operationName": "GetData",
            "variables": {
                "count": 100,
                "identifiers": identifiers,
                "period": {
                    "startDate": "2026-06-24T22:00:00.000Z",
                    "endDate": "2026-07-25T22:00:00.000Z",
                },
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        auth = (
            aiohttp.BasicAuth(self.username, self.password)
            if self.username and self.password
            else None
        )

        try:
            async with self.session.post(
                self.endpoint,
                json=payload,
                headers=headers,
                auth=auth,
                timeout=10,
                ssl=False,
            ) as response:
                text = await response.text()
                if response.status != 200:
                    _LOGGER.debug(
                        "Time-series query failed for zone %s: %s",
                        zone.get("zoneId"),
                        text,
                    )
                    return

                data = await response.json()
                if "errors" in data:
                    _LOGGER.debug(
                        "Time-series query error for zone %s: %s",
                        zone.get("zoneId"),
                        data.get("errors"),
                    )
                    return

                datasets = normalize_time_series_payload(data)
                if datasets:
                    zone["timeSeries"] = {"dataSets": list(datasets.values())}
        except aiohttp.ClientError as err:
            _LOGGER.debug(
                "Time-series request failed for zone %s: %s", zone.get("zoneId"), err
            )

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
    ) -> bool:
        """Change settings for a specific zone via a patch mutation."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        auth = (
            aiohttp.BasicAuth(self.username, self.password)
            if self.username and self.password
            else None
        )

        # Build the patch payload.
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
                headers=headers,
                auth=auth,
                timeout=10,
                ssl=False,
            ) as response:
                text = await response.text()

                if response.status != 200:
                    _LOGGER.error(
                        "Mutation returned HTTP error (%s): %s", response.status, text
                    )
                    return False

                res_json = await response.json()

                if "errors" in res_json:
                    _LOGGER.error("Mutation GraphQL error: %s", res_json["errors"])
                    return False

                job = (
                    res_json.get("data", {})
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
                return True

        except (aiohttp.ClientError, ValueError) as err:
            _LOGGER.error("Failed to send mutation for zone %s: %s", zone_id, err)
            return False
