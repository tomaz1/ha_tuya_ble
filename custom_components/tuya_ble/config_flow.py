"""Configure Tuya BLE through User Code and QR login or manual credentials."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult, section
from homeassistant.helpers import selector

from .const import DOMAIN
from .credentials import (
    DEVICE_FIELDS,
    SERVICE_UUID,
    advertised_uuid,
    credentials_complete,
    local_credentials,
    normalize_address,
    shared_device_credentials,
)
from .sharing import confirm_login, get_account_devices, request_qr_code


def _credential_schema(values: dict[str, Any], *, address: bool = True) -> vol.Schema:
    """Validate manual fields only when the user selects that setup method."""
    fields = {}
    for key in DEVICE_FIELDS:
        if key == "address" and not address:
            continue
        validator = (
            selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            )
            if key == "local_key"
            else str
        )
        fields[vol.Optional(key, default=values.get(key, ""))] = validator
    return vol.Schema(fields)


class _SetupFlow:
    """Share the account and manual steps across setup, recovery and options."""

    _entry: ConfigEntry | None = None
    _discovery_info: BluetoothServiceInfoBleak | None = None
    _is_options = False
    _is_reauth = False

    def _initialize_setup(self) -> None:
        self._user_code = ""
        self._qr_code = ""
        self._session: dict[str, Any] | None = None
        self._account_devices: dict[str, dict[str, Any]] = {}
        self._selected: dict[str, str] = {}
        self._selected_device_id = ""

    def _stored(self) -> dict[str, Any]:
        return {**self._entry.data, **self._entry.options} if self._entry else {}

    async def _async_start(self, step_id: str, user_input=None) -> FlowResult:
        errors = {}
        values = user_input or {}
        if user_input is not None:
            if user_input.get("setup_method", "user_code") == "manual":
                manual = dict(user_input.get("manual", {}))
                if self._entry:
                    manual["address"] = self._entry.data["address"]
                errors = self._validate(manual)
                if not errors:
                    return await self._async_finish(local_credentials(manual), "manual")
            else:
                self._user_code = str(
                    user_input.get("user_code", {}).get("user_code", "")
                ).strip()
                if not self._user_code:
                    errors["base"] = "missing_user_code"
                else:
                    try:
                        self._qr_code = await self.hass.async_add_executor_job(
                            request_qr_code, self._user_code
                        )
                    except Exception:
                        # SDK errors may contain authentication data. Never log them.
                        errors["base"] = "cannot_connect"
                    else:
                        return await self.async_step_scan()
        manual_values = values.get("manual", self._stored())
        if self._discovery_info and not manual_values.get("address"):
            manual_values = {**manual_values, "address": self._discovery_info.address}
        default_method = "user_code"
        if self._is_options and self._stored().get("setup_method") == "manual":
            default_method = "manual"
        method = values.get("setup_method", default_method)
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required("setup_method", default=method): vol.In(
                        {
                            "user_code": "User Code (Smart Life / Tuya Smart)",
                            "manual": "Manual setup",
                        }
                    ),
                    vol.Required("user_code"): section(
                        vol.Schema(
                            {vol.Optional("user_code", default=self._user_code): str}
                        ),
                        {"collapsed": False},
                    ),
                    vol.Required("manual"): section(
                        _credential_schema(manual_values, address=self._entry is None),
                        {"collapsed": method != "manual"},
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_scan(self, user_input=None) -> FlowResult:
        """Render a local QR and check app confirmation after Submit."""
        errors = {}
        if user_input is not None:
            try:
                if user_input.get("new_qr_code", False):
                    self._qr_code = await self.hass.async_add_executor_job(
                        request_qr_code, self._user_code
                    )
                else:
                    self._session = await self.hass.async_add_executor_job(
                        confirm_login, self._qr_code, self._user_code
                    )
                    if self._session:
                        self._qr_code = ""
                        return await self.async_step_account_device()
                    errors["base"] = "qr_not_confirmed"
            except Exception:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="scan",
            data_schema=vol.Schema(
                {
                    vol.Optional("QR"): selector.QrCodeSelector(
                        selector.QrCodeSelectorConfig(
                            data=f"tuyaSmart--qrLogin?token={self._qr_code}",
                            scale=5,
                            error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
                        )
                    ),
                    vol.Optional("new_qr_code", default=False): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_account_device(self, user_input=None) -> FlowResult:
        """Choose a device belonging to the app account after QR login."""
        errors = {}
        if not self._account_devices and self._session:
            try:
                devices = await self.hass.async_add_executor_job(
                    get_account_devices, self._session
                )
            except Exception:
                errors["base"] = "device_list_failed"
            else:
                self._account_devices = {
                    device_id: shared_device_credentials(device)
                    for device_id, device in devices.items()
                }
                if self._account_devices:
                    self._session = None
                    self._user_code = ""
        choices = self._account_devices
        stored_id = self._stored().get("device_id")
        if self._entry and stored_id:
            choices = {key: value for key, value in choices.items() if key == stored_id}
        if user_input and user_input.get("device_id") in choices:
            self._selected_device_id = user_input["device_id"]
            self._selected = dict(choices[self._selected_device_id])
            if self._entry:
                self._selected["address"] = self._entry.data["address"]
            else:
                matches = self._matching_addresses(self._selected["uuid"])
                if len(matches) == 1:
                    self._selected["address"] = matches[0]
                elif not self._selected["address"] and self._discovery_info:
                    # Add on a Bluetooth discovery card already identifies a MAC.
                    # Some advertisement formats cannot expose a UUID, so retain
                    # that address for confirmation unless a decoded UUID disagrees.
                    discovery = self._discovered().get(
                        normalize_address(self._discovery_info.address)
                    )
                    if discovery:
                        uuid = advertised_uuid(
                            discovery.service_data, discovery.manufacturer_data
                        )
                        if uuid is None or uuid == self._selected["uuid"]:
                            self._selected["address"] = normalize_address(
                                discovery.address
                            )
            return await self.async_step_device_credentials()
        if not choices and not errors:
            errors["base"] = (
                "account_device_not_found" if self._entry else "no_account_devices"
            )
        schema = {}
        if choices:
            schema[vol.Required("device_id")] = vol.In(
                {
                    key: f"{value['device_name'] or 'Tuya device'} ({key})"
                    for key, value in choices.items()
                }
            )
        return self.async_show_form(
            step_id="account_device", data_schema=vol.Schema(schema), errors=errors
        )

    def _discovered(self) -> dict[str, BluetoothServiceInfoBleak]:
        devices = {
            normalize_address(info.address): info
            for info in async_discovered_service_info(self.hass, connectable=True)
            if SERVICE_UUID in info.service_data or SERVICE_UUID in info.service_uuids
        }
        if self._discovery_info:
            devices.setdefault(
                normalize_address(self._discovery_info.address), self._discovery_info
            )
        devices.pop("", None)
        return devices

    def _matching_addresses(self, uuid: str) -> list[str]:
        if not uuid:
            return []
        return [
            address
            for address, info in self._discovered().items()
            if advertised_uuid(info.service_data, info.manufacturer_data) == uuid
        ]

    async def async_step_device_credentials(self, user_input=None) -> FlowResult:
        """Confirm retrieved credentials and complete any missing BLE fields."""
        errors = {}
        values = self._selected
        if user_input is not None:
            values = dict(user_input)
            if user_input.get("bluetooth_device"):
                values["address"] = user_input["bluetooth_device"]
            if self._entry:
                values["address"] = self._entry.data["address"]
            errors = self._validate(values)
            if values.get("device_id", "").strip() != self._selected_device_id:
                errors["base"] = "wrong_device"
            if not errors:
                info = self._discovered().get(normalize_address(values["address"]))
                uuid = (
                    advertised_uuid(info.service_data, info.manufacturer_data)
                    if info
                    else None
                )
                if uuid and uuid != values["uuid"].strip():
                    errors["base"] = "bluetooth_device_mismatch"
                else:
                    return await self._async_finish(
                        local_credentials(values), "user_code"
                    )
        schema = dict(_credential_schema(values, address=self._entry is None).schema)
        devices = self._discovered()
        if devices and not self._entry:
            schema[vol.Optional("bluetooth_device", default="")] = vol.In(
                {
                    "": "Use the MAC address above",
                    **{
                        address: f"{info.name or 'Tuya BLE'} ({address})"
                        for address, info in devices.items()
                    },
                }
            )
        return self.async_show_form(
            step_id="device_credentials", data_schema=vol.Schema(schema), errors=errors
        )

    def _validate(self, values: dict[str, Any]) -> dict[str, str]:
        if not credentials_complete(values):
            return {"base": "missing_manual_credentials"}
        if not str(values.get("address") or "").strip():
            return {"base": "missing_address"}
        if not normalize_address(values.get("address")):
            return {"base": "invalid_address"}
        stored_id = self._stored().get("device_id")
        if (
            self._entry
            and stored_id
            and values.get("device_id", "").strip() != stored_id
        ):
            return {"base": "wrong_device"}
        return {}

    async def _async_finish(
        self, credentials: dict[str, str], method: str
    ) -> FlowResult:
        """Store the same local format for both methods, with no account tokens."""
        options = {**credentials, "setup_method": method}
        title = credentials["device_name"] or credentials["address"]
        self._session = None
        self._account_devices = {}
        self._selected = {}
        self._user_code = self._qr_code = ""
        if self._is_options:
            # Update the title and key atomically so a rename cannot reload old keys.
            self.hass.config_entries.async_update_entry(
                self._entry, title=title, options=options
            )
            return self.async_create_entry(title="", data=options)
        if self._is_reauth:
            return self.async_update_reload_and_abort(
                self._entry,
                data={"address": credentials["address"]},
                options=options,
                title=title,
            )
        await self.async_set_unique_id(credentials["address"])
        self._abort_if_unique_id_configured()
        for entry in self._async_current_entries():
            if entry.options.get("device_id") == credentials["device_id"]:
                return self.async_abort(reason="already_configured")
        return self.async_create_entry(
            title=title, data={"address": credentials["address"]}, options=options
        )


class TuyaBLEConfigFlow(_SetupFlow, ConfigFlow, domain=DOMAIN):
    """Handle new devices and recovery of legacy developer-account entries."""

    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        self._initialize_setup()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TuyaBLEOptionsFlow:
        return TuyaBLEOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None) -> FlowResult:
        return await self._async_start("user", user_input)

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Open the same setup form for nearby BLE devices."""
        await self.async_set_unique_id(normalize_address(discovery_info.address))
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or discovery_info.address
        }
        return await self.async_step_user()

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Recover missing local credentials without the retired developer API."""
        self._entry = self._get_reauth_entry()
        self._is_reauth = True
        return await self.async_step_user()


class TuyaBLEOptionsFlow(_SetupFlow, OptionsFlow):
    """Edit manual credentials or fetch fresh keys for the same app device."""

    _is_options = True

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry
        self._initialize_setup()

    async def async_step_init(self, user_input=None) -> FlowResult:
        return await self._async_start("init", user_input)
