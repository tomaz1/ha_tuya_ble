"""The Tuya BLE integration."""

from __future__ import annotations

from typing_extensions import Final

# Enable verbose Tuya BLE debug logging
DEBUG_LOG = False

DOMAIN: Final = "tuya_ble"

DEVICE_METADATA_UUIDS: Final = "uuids"

DEVICE_DEF_MANUFACTURER: Final = "Tuya"
SET_DISCONNECTED_DELAY = 10 * 60

CONF_UUID: Final = "uuid"
CONF_LOCAL_KEY: Final = "local_key"
CONF_CATEGORY: Final = "category"
CONF_PRODUCT_ID: Final = "product_id"
CONF_DEVICE_NAME: Final = "device_name"
CONF_PRODUCT_MODEL: Final = "product_model"
CONF_PRODUCT_NAME: Final = "product_name"

BATTERY_STATE_LOW: Final = "low"
BATTERY_STATE_NORMAL: Final = "normal"
BATTERY_STATE_HIGH: Final = "high"

BATTERY_NOT_CHARGING: Final = "not_charging"
BATTERY_CHARGING: Final = "charging"
BATTERY_CHARGED: Final = "charged"

CO2_LEVEL_NORMAL: Final = "normal"
CO2_LEVEL_ALARM: Final = "alarm"

FINGERBOT_MODE_PUSH: Final = "push"
FINGERBOT_MODE_SWITCH: Final = "switch"
FINGERBOT_MODE_PROGRAM: Final = "program"
FINGERBOT_BUTTON_EVENT: Final = "fingerbot_button_pressed"

WINDOW_OPENED: Final = "opened"
WINDOW_CLOSED: Final = "closed"

WORK_STATE_OFF: Final = "closed"
WORK_STATE_ON: Final = "opened"

MOTOR_THRUST_STRONG: Final = "strong"
MOTOR_THRUST_MIDDLE: Final = "middle"
MOTOR_THRUST_WEAK: Final = "weak"

LED_BRIGHTNESS_HIGH: Final = "high"
LED_BRIGHTNESS_MID: Final = "mid"
LED_BRIGHTNESS_LOW: Final = "low"
LED_BRIGHTNESS_ALL: Final = [
    LED_BRIGHTNESS_HIGH,
    LED_BRIGHTNESS_MID,
    LED_BRIGHTNESS_LOW,
]

SCREEN_ORIENTATION_UP: Final = "up"
SCREEN_ORIENTATION_DOWN: Final = "down"
SCREEN_ORIENTATION_LEFT: Final = "left"
SCREEN_ORIENTATION_RIGHT: Final = "right"
SCREEN_ORIENTATION_ALL: Final = [
    SCREEN_ORIENTATION_UP,
    SCREEN_ORIENTATION_DOWN,
    SCREEN_ORIENTATION_LEFT,
    SCREEN_ORIENTATION_RIGHT,
]
SCREEN_ORIENTATION_VALUE_MAP: Final = {
    SCREEN_ORIENTATION_UP: 0,
    SCREEN_ORIENTATION_DOWN: 2,
}  # needed for llflaywg, which only supports 0 and 2 as values
