"""Define GraphQL queries and mutations for NOVA_RC."""

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

GET_GPIOS_QUERY = """
query GetGpios {
  gpio {
    gpios {
      ...GpioSimple
      __typename
    }
    __typename
  }
}

fragment GpioSimple on Gpio {
  id
  function
  value
  __typename
}
"""

GET_ZONE_QUERY = """
query GetZone($zoneId: Int!) {
  xybus {
    zone(zoneId: $zoneId) {
      ...ZoneDetail
      __typename
    }
    __typename
  }
}

fragment ZoneDetail on XYBusZone {
  zoneId
  displayName
  indoorUnits {
    ...IndoorUnit
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
  temperatureRangeEnable
  temperatureRangeHeating {
    lower
    upper
    __typename
  }
  temperatureRangeCooling {
    lower
    upper
    __typename
  }
  operationModePermission {
    auto
    cooling
    heating
    dry
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
  patchOptions {
    ...ZonePatchOptions
    __typename
  }
  __typename
}

fragment IndoorUnit on IndoorUnit {
  indoorUnitId
  displayName
  state {
    running
    roomAirTemperature
    __typename
  }
  __typename
}

fragment ZonePatchOptions on ZonePatchOptions {
  operationMode
  temperatureRangeEnable
  operationModePermission
  running
  fanSpeed
  setpoint
  setpointRange {
    lower
    upper
    __typename
  }
  fanSpeedRange
  louverPosition
  vanePosition
  flap3dAuto
  temperatureRangeCooling
  temperatureRangeHeating
  __typename
}
"""

GET_UPDATE_CLOUD_SETTINGS_QUERY = """
query GetUpdateCloudSettings {
  system {
    information {
      installedVersion {
        asString
        __typename
      }
      installedBundleDescription
      installedBundleBuild
      __typename
    }
    __typename
  }
  update {
    cloud {
      availableSoftwareRelease {
        version {
          asString
          __typename
        }
        __typename
      }
      settings {
        automaticCheck
        automaticInstall
        __typename
      }
      __typename
    }
    __typename
  }
}
"""

GET_TIME_SERIES_QUERY = """
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
"""

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
