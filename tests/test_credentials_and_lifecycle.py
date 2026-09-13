"""Test BLE identity matching, local manager imports and credential migration."""

import hashlib
import importlib
import importlib.util
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from conftest import PACKAGE, ROOT, module
from Crypto.Cipher import AES


def advertisement(uuid, address="AA:BB:CC:DD:EE:FF"):
    product = b"llflaywg"
    key = hashlib.md5(product).digest()
    encrypted = AES.new(key, AES.MODE_CBC, key).encrypt(uuid.encode())
    return SimpleNamespace(
        address=address,
        name="Valve",
        service_uuids=[],
        service_data={"0000a201-0000-1000-8000-00805f9b34fb": b"\x00" + product},
        manufacturer_data={0x07D0: bytes(6) + encrypted},
    )


def test_uuid_decoder_and_malformed_advertisements():
    credentials = importlib.import_module(PACKAGE + ".credentials")
    info = advertisement("0123456789abcdef")
    assert (
        credentials.advertised_uuid(info.service_data, info.manufacturer_data)
        == "0123456789abcdef"
    )
    assert credentials.advertised_uuid({}, {}) is None
    assert credentials.advertised_uuid(info.service_data, {0x07D0: bytes(9)}) is None


def test_generic_wifi_mac_is_not_used():
    credentials = importlib.import_module(PACKAGE + ".credentials")
    device = {"id": "test", "mac": "11:22:33:44:55:66", "local_key": "test-key"}
    assert credentials.shared_device_credentials(device)["address"] == ""
    device["ble_mac"] = "aabbccddeeff"
    assert (
        credentials.shared_device_credentials(device)["address"] == "AA:BB:CC:DD:EE:FF"
    )


@pytest.mark.asyncio
async def test_library_exports_and_local_manager(credentials):
    library = importlib.import_module(PACKAGE + ".tuya_ble")
    assert library.TuyaBLEDevice
    cloud = importlib.import_module(PACKAGE + ".cloud")
    manager = cloud.HASSTuyaBLEDeviceManager(
        object(), {**credentials, "access_secret": "discard"}
    )
    result = await manager.get_device_credentials(credentials["address"], True, True)
    assert result.local_key == credentials["local_key"]
    assert "access_secret" not in manager.data
    assert await manager.get_device_credentials("11:22:33:44:55:66") is None


@pytest.mark.asyncio
async def test_uuid_match_and_mismatch(flow, ha, credentials):
    ha.inventory.append(advertisement(credentials["uuid"]))
    flow._account_devices = {credentials["device_id"]: dict(credentials, address="")}
    await flow.async_step_account_device({"device_id": credentials["device_id"]})
    assert flow._selected["address"] == credentials["address"]
    ha.inventory[0] = advertisement("different-uuid01")
    result = await flow.async_step_device_credentials(credentials)
    assert result["errors"]["base"] == "bluetooth_device_mismatch"


@pytest.fixture
def lifecycle(ha, monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        PACKAGE + ".devices",
        module(
            PACKAGE + ".devices",
            TuyaBLECoordinator=object,
            TuyaBLEData=object,
            get_device_product_info=lambda device: None,
        ),
    )
    spec = importlib.util.spec_from_file_location(
        PACKAGE + "._lifecycle", ROOT / "custom_components/tuya_ble/__init__.py"
    )
    result = importlib.util.module_from_spec(spec)
    result.__package__ = PACKAGE
    spec.loader.exec_module(result)
    return result


@pytest.mark.asyncio
async def test_migration_keeps_keys_and_identity(lifecycle, ha, entry, credentials):
    entry.options.update(
        access_id="retired", access_secret="secret", password="password"
    )
    assert await lifecycle.async_migrate_entry(ha.hass, entry)
    assert entry.options["local_key"] == credentials["local_key"]
    assert entry.options["uuid"] == credentials["uuid"]
    assert entry.unique_id == credentials["address"]
    assert entry.minor_version == 2
    assert "password" not in entry.options
    assert "access_secret" not in entry.options
    assert entry.data == {"address": credentials["address"]}


@pytest.mark.asyncio
async def test_incomplete_legacy_entry_requests_reauth(lifecycle, ha, entry):
    entry.options = {"access_secret": "retired"}
    await lifecycle.async_migrate_entry(ha.hass, entry)
    with pytest.raises(lifecycle.ConfigEntryAuthFailed):
        await lifecycle.async_setup_entry(ha.hass, entry)


