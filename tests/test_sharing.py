"""Exercise credential retrieval with the actual device-sharing SDK boundary."""

import importlib
from unittest.mock import Mock

import pytest
from conftest import PACKAGE


def test_real_sdk_qr_protocol(monkeypatch):
    sharing = importlib.import_module(PACKAGE + ".sharing")
    request = Mock(
        return_value=Mock(
            json=lambda: {"success": True, "result": {"qrcode": "qr-test"}}
        )
    )
    monkeypatch.setattr(sharing._TimeoutSession, "request", request)
    assert sharing.request_qr_code("user-test") == "qr-test"
    args = request.call_args.args
    assert args[0] == "POST"
    assert "clientid=HA_3y9q4ak7g4ephrvke" in args[1]
    assert "usercode=user-test" in args[1]


def test_real_sdk_login_and_missing_tokens(monkeypatch):
    sharing = importlib.import_module(PACKAGE + ".sharing")
    info = dict(
        uid="user",
        expire_time=3600,
        access_token="access",
        refresh_token="refresh",
        endpoint="https://example.test",
    )
    request = Mock(
        return_value=Mock(json=lambda: {"success": True, "t": 123, "result": info})
    )
    monkeypatch.setattr(sharing._TimeoutSession, "request", request)
    session = sharing.confirm_login("qr", "code")
    assert session["token_info"]["t"] == 123
    assert session["token_info"]["refresh_token"] == "refresh"
    del info["access_token"]
    with pytest.raises(sharing.SharingError):
        sharing.confirm_login("qr", "code")


def test_unconfirmed_qr(monkeypatch):
    sharing = importlib.import_module(PACKAGE + ".sharing")
    monkeypatch.setattr(
        sharing._TimeoutSession,
        "request",
        Mock(return_value=Mock(json=lambda: {"success": False, "code": "pending"})),
    )
    assert sharing.confirm_login("qr", "code") is None


def test_all_homes_keep_local_key_and_deduplicate(monkeypatch):
    sharing = importlib.import_module(PACKAGE + ".sharing")
    device = {"id": "ble-1", "uuid": "uuid", "local_key": "key"}
    get = Mock(
        side_effect=[
            {"success": True, "result": [{"ownerId": 1}, {"ownerId": 2}]},
            {"success": True, "result": [device]},
            {"success": True, "result": [device, {"id": "ble-2", "local_key": "key2"}]},
        ]
    )
    monkeypatch.setattr(sharing.CustomerApi, "get", get)
    session = {
        "user_code": "code",
        "endpoint": "https://example.test",
        "token_info": {},
    }
    result = sharing.get_account_devices(session)
    assert len(result) == 2
    assert result["ble-1"]["local_key"] == "key"
    assert get.call_args_list[2].args[1] == {"homeId": "2"}


@pytest.mark.parametrize(
    "response", [None, {"success": False}, {"success": True, "result": {}}]
)
def test_invalid_account_responses(monkeypatch, response):
    sharing = importlib.import_module(PACKAGE + ".sharing")
    monkeypatch.setattr(sharing.CustomerApi, "get", Mock(return_value=response))
    with pytest.raises(sharing.SharingError):
        sharing.get_account_devices(
            {"user_code": "code", "endpoint": "https://example.test", "token_info": {}}
        )


def test_request_timeouts_are_instance_local(monkeypatch):
    sharing = importlib.import_module(PACKAGE + ".sharing")
    request = Mock()
    monkeypatch.setattr(sharing.Session, "request", request)
    with sharing._TimeoutSession() as session:
        session.request("GET", "https://example.test")
    assert request.call_args.kwargs["timeout"] == (10, 30)
