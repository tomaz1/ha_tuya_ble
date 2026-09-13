"""Home Assistant boundary doubles for portable integration unit tests.

The actual Tuya SDK and BLE library are used. Home Assistant's flow manager,
selectors and Bluetooth inventory are simulated, not an HA runtime.
"""

import importlib
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.tuya_ble"


def module(name, **attrs):
    result = ModuleType(name)
    result.__dict__.update(attrs)
    return result


@pytest.fixture(autouse=True)
def isolated_packages(monkeypatch):
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE):
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(
        sys.modules,
        "custom_components",
        module("custom_components", __path__=[str(ROOT / "custom_components")]),
    )
    monkeypatch.setitem(
        sys.modules,
        PACKAGE,
        module(PACKAGE, __path__=[str(ROOT / "custom_components/tuya_ble")]),
    )


@pytest.fixture
def credentials():
    return dict(
        address="AA:BB:CC:DD:EE:FF",
        uuid="0123456789abcdef",
        local_key="test-local-key-01",
        device_id="device-1",
        category="wkf",
        product_id="llflaywg",
        device_name="Valve",
        product_name="TRV",
        product_model="",
    )


class AbortFlow(Exception):
    pass


class Flow:
    def __init_subclass__(cls, **kwargs):
        return super().__init_subclass__()

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_abort(self, **kwargs):
        return {"type": "abort", **kwargs}

    async def async_set_unique_id(self, unique_id, **kwargs):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        if any(e.unique_id == self.unique_id for e in self.entries):
            raise AbortFlow("already_configured")

    def _async_current_entries(self):
        return self.entries

    def _get_reauth_entry(self):
        return self.reauth_entry

    def async_update_reload_and_abort(self, entry, **kwargs):
        self.hass.config_entries.async_update_entry(entry, **kwargs)
        return self.async_abort(reason="reauth_successful")


class Selector:
    def __init__(self, config):
        self.config = config

    def __call__(self, value):
        return value


class Section:
    def __init__(self, schema, options):
        self.schema, self.options = schema, options

    def __call__(self, value):
        return self.schema(value)


@pytest.fixture
def ha(monkeypatch):
    inventory = []
    platform = Enum(
        "Platform", "BUTTON CLIMATE NUMBER SENSOR BINARY_SENSOR SELECT SWITCH TEXT"
    )
    modules = {
        "homeassistant": {},
        "homeassistant.components": {},
        "homeassistant.components.bluetooth": {
            "BluetoothServiceInfoBleak": object,
            "async_discovered_service_info": lambda *args, **kwargs: inventory,
        },
        "homeassistant.components.bluetooth.match": {
            "ADDRESS": "address",
            "BluetoothCallbackMatcher": dict,
        },
        "homeassistant.config_entries": {
            "ConfigEntry": object,
            "ConfigFlow": Flow,
            "OptionsFlow": Flow,
        },
        "homeassistant.core": {
            "callback": lambda func: func,
            "HomeAssistant": object,
            "Event": object,
        },
        "homeassistant.const": {
            "CONF_ADDRESS": "address",
            "EVENT_HOMEASSISTANT_STOP": "stop",
            "Platform": platform,
        },
        "homeassistant.exceptions": {
            "ConfigEntryAuthFailed": type("ConfigEntryAuthFailed", (Exception,), {}),
            "ConfigEntryNotReady": type("ConfigEntryNotReady", (Exception,), {}),
        },
        "homeassistant.data_entry_flow": {"FlowResult": dict, "section": Section},
        "homeassistant.helpers": {},
        "homeassistant.helpers.selector": {
            "TextSelector": Selector,
            "TextSelectorConfig": dict,
            "TextSelectorType": SimpleNamespace(PASSWORD="password"),
            "QrCodeSelector": Selector,
            "QrCodeSelectorConfig": dict,
            "QrErrorCorrectionLevel": SimpleNamespace(QUARTILE="quartile"),
        },
    }
    for name, attrs in modules.items():
        monkeypatch.setitem(sys.modules, name, module(name, **attrs))

    def update_entry(entry, **kwargs):
        for key, value in kwargs.items():
            setattr(entry, key, value)

    async def executor(func, *args):
        return func(*args)

    hass = SimpleNamespace(
        async_add_executor_job=AsyncMock(side_effect=executor),
        data={},
        config_entries=SimpleNamespace(
            async_update_entry=Mock(side_effect=update_entry),
            async_reload=AsyncMock(),
            async_unload_platforms=AsyncMock(return_value=True),
        ),
    )
    return SimpleNamespace(hass=hass, inventory=inventory)


@pytest.fixture
def flow_module(ha):
    return importlib.import_module(PACKAGE + ".config_flow")


@pytest.fixture
def flow(flow_module, ha):
    result = flow_module.TuyaBLEConfigFlow()
    result.hass, result.context, result.entries = ha.hass, {}, []
    return result


@pytest.fixture
def entry(credentials):
    return SimpleNamespace(
        data={"address": credentials["address"]},
        options=dict(credentials),
        version=1,
        minor_version=1,
        unique_id=credentials["address"],
        title="Valve",
        entry_id="entry-1",
    )
