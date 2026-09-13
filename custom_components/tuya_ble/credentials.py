"""Normalize local BLE credentials without retaining account login secrets."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from Crypto.Cipher import AES

REQUIRED_FIELDS = ("uuid", "local_key", "device_id", "category", "product_id")
OPTIONAL_FIELDS = ("device_name", "product_name", "product_model")
DEVICE_FIELDS = ("address", *REQUIRED_FIELDS, *OPTIONAL_FIELDS)
SERVICE_UUID = "0000a201-0000-1000-8000-00805f9b34fb"


def normalize_address(value: Any) -> str:
    """Accept common MAC formats and return the canonical Bluetooth address."""
    if not isinstance(value, str):
        return ""
    value = re.sub(r"[:.\-]", "", value.strip()).upper()
    if not re.fullmatch(r"[0-9A-F]{12}", value):
        return ""
    return ":".join(value[index : index + 2] for index in range(0, 12, 2))


def local_credentials(values: dict[str, Any]) -> dict[str, str]:
    """Copy only device credentials; never persist QR tokens or account secrets."""
    result = {
        key: value.strip() if isinstance(value := values.get(key), str) else ""
        for key in DEVICE_FIELDS
    }
    result["address"] = normalize_address(result["address"])
    return result


def credentials_complete(values: dict[str, Any]) -> bool:
    """Check the fields required by the existing BLE pairing protocol."""
    normalized = local_credentials(values)
    return all(normalized[key] for key in REQUIRED_FIELDS)


def shared_device_credentials(device: dict[str, Any]) -> dict[str, str]:
    """Translate a device-sharing response into the existing manual format."""
    values = dict(device)
    values["device_id"] = device.get("id") or device.get("device_id")
    values["device_name"] = device.get("name") or device.get("device_name")
    values["product_model"] = device.get("model") or device.get("product_model")
    # A generic MAC may belong to Wi-Fi or a gateway. Match BLE UUIDs instead.
    values["address"] = device.get("ble_mac") or device.get("bluetooth_mac")
    return local_credentials(values)


def advertised_uuid(service_data: dict, manufacturer_data: dict) -> str | None:
    """Decode the UUID using the same advertisement format as our BLE library."""
    service = service_data.get(SERVICE_UUID, b"")
    manufacturer = manufacturer_data.get(0x07D0, b"")
    if len(service) < 2 or service[0] != 0 or len(manufacturer) <= 6:
        return None
    encrypted = manufacturer[6:]
    if len(encrypted) % AES.block_size:
        return None
    key = hashlib.md5(service[1:]).digest()
    try:
        return (
            AES.new(key, AES.MODE_CBC, key).decrypt(encrypted).decode().rstrip("\x00")
        )
    except (ValueError, UnicodeDecodeError):
        return None