@pytest.mark.asyncio
async def test_options_change_reloads_even_without_rename(lifecycle, ha, entry):
    await lifecycle._async_update_listener(ha.hass, entry)
    ha.hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)


@pytest.mark.asyncio
async def test_unload_timeout_does_not_block_removal(lifecycle, ha, entry):
    ha.hass.data["tuya_ble"] = {
        entry.entry_id: SimpleNamespace(
            device=SimpleNamespace(stop=AsyncMock(side_effect=TimeoutError))
        )
    }
    assert await lifecycle.async_unload_entry(ha.hass, entry)
    assert "tuya_ble" not in ha.hass.data


@pytest.mark.asyncio
async def test_failed_platform_unload_keeps_runtime(lifecycle, ha, entry):
    ha.hass.config_entries.async_unload_platforms.return_value = False
    ha.hass.data["tuya_ble"] = {entry.entry_id: object()}
    assert not await lifecycle.async_unload_entry(ha.hass, entry)
    assert entry.entry_id in ha.hass.data["tuya_ble"]


@pytest.mark.asyncio
async def test_discovery_add_prefills_mac_without_decodable_uuid(flow, credentials):
    info = SimpleNamespace(
        address=credentials["address"],
        name="Discovered valve",
        service_uuids=[],
        manufacturer_data={},
        service_data={"0000a201-0000-1000-8000-00805f9b34fb": b"\x01unknown"},
    )
    await flow.async_step_bluetooth(info)
    flow._account_devices = {credentials["device_id"]: dict(credentials, address="")}
    result = await flow.async_step_account_device(
        {"device_id": credentials["device_id"]}
    )
    # Validate the form defaults exactly as a Submit without edits would do.
    submitted = result["data_schema"]({})
    assert submitted["address"] == credentials["address"]
    result = await flow.async_step_device_credentials(submitted)
    assert result["type"] == "create_entry"
    assert result["options"]["address"] == credentials["address"]


@pytest.mark.asyncio
async def test_discovery_fallback_does_not_accept_conflicting_uuid(flow, credentials):
    await flow.async_step_bluetooth(advertisement("different-uuid01"))
    flow._account_devices = {credentials["device_id"]: dict(credentials, address="")}
    result = await flow.async_step_account_device(
        {"device_id": credentials["device_id"]}
    )
    submitted = result["data_schema"]({})
    assert submitted["address"] == ""
    result = await flow.async_step_device_credentials(submitted)
    assert result["errors"]["base"] == "missing_address"


@pytest.mark.asyncio
async def test_exact_uuid_match_wins_over_discovery_card(flow, ha, credentials):
    await flow.async_step_bluetooth(advertisement("different-uuid01"))
    matching = "11:22:33:44:55:66"
    ha.inventory.append(advertisement(credentials["uuid"], matching))
    flow._account_devices = {credentials["device_id"]: dict(credentials, address="")}
    await flow.async_step_account_device({"device_id": credentials["device_id"]})
    assert flow._selected["address"] == matching


@pytest.mark.asyncio
async def test_current_advertisement_wins_over_stale_discovery(flow, ha, credentials):
    stale = advertisement(credentials["uuid"])
    stale.manufacturer_data = {}
    await flow.async_step_bluetooth(stale)
    ha.inventory.append(advertisement("different-uuid01"))
    flow._account_devices = {credentials["device_id"]: dict(credentials, address="")}
    await flow.async_step_account_device({"device_id": credentials["device_id"]})
    assert flow._selected["address"] == ""


@pytest.mark.asyncio
async def test_general_add_does_not_guess_only_nearby_device(flow, ha, credentials):
    info = advertisement(credentials["uuid"])
    info.manufacturer_data = {}
    ha.inventory.append(info)
    flow._account_devices = {credentials["device_id"]: dict(credentials, address="")}
    result = await flow.async_step_account_device(
        {"device_id": credentials["device_id"]}
    )
    submitted = result["data_schema"]({})
    assert submitted["address"] == ""
    submitted["bluetooth_device"] = credentials["address"]
    result = await flow.async_step_device_credentials(submitted)
    assert result["type"] == "create_entry"


@pytest.mark.asyncio
async def test_sdk_bluetooth_mac_is_preserved(flow, credentials):
    other = "11:22:33:44:55:66"
    info = advertisement(credentials["uuid"])
    info.manufacturer_data = {}
    await flow.async_step_bluetooth(info)
    flow._account_devices = {credentials["device_id"]: dict(credentials, address=other)}
    await flow.async_step_account_device({"device_id": credentials["device_id"]})
    assert flow._selected["address"] == other
