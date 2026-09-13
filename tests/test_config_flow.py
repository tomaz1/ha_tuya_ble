"""Regression tests for manual setup, account login and local key persistence."""

from unittest.mock import Mock

import pytest
from conftest import AbortFlow

pytestmark = pytest.mark.asyncio


async def test_user_code_is_first_and_default(flow):
    result = await flow.async_step_user()
    keys = list(result["data_schema"].schema)
    assert [str(key) for key in keys] == ["setup_method", "user_code", "manual"]
    assert keys[0].default() == "user_code"
    assert result["data_schema"].schema[keys[2]].options["collapsed"]


async def test_manual_setup_without_account_request(
    flow, credentials, monkeypatch, flow_module
):
    request = Mock(side_effect=AssertionError("Manual setup must stay offline"))
    monkeypatch.setattr(flow_module, "request_qr_code", request)
    result = await flow.async_step_user(
        {"setup_method": "manual", "manual": credentials}
    )
    assert result["type"] == "create_entry"
    assert result["options"]["local_key"] == credentials["local_key"]
    assert result["data"] == {"address": credentials["address"]}
    request.assert_not_called()


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("local_key", "", "missing_manual_credentials"),
        ("uuid", "", "missing_manual_credentials"),
        ("address", "ZZ:BB:CC:DD:EE:FF", "invalid_address"),
    ],
)
async def test_manual_invalid_credentials(flow, credentials, field, value, error):
    credentials[field] = value
    result = await flow.async_step_user(
        {"setup_method": "manual", "manual": credentials}
    )
    assert result["errors"]["base"] == error


async def test_duplicate_mac(flow, credentials, entry):
    flow.entries = [entry]
    with pytest.raises(AbortFlow):
        await flow.async_step_user({"setup_method": "manual", "manual": credentials})


async def test_duplicate_device_id_at_another_mac(flow, credentials, entry):
    flow.entries = [entry]
    credentials["address"] = "11:22:33:44:55:66"
    result = await flow.async_step_user(
        {"setup_method": "manual", "manual": credentials}
    )
    assert result["reason"] == "already_configured"


async def test_qr_to_saved_key_without_account_tokens(
    flow, flow_module, credentials, monkeypatch
):
    monkeypatch.setattr(flow_module, "request_qr_code", Mock(return_value="test-qr"))
    monkeypatch.setattr(
        flow_module,
        "confirm_login",
        Mock(return_value={"token_info": {"access_token": "secret"}}),
    )
    monkeypatch.setattr(
        flow_module,
        "get_account_devices",
        Mock(
            return_value={
                "device-1": {**credentials, "id": "device-1", "name": "Valve"}
            }
        ),
    )
    result = await flow.async_step_user({"user_code": {"user_code": "code"}})
    assert result["step_id"] == "scan"
    result = await flow.async_step_scan({})
    assert result["step_id"] == "account_device"
    assert flow._session is None
    result = await flow.async_step_account_device({"device_id": "device-1"})
    assert result["step_id"] == "device_credentials"
    result = await flow.async_step_device_credentials(credentials)
    assert result["options"]["local_key"] == credentials["local_key"]
    assert result["options"]["setup_method"] == "user_code"
    assert "secret" not in str(result)
    assert "user_code" not in result["options"]
    assert not flow._account_devices


async def test_qr_pending_regenerate_and_network_error(flow, flow_module, monkeypatch):
    flow._qr_code, flow._user_code = "old", "code"
    monkeypatch.setattr(flow_module, "confirm_login", Mock(return_value=None))
    result = await flow.async_step_scan({})
    assert result["errors"]["base"] == "qr_not_confirmed"
    monkeypatch.setattr(flow_module, "request_qr_code", Mock(return_value="new"))
    await flow.async_step_scan({"new_qr_code": True})
    assert flow._qr_code == "new"
    monkeypatch.setattr(
        flow_module, "confirm_login", Mock(side_effect=RuntimeError("secret"))
    )
    result = await flow.async_step_scan({})
    assert result["errors"]["base"] == "cannot_connect"
    assert "secret" not in str(result)


async def test_device_list_retry(flow, flow_module, monkeypatch, credentials):
    flow._session = {"token_info": {}}
    monkeypatch.setattr(
        flow_module,
        "get_account_devices",
        Mock(side_effect=[RuntimeError(), {"device-1": credentials}]),
    )
    result = await flow.async_step_account_device()
    assert result["errors"]["base"] == "device_list_failed"
    assert flow._session is not None
    result = await flow.async_step_account_device({})
    assert not result["errors"]


async def test_missing_local_key_is_not_saved(flow, credentials):
    flow._selected_device_id = credentials["device_id"]
    credentials["local_key"] = ""
    result = await flow.async_step_device_credentials(credentials)
    assert result["type"] == "form"
    assert result["errors"]["base"] == "missing_manual_credentials"


async def test_options_preserve_identity_and_replace_old_secrets(
    flow_module, ha, entry, credentials
):
    entry.options["access_secret"] = "obsolete"
    flow = flow_module.TuyaBLEOptionsFlow(entry)
    flow.hass = ha.hass
    credentials["local_key"] = "new-local-key"
    result = await flow.async_step_init(
        {"setup_method": "manual", "manual": credentials}
    )
    assert result["data"]["address"] == entry.data["address"]
    assert result["data"]["local_key"] == "new-local-key"
    assert "access_secret" not in result["data"]
    assert entry.options == result["data"]
    assert (
        ha.hass.config_entries.async_update_entry.call_args.kwargs["options"]
        == result["data"]
    )
    credentials["device_id"] = "another-device"
    result = await flow.async_step_init(
        {"setup_method": "manual", "manual": credentials}
    )
    assert result["errors"]["base"] == "wrong_device"


async def test_reauth_keeps_existing_entry(flow, entry, credentials):
    flow.reauth_entry = entry
    result = await flow.async_step_reauth(entry.data)
    assert result["step_id"] == "user"
    credentials["local_key"] = "updated-key"
    result = await flow.async_step_user(
        {"setup_method": "manual", "manual": credentials}
    )
    assert result["reason"] == "reauth_successful"
    assert entry.options["local_key"] == "updated-key"
    assert entry.unique_id == credentials["address"]
