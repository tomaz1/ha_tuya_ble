"""Serve stored local BLE credentials without a Tuya developer account.

The module and manager names remain stable for the existing entity modules.
"""

from __future__ import annotations

from typing import Any

from .credentials import credentials_complete, local_credentials, normalize_address
from .tuya_ble import AbstaractTuyaBLEDeviceManager, TuyaBLEDeviceCredentials


class HASSTuyaBLEDeviceManager(AbstaractTuyaBLEDeviceManager):
    """Supply saved credentials for local BLE communication."""

    def __init__(self, hass, data: dict[str, Any]) -> None:
        self._data = local_credentials(data)

    async def get_device_credentials(
        self, address: str, force_update: bool = False, save_data: bool = False
    ) -> TuyaBLEDeviceCredentials | None:
        """Return local keys; explicit refreshes belong to the options flow."""
        if not credentials_complete(self._data):
            return None
        if normalize_address(address) != self._data["address"]:
            return None
        return TuyaBLEDeviceCredentials(
            **{key: value for key, value in self._data.items() if key != "address"}
        )

    @property
    def data(self) -> dict[str, Any]:
        return self._data
