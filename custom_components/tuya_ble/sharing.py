"""Retrieve local credentials through Tuya's official device-sharing SDK.

The public application registration and QR protocol follow Home Assistant's
Tuya integration. Account tokens live only for the duration of the config flow.
"""

from __future__ import annotations

from typing import Any

from requests import Session
from tuya_sharing import LoginControl
from tuya_sharing.customerapi import CustomerApi, CustomerTokenInfo

CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
SCHEMA = "haauthorize"
TOKEN_FIELDS = ("t", "uid", "expire_time", "access_token", "refresh_token")


class SharingError(Exception):
    """An account request failed or returned an incomplete response."""


class _TimeoutSession(Session):
    """Bound SDK requests without changing global SDK or requests behavior."""

    def request(self, method, url, **kwargs):
        kwargs["timeout"] = (10, 30)
        return super().request(method, url, **kwargs)


def _result(response: Any) -> Any:
    if not isinstance(response, dict) or not response.get("success"):
        raise SharingError("Tuya request was not successful")
    return response.get("result")


def request_qr_code(user_code: str) -> str:
    """Request a QR token; the caller renders it locally in Home Assistant."""
    login = LoginControl()
    login.session.close()
    with _TimeoutSession() as login.session:
        result = _result(login.qr_code(CLIENT_ID, SCHEMA, user_code))
    if not isinstance(result, dict) or not result.get("qrcode"):
        raise SharingError("Tuya did not return a QR token")
    return result["qrcode"]


def confirm_login(qr_code: str, user_code: str) -> dict[str, Any] | None:
    """Check app confirmation once; an unconfirmed or expired QR returns None."""
    login = LoginControl()
    login.session.close()
    with _TimeoutSession() as login.session:
        success, info = login.login_result(qr_code, CLIENT_ID, user_code)
    if not success:
        return None
    endpoint = info.get("endpoint") or info.get("end_point")
    if not endpoint or not all(info.get(key) is not None for key in TOKEN_FIELDS):
        raise SharingError("Tuya returned incomplete login data")
    return {
        "user_code": user_code,
        "endpoint": endpoint,
        "token_info": {key: info[key] for key in TOKEN_FIELDS},
    }


class _TokenListener:
    """Keep token refreshes in memory until device retrieval finishes."""

    def __init__(self, session: dict[str, Any]) -> None:
        self.session = session

    def update_token(self, token_info: dict[str, Any]) -> None:
        self.session["token_info"] = dict(token_info)


def get_account_devices(session: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Fetch raw SDK device data, including local_key and UUID, for all homes.

    Use the same home/device endpoints as the SDK repositories. Avoid requesting
    cloud status specifications: these are unnecessary for BLE credentials and
    can be unavailable for otherwise usable Bluetooth devices.
    """
    api = CustomerApi(
        CustomerTokenInfo(session["token_info"]),
        CLIENT_ID,
        session["user_code"],
        session["endpoint"],
        _TokenListener(session),
    )
    api.session.close()
    devices = {}
    with _TimeoutSession() as api.session:
        homes = _result(api.get("/v1.0/m/life/users/homes"))
        if not isinstance(homes, list):
            raise SharingError("Tuya returned an invalid home list")
        for home in homes:
            items = _result(
                api.get(
                    "/v1.0/m/life/ha/home/devices", {"homeId": str(home["ownerId"])}
                )
            )
            if not isinstance(items, list):
                raise SharingError("Tuya returned an invalid device list")
            for item in items:
                if isinstance(item, dict) and item.get("id"):
                    devices[str(item["id"])] = item
    return devices
