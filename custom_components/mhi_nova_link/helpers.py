"""Provide helpers for parsing NOVA_RC time-series payloads."""

from collections.abc import Mapping
from typing import Any


def get_zone_time_series_datasets(zone: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return all time series datasets attached to a zone."""
    datasets: dict[str, dict[str, Any]] = {}

    for payload in _iter_time_series_payloads(zone):
        items = payload.get("dataSets") or payload.get("datasets") or []
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            dataset_id = item.get("id")
            if isinstance(dataset_id, str) and dataset_id:
                datasets[dataset_id] = item

            nested_items = item.get("dataSets") or item.get("datasets") or []
            if isinstance(nested_items, list):
                for nested_item in nested_items:
                    if isinstance(nested_item, dict):
                        nested_id = nested_item.get("id")
                        if isinstance(nested_id, str) and nested_id:
                            datasets[nested_id] = nested_item

    return datasets


def get_dataset_value(dataset: Mapping[str, Any]) -> Any:
    """Extract the latest known value from a dataset payload."""
    data = dataset.get("data")
    if data is None:
        return None

    if isinstance(data, (int, float, bool, str)):
        return data

    if isinstance(data, list):
        if not data:
            return None

        if len(data) == 1:
            return get_dataset_value({"data": data[0]})

        latest_item = None
        latest_timestamp = None
        for item in data:
            if not isinstance(item, dict):
                continue
            timestamp = item.get("timestamp")
            if timestamp is None:
                continue
            if latest_timestamp is None or timestamp >= latest_timestamp:
                latest_timestamp = timestamp
                latest_item = item

        if latest_item is not None:
            return get_dataset_value({"data": latest_item})

        values = [get_dataset_value({"data": item}) for item in data]
        return values[-1] if values else None

    if isinstance(data, dict):
        for key in ("value", "currentValue", "latestValue", "current", "state"):
            if key in data and data[key] is not None:
                return get_dataset_value({"data": data[key]})

        for key in ("values", "points"):
            if key in data and isinstance(data[key], list):
                values = [get_dataset_value({"data": item}) for item in data[key]]
                return values[-1] if values else None

        if "rawValue" in data and data["rawValue"] is not None:
            return data["rawValue"]

        if "data" in data and data["data"] is not None:
            return get_dataset_value({"data": data["data"]})

        if "normal" in data:
            return data["normal"]

    return data


def get_dataset_option_label(dataset: Mapping[str, Any], value: Any) -> str | None:
    """Return the label for an enumerated dataset value when available."""
    options = dataset.get("options", {}).get("options", [])
    if not isinstance(options, list):
        return None

    for option in options:
        if isinstance(option, dict) and option.get("value") == value:
            label = option.get("label")
            if isinstance(label, str) and label:
                return label

    return None


def dataset_is_on(dataset_id: str, dataset: Mapping[str, Any]) -> bool:
    """Convert a dataset to a boolean suitable for binary sensors."""
    value = get_dataset_value(dataset)
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        options = dataset.get("options", {}).get("options", [])
        if isinstance(options, list):
            for option in options:
                if not isinstance(option, dict):
                    continue
                label = _normalize_enum_token(str(option.get("label", "")))
                if label in {
                    "active",
                    "enabled",
                    "on",
                    "open",
                    "true",
                    "yes",
                    "ja",
                    "aktiv",
                    "ein",
                }:
                    return value == option.get("value")
                if label in {
                    "inactive",
                    "disabled",
                    "off",
                    "closed",
                    "false",
                    "no",
                    "nein",
                    "inaktiv",
                    "aus",
                }:
                    return value == option.get("value")
        return bool(value)

    if isinstance(value, str):
        normalized = _normalize_enum_token(value)
        if normalized in {
            "active",
            "enabled",
            "on",
            "open",
            "true",
            "1",
            "ja",
            "yes",
            "y",
            "aktiv",
            "ein",
        }:
            return True
        if normalized in {
            "inactive",
            "disabled",
            "off",
            "closed",
            "false",
            "0",
            "nein",
            "no",
            "n",
            "inaktiv",
            "aus",
        }:
            return False

    if dataset_id in {"compressor_active", "defrosting_active", "filter_sign"}:
        return False

    return bool(value)


def _iter_time_series_payloads(zone: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Collect potential time series payload containers from the zone."""
    payloads: list[dict[str, Any]] = []

    if isinstance(zone.get("timeSeries"), dict):
        payloads.append(zone["timeSeries"])

    if isinstance(zone.get("data"), dict):
        nested = zone["data"].get("timeSeries")
        if isinstance(nested, dict):
            payloads.append(nested)

    return payloads


def _normalize_enum_token(value: str) -> str:
    """Normalize enum-like strings from gateways/options to a comparable token."""
    normalized = value.strip().lower()
    if normalized.startswith("${") and normalized.endswith("}"):
        normalized = normalized[2:-1].strip().lower()
    if "." in normalized:
        normalized = normalized.rsplit(".", 1)[-1]
    return normalized
