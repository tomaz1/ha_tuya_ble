"""The Tuya BLE integration."""
from __future__ import annotations

from dataclasses import dataclass

import logging
from typing import Callable

from homeassistant.components.climate import (
    ClimateEntityDescription,
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
    PRESET_AWAY,
    PRESET_NONE,
    PRESET_COMFORT,
    PRESET_ECO,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPoint, TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)


@dataclass
class TuyaBLEClimateMapping:
    description: ClimateEntityDescription

    hvac_mode_bool_dp_id: int = 0  # hvac_switch_dp_id: int = 0
    hvac_mode_value_dp_id: int = 0
    hvac_mode_enum_dp_id: int = 0

    hvac_modes: list[str] | None = None
    value_map: dict[HVACMode, int] = None
    hvac_switch_mode: HVACMode | None = None

    preset_mode_dp_ids: dict[str, int] | None = None

    temperature_unit: str = UnitOfTemperature.CELSIUS
    current_temperature_dp_id: int = 0
    current_temperature_coefficient: float = 1.0
    target_temperature_dp_id: int = 0
    target_temperature_coefficient: float = 1.0
    target_temperature_max: float = 30.0
    target_temperature_min: float = 5
    target_temperature_step: float = 1.0

    current_humidity_dp_id: int = 0
    current_humidity_coefficient: float = 1.0
    target_humidity_dp_id: int = 0
    target_humidity_coefficient: float = 1.0
    target_humidity_max: float = 100.0
    target_humidity_min: float = 0.0


@dataclass
class TuyaBLECategoryClimateMapping:
    products: dict[str, list[TuyaBLEClimateMapping]] | None = None
    mapping: list[TuyaBLEClimateMapping] | None = None


mapping: dict[str, TuyaBLECategoryClimateMapping] = {
    "wk": TuyaBLECategoryClimateMapping(
        products={
            **dict.fromkeys(
                [
                "drlajpqc", 
                "nhj2j7su",
                ],  # Thermostatic Radiator Valve
                [
                # Thermostatic Radiator Valve
                # - [x] 8   - Window
                # - [x] 10  - Antifreeze
                # - [x] 27  - Calibration
                # - [x] 40  - Lock
                # - [x] 101 - Switch
                # - [x] 102 - Current
                # - [x] 103 - Target
                # - [ ] 104 - Heating time
                # - [x] 105 - Battery power alarm
                # - [x] 106 - Away
                # - [x] 107 - Programming mode
                # - [x] 108 - Programming switch
                # - [ ] 109 - Programming data (deprecated - do not delete)
                # - [ ] 110 - Historical data protocol (Day-Target temperature)
                # - [ ] 111 - System Time Synchronization
                # - [ ] 112 - Historical data (Week-Target temperature)
                # - [ ] 113 - Historical data (Month-Target temperature)
                # - [ ] 114 - Historical data (Year-Target temperature)
                # - [ ] 115 - Historical data (Day-Current temperature)
                # - [ ] 116 - Historical data (Week-Current temperature)
                # - [ ] 117 - Historical data (Month-Current temperature)
                # - [ ] 118 - Historical data (Year-Current temperature)
                # - [ ] 119 - Historical data (Day-motor opening degree)
                # - [ ] 120 - Historical data (Week-motor opening degree)
                # - [ ] 121 - Historical data (Month-motor opening degree)
                # - [ ] 122 - Historical data (Year-motor opening degree)
                # - [ ] 123 - Programming data (Monday)
                # - [ ] 124 - Programming data (Tuseday)
                # - [ ] 125 - Programming data (Wednesday)
                # - [ ] 126 - Programming data (Thursday)
                # - [ ] 127 - Programming data (Friday)
                # - [ ] 128 - Programming data (Saturday)
                # - [ ] 129 - Programming data (Sunday)
                # - [x] 130 - Water scale
                TuyaBLEClimateMapping(
                    description=ClimateEntityDescription(
                        key="thermostatic_radiator_valve",
                    ),
                    hvac_mode_bool_dp_id=101,
                    hvac_switch_mode=HVACMode.HEAT,
                    hvac_modes=[HVACMode.OFF, HVACMode.HEAT],
                    preset_mode_dp_ids={PRESET_AWAY: 106, PRESET_NONE: 106},
                    current_temperature_dp_id=102,
                    current_temperature_coefficient=10.0,
                    target_temperature_coefficient=10.0,
                    target_temperature_step=0.5,
                    target_temperature_dp_id=103,
                    target_temperature_min=5.0,
                    target_temperature_max=30.0,
                    ),
                ],
            ),
        },
    ),
    "wkf": TuyaBLECategoryClimateMapping(
        products={
            **dict.fromkeys(
                [
                "llflaywg",
                ],  # Thermostatic Radiator Valve
                [
                # Thermostatic Radiator Valve
                # - [RW] DPID code,               Type,     values,                                   - Comment
                    
                # - [RW] 1,   mode,               Enum,     "auto","manual","off","on"                - Operation mode
                # - [R ] 2,   temp_set,           Integer,  "min":50,"max":350,"scale":1,"step":5,    - Valve temperature setting (devide by 10 to get C)
                # - [R ] 3,   temp_current,       Integer,  "min":-300,"max":1000,"scale":1,"step":5  - Current room temerature (devide by 10 to get C)
                # - [R ] 6,   work_state,         Enum,     "closed","opened"                         - Current valve state
                # - [R ] 7,   window_state,       Enum,     "closed","opened"                         - Current windows state
                # - [RW] 8,   window_check,       Boolean,  true,false                                - Settings to check window status (on/off)
                # - [RW] 12,  child_lock,         Boolean,  true,false                                - Settings to set child lock (on/off)
                # - [R ] 13,  battery_percentage, Integer,  "min":0,"max":100,"scale":0,"step":1      - Battery level in %
                # - [  ] 14,  fault,              Bitmap,   fault_sensor/motorlow_batt/ug_low_batt    - Fault reason
                # - [? ] 15,  lower_temp,         Integer,  "min":50,"max":150,"scale":1,"step":10    - Minimum temperature setting (devide by 10 to get C)
                # - [? ] 16,  upper_temp,         Integer,  "min":200,"max":350,"scale":1,"step":10   - Maximum temperature setting (devide by 10 to get C)
                # - [  ] 17,  week_program_13_1,  Raw,      TODO, example: AQEAAMgGHgDXCAAAlg8AANI=   - Probably daily heating schedule for Monday/Saturday
                # - [  ] 18,  week_program_13_2,  Raw,      TODO                                      - Probably daily heating schedule
                # - [  ] 19,  week_program_13_3,  Raw,      TODO                                      - Probably daily heating schedule
                # - [  ] 20,  week_program_13_4,  Raw,      TODO                                      - Probably daily heating schedule
                # - [  ] 21,  week_program_13_5,  Raw,      TODO                                      - Probably daily heating schedule
                # - [  ] 22,  week_program_13_6,  Raw,      TODO                                      - Probably daily heating schedule
                # - [  ] 23,  week_program_13_7,  Raw,      TODO                                      - Probably daily heating schedule
                # - [RW] 101, temp_correction,    Integer,  "min":-100,"max":100,"scale":1,"step":1   - Temperature correcton [can be negative] (devide by 10 to get C)
                # - [R ] 108, valve_open_degree,  Integer,  "min":0,"max":1000,"scale":1,"step":10    - (read only) Valve open degree (Tested myself and it is read only!)
                # - [R ] 109, mfg_model,          String,   TODO, example: bt3l_60x\u0000             - (read only) - ?? Manufacturing ??
                # - [R ] 110, motor_thrust,       Enum,     "strong","middle","weak"                  - Motor thrust
                # - [RW] 111, brightness,         Enum,     "high","mid","low"                        - LEDs brightness
                # - [R ] 112, soft_version,       Integer,  "min":0,"max":65536,"scale":0,"step":1    - (read only) - Software version
                # - [RW] 113, screen_orientation, Enum,     "up","right","down","left"                - Screen/LEDs orientaton (Tested myself and it is only UP or DOWN!)
                # - [RW] 114, system_mode,        Enum,     "comfort_mode","Eco_mode"                 - System mode (Comfort or Eco mode)
                # - [RW] 115, switch_wrap,        Integer,  "min":5,"max":50,"scale":1,"step":1       - Switch deviation (energy-saving mode only)
                # - [  ] 116, motor_data,         String,   TODO, example: 615, 2944, 0, 321          - (read only) - Motor data
                #
                #GLEJ, kakšnega tipa so vrednosti, ki jih vrnejo ti DPID-ji:

                # Connected; RSSI: -80
                # Sending device info request
                # Sending packet: #1 FUN_SENDER_DEVICE_INFO
                # Packet received: 008101300493c48547afc3ab8f9b951bec49faa1
                # Packet received: 0105d467397f08c92c96737dfc839f5480c2cc58
                # Packet received: 022522023b95d5510d67d429f6a0c01a5779ffdd
                # Packet received: 038bf1c71aed77afc02d3db687f94f2f8fa30f16
                # Packet received: 04f7b26c53722a6d5baf5e6d80d30fad7055d520
                # Packet received: 05d94a956bc23e213a064f6fd0547b5cdf414d9b
                # Packet received: 0640b649edb96c6aed7d367f06f91a2f0b4040
                # Received: #1 FUN_SENDER_DEVICE_INFO, response to #1
                # Received expected response to #1, result: 0
                # Sending pairing request
                # Sending packet: #2 FUN_SENDER_PAIR
                # Packet received: 00213005e2f6d7027ffa92aa57245478fbd583be
                # Packet received: 01d3ccae1cf2cd078f47bcf3e77f7c4e64
                # Received: #2 FUN_SENDER_PAIR, response to #2
                # Device is already paired
                # Received expected response to #2, result: 0
                # Packet received: 002130058b3ac52b7c6498659135be3957b92a5e
                # Successfully connected
                # Sending packet: #3 FUN_SENDER_DEVICE_STATUS
                # Packet received: 01e2e94680082d76d22b70ea744fcfa1f4
                # Received: #3 FUN_RECEIVE_TIME1_REQ
                # Sending packet: #4 FUN_RECEIVE_TIME1_REQ in response to #3
                # Operation already in progress, waiting for it to complete; RSSI: -80
                # Packet received: 0021300544f4415730b2fbc31a1eb012f47db4c8
                # Packet received: 0171e3088a33961f262d1b9a73e71fe8f9
                # Received: #4 FUN_SENDER_DPS, response to #3
                # Received expected response to #3, result: 0
                # Packet received: 0081013005f332893c6c267643606287d023b1f9
                # Packet received: 0152f67129ba3822b5cdc48bf13c9a0bb76959d9
                # Packet received: 02d07de4905bd3d830ada971d7094da3ccc68d6b
                # Packet received: 03c3a2fa9c018a26d2c0417cc448538986930bda
                # Packet received: 04e897ee07eb3d66e19509819c1099d162e8cfab
                # Packet received: 050e2c653fc1d2916b261261b40453eac345605c
                # Packet received: 06f7843a534b9214e7c92b6e274ab7db3c622b
                # Received: #5 FUN_RECEIVE_DP
                # Received datapoint update, id: 14, type: DT_BITMAP: value: b'\x00'
                # Received datapoint update, id: 1, type: DT_ENUM: value: 1
                # Received datapoint update, id: 2, type: DT_VALUE: value: 70
                # Received datapoint update, id: 3, type: DT_VALUE: value: 255
                # Received datapoint update, id: 6, type: DT_ENUM: value: 0
                # Received datapoint update, id: 7, type: DT_ENUM: value: 0
                # Received datapoint update, id: 8, type: DT_BOOL: value: False
                # Received datapoint update, id: 16, type: DT_VALUE: value: 300
                # Received datapoint update, id: 15, type: DT_VALUE: value: 50
                # Received datapoint update, id: 12, type: DT_BOOL: value: False
                # Received datapoint update, id: 13, type: DT_VALUE: value: 67
                # Received datapoint update, id: 101, type: DT_VALUE: value: 0
                # Received datapoint update, id: 109, type: DT_STRING: value: bt3l_60x
                # Received datapoint update, id: 110, type: DT_ENUM: value: 1
                # Received datapoint update, id: 111, type: DT_ENUM: value: 0
                # Sending packet: #5 FUN_RECEIVE_DP in response to #5
                # Packet received: 006130053ea88a630d48a7cef3a5fc9afa031864
                # Packet received: 018c72fd1937179f5ef5ef5b5c23e8844a2ea982
                # Packet received: 0255070264e8827673dff2c5e7962585a22a086f
                # Packet received: 034cc0889dd133dd1af1d75ab131f8048da31d1b
                # Packet received: 04df1f3bd75bdb25bca9f65b94855bd70e28d20b
                # Packet received: 05e88c2b8d
                # Received: #6 FUN_RECEIVE_DP
                # Received datapoint update, id: 112, type: DT_VALUE: value: 1003
                # Received datapoint update, id: 113, type: DT_ENUM: value: 0
                # Received datapoint update, id: 108, type: DT_VALUE: value: 0
                # Received datapoint update, id: 115, type: DT_VALUE: value: 5
                # Received datapoint update, id: 116, type: DT_STRING: value: 617, 2805, 0, 341, 5ohm, 4002
                # Received datapoint update, id: 114, type: DT_ENUM: value: 0
                # Sending packet: #6 FUN_RECEIVE_DP in response to #6
                # Packet received: 00413005749f31db48dbd207891929bac39ee87b
                # Packet received: 01f41fd0713c88a0ce4185ba65ff99304f0f33d8
                # Packet received: 02feef118d93590fcb39e691c72cc2de1ee8bc1a
                # Packet received: 0317c77c659b33c7c40c36
                # Received: #7 FUN_RECEIVE_DP
                # Received datapoint update, id: 17, type: DT_RAW: value: b'\x01\x01\x00\x00\xcd\x06\x1e\x00\xdc\x08\x00\x00\xaf\x0e\x00\x00\xdc'
                # Sending packet: #7 FUN_RECEIVE_DP in response to #7
                # Packet received: 00413005f2fbe6bfd897f1982e52e284b15f3541
                # Packet received: 017cbcbe0f6363241a50bdc7b1dd09e34f6c7292
                # Packet received: 02687c1eeaebe6c8b967c335443e8ed96fbd0425
                # Packet received: 033ad1730db5d2911ad227
                # Received: #8 FUN_RECEIVE_DP
                # Received datapoint update, id: 18, type: DT_RAW: value: b'\x02\x01\x00\x00\xcd\x06\x1e\x00\xdc\x08\x00\x00\xaf\x0e\x00\x00\xdc'
                # Sending packet: #8 FUN_RECEIVE_DP in response to #8
                # Packet received: 004130050935b3dbfc260a7adbb8be967b3bb095
                # Packet received: 01fcb16348686bab20cfc6ba378ef5a3ac1213a5
                # Packet received: 02fe8d1ebdadea4c14414f5ef31d936510e05f77
                # Packet received: 03707c5ae7150a4354ec37
                # Received: #9 FUN_RECEIVE_DP
                # Received datapoint update, id: 19, type: DT_RAW: value: b'\x03\x01\x00\x00\xcd\x06\x1e\x00\xdc\x08\x00\x00\xaf\x0e\x00\x00\xdc'
                # Sending packet: #9 FUN_RECEIVE_DP in response to #9
                # Packet received: 004130054e6636f4b9914684f25fc61c6808aecd
                # Packet received: 01d154a99775aeb2adec3eaac842f642ccc3cb7c
                # Packet received: 022d75dfc3bfeb109258a84daf86bef8b0464f86
                # Packet received: 034db28f4d70d25da4290c
                # Received: #10 FUN_RECEIVE_DP
                # Received datapoint update, id: 20, type: DT_RAW: value: b'\x04\x01\x00\x00\xcd\x06\x1e\x00\xdc\x08\x00\x00\xaf\x0e\x00\x00\xdc'
                # Sending packet: #10 FUN_RECEIVE_DP in response to #10
                # Packet received: 0041300564bc92a880aeb2e2efc83149bb831a00
                # Packet received: 010034f560824a892cdfd225e5962b0f6e80b586
                # Packet received: 02348959e36534bd7905cc86d86069031db97a6b
                # Packet received: 0360ea5fdb4eb3ea304976
                # Received: #11 FUN_RECEIVE_DP
                # Received datapoint update, id: 21, type: DT_RAW: value: b'\x05\x01\x00\x00\xcd\x06\x1e\x00\xdc\x08\x00\x00\xaf\x0e\x00\x00\xdc'
                # Sending packet: #11 FUN_RECEIVE_DP in response to #11
                # Packet received: 00413005883b9d0f7aab1b5a8ddd23ef9d1cc404
                # Packet received: 01d7ee0751bc99950a1528e4ffcc8a617e8b10b4
                # Packet received: 022c4548dc11d173a673fd3de7cca1740e191ca4
                # Packet received: 037625ccba45784dbf95ef
                # Received: #12 FUN_RECEIVE_DP
                # Received datapoint update, id: 22, type: DT_RAW: value: b'\x06\x00\x00\x00\xd7\x00\x01\x00\xd7\x00\x02\x00\xd7\x00\x03\x00\xd7'
                # Sending packet: #12 FUN_RECEIVE_DP in response to #12
                # Packet received: 00413005bf8937a95abcd053ff972055fd38dde1
                # Packet received: 0125ef597afb4f121569f5fff235aeca563b237d
                # Packet received: 02e096a75f2d247d82f9ce33debae633d5e1fcd9
                # Packet received: 03a06836d88a66ada9aa3e
                # Received: #13 FUN_RECEIVE_DP
                # Received datapoint update, id: 23, type: DT_RAW: value: b'\x07\x00\x00\x00\xd7\x00\x01\x00\xd7\x00\x02\x00\xdc\x17;\x00\xcd'
                # Sending packet: #13 FUN_RECEIVE_DP in response to #13

                #in še Climate objekt na HA: https://developers.home-assistant.io/docs/core/entity/climate/

                TuyaBLEClimateMapping(
                    description=ClimateEntityDescription(
                        key="thermostatic_radiator_valve",
                    ),
                    hvac_mode_enum_dp_id=1,
                    # value_map preslika HVACMode → integer, enako velja za enum in value tipe
                    value_map = {
                            HVACMode.AUTO: 0,
                            HVACMode.HEAT: 1,   # manual → heat
                            HVACMode.OFF: 2,
                            # 3 odpre ventil na 100% (izbral FAN_ONLY, ker je to edina možnost, ki jo poznam))
                            HVACMode.DRY: 3,
                    },
                    hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF, HVACMode.DRY],
                    preset_mode_dp_ids={PRESET_COMFORT: 114, PRESET_ECO: 114},
                    current_temperature_dp_id=3,
                    current_temperature_coefficient=10.0,
                    target_temperature_coefficient=10.0,
                    target_temperature_step=0.5,
                    target_temperature_dp_id=2,
                    target_temperature_min=5.0,
                    target_temperature_max=30.0,
                    ),
                ],
            ),
        },
    ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLECategoryClimateMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
            return category.mapping
        else:
            return []
    else:
        return []


class TuyaBLEClimate(TuyaBLEEntity, ClimateEntity):
    """Representation of a Tuya BLE Climate."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLEClimateMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping
        self._attr_hvac_mode = HVACMode.HEAT
        self._attr_preset_mode = PRESET_NONE
        self._attr_hvac_action = HVACAction.HEATING
        self._attr_translation_key = "valve_mode"

        # _LOGGER.info(f"Test !!! ") #Krnekje našel kako se logira, tu je bilo še... a tu verjetno ni OK.. pustil da vidim kako se doda spremenljivke{self.entity_description.name}

        if mapping.hvac_mode_bool_dp_id and mapping.hvac_switch_mode:
            self._attr_hvac_modes = [HVACMode.OFF, mapping.hvac_switch_mode]
        elif mapping.hvac_mode_enum_dp_id and mapping.hvac_modes:
            self._attr_hvac_modes = mapping.hvac_modes
        elif mapping.hvac_mode_value_dp_id and mapping.value_map:
            self._attr_hvac_modes = list(mapping.value_map.keys())
        else:
            self._attr_hvac_modes = []

        if mapping.preset_mode_dp_ids:
            self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE
            self._attr_preset_modes = list(mapping.preset_mode_dp_ids.keys())

        if mapping.target_temperature_dp_id != 0:
            #self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
            self._attr_temperature_unit = mapping.temperature_unit
            self._attr_max_temp = mapping.target_temperature_max
            self._attr_min_temp = mapping.target_temperature_min
            self._attr_target_temperature_step = mapping.target_temperature_step

        if mapping.target_humidity_dp_id != 0:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_HUMIDITY
            self._attr_max_humidity = mapping.target_humidity_max
            self._attr_min_humidity = mapping.target_humidity_min
            
    #https://github.com/kamaradclimber/heishamon-homeassistant/blob/0ac5769d64848b8c46feb69c6260dc7a53bd3242/custom_components/aquarea/climate.py
    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEATING)
       
    @property
    def icon(self) -> str | None:
        """Prikaži specifično ikono za - 100% odpreti ventil (DRY = Open 100 %) in ostale načine delovanja."""
        if self._attr_hvac_mode == HVACMode.DRY:
            return "mdi:valve-open"
        if self._attr_hvac_mode == HVACMode.HEAT:
            return "mdi:fire-circle"
        if self._attr_hvac_mode == HVACMode.AUTO:
            return "mdi:thermostat-auto"
        if self._attr_hvac_mode == HVACMode.OFF:
            return "mdi:valve-closed"
        return super().icon

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        # 🔹 Temperature in vlaga
        if self._mapping.current_temperature_dp_id:
            dp = self._device.datapoints[self._mapping.current_temperature_dp_id]
            if dp:
                self._attr_current_temperature = dp.value / self._mapping.current_temperature_coefficient

        if self._mapping.target_temperature_dp_id:
            dp = self._device.datapoints[self._mapping.target_temperature_dp_id]
            if dp:
                self._attr_target_temperature = dp.value / self._mapping.target_temperature_coefficient

        if self._mapping.current_humidity_dp_id:
            dp = self._device.datapoints[self._mapping.current_humidity_dp_id]
            if dp:
                self._attr_current_humidity = dp.value / self._mapping.current_humidity_coefficient

        if self._mapping.target_humidity_dp_id:
            dp = self._device.datapoints[self._mapping.target_humidity_dp_id]
            if dp:
                self._attr_target_humidity = dp.value / self._mapping.target_humidity_coefficient

        # 🔹 Način delovanja (hvac_mode)
        mode = None

        # 1) Boolean tip (ON/OFF)
        if self._mapping.hvac_mode_bool_dp_id and self._mapping.hvac_switch_mode:
            dp = self._device.datapoints[self._mapping.hvac_mode_bool_dp_id]
            if dp:
                mode = self._mapping.hvac_switch_mode if dp.value else HVACMode.OFF

        # 2) Enum tip (uporabi direktno hvac_modes seznam po indeksu dp.value)
        elif self._mapping.hvac_mode_enum_dp_id:
            dp = self._device.datapoints[self._mapping.hvac_mode_enum_dp_id]
            if dp:
                if dp.value == 0:
                    mode = HVACMode.AUTO
                #elif dp.value in (1, 3):  # manual ali on
                elif dp.value == 1:  # manual ali on
                    mode = HVACMode.HEAT
                elif dp.value == 2:
                    mode = HVACMode.OFF
                elif dp.value == 3:
                    mode = HVACMode.DRY

        # 3) Integer/value tip (uporabi value_map)
        elif self._mapping.hvac_mode_value_dp_id and self._mapping.value_map:
            dp = self._device.datapoints[self._mapping.hvac_mode_value_dp_id]
            if dp:
                for hvac_mode, value in self._mapping.value_map.items():
                    if dp.value == value:
                        mode = hvac_mode
                        break

        self._attr_hvac_mode = mode

        # 🔹 Preset mode
        if self._mapping.preset_mode_dp_ids:
            current_preset = PRESET_NONE
            dp_ids = list(self._mapping.preset_mode_dp_ids.values())

            if all(dp_ids[0] == dp_id for dp_id in dp_ids):
                # ENUM način
                dp = self._device.datapoints[dp_ids[0]]
                if dp and isinstance(dp.value, int):
                    # 0 → "comfort_mode", 1 → "Eco_mode"
                    # preslikaj v HA prepoznavne konstante
                    if dp.value == 0:
                        current_preset = PRESET_COMFORT
                    elif dp.value == 1:
                        current_preset = PRESET_ECO
            else:
                # BOOL način
                for preset, dp_id in self._mapping.preset_mode_dp_ids.items():
                    dp = self._device.datapoints[dp_id]
                    if dp and dp.value:
                        current_preset = preset
                        break

            self._attr_preset_mode = current_preset

        # 🔹 HVAC akcija (ogrevanje ali idle)
        try:
            if (
                self._attr_preset_mode == PRESET_AWAY
                or self._attr_hvac_mode == HVACMode.OFF
                or (
                    self._attr_target_temperature is not None
                    and self._attr_current_temperature is not None
                    and self._attr_target_temperature <= self._attr_current_temperature
                )
            ):
                self._attr_hvac_action = HVACAction.IDLE
            else:
                self._attr_hvac_action = HVACAction.HEATING
        except Exception:
            self._attr_hvac_action = HVACAction.IDLE

        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if self._mapping.target_temperature_dp_id != 0:
            int_value = int(
                kwargs["temperature"] * self._mapping.target_temperature_coefficient
            )
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.target_temperature_dp_id,
                TuyaBLEDataPointType.DT_VALUE,
                int_value,
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(int_value))

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        if self._mapping.target_humidity_dp_id != 0:
            int_value = int(humidity * self._mapping.target_humidity_coefficient)
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.target_humidity_dp_id,
                TuyaBLEDataPointType.DT_VALUE,
                int_value,
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(int_value))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        # da imamo hvac_mode vedno tipa HVACMode:
        #_LOGGER.warning(f"--------Received hvac_mode: {hvac_mode} ({type(hvac_mode)})")
        #if isinstance(hvac_mode, str):
        #    try:
        #        hvac_mode = HVACMode(hvac_mode)
        #    except ValueError:
        #        raise ValueError(f"Invalid hvac_mode string: {hvac_mode}")

        # 1) Boolean tip
        if self._mapping.hvac_mode_bool_dp_id and self._mapping.hvac_switch_mode:
            desired = hvac_mode == self._mapping.hvac_switch_mode
            dp = self._device.datapoints.get_or_create(
                self._mapping.hvac_mode_bool_dp_id,
                TuyaBLEDataPointType.DT_BOOL,
                desired,
            )
            if dp:
                self._hass.create_task(dp.set_value(desired))
            return

        # 2) Integer / value ali Enum tip (uporablja enako value_map)
        if (self._mapping.hvac_mode_value_dp_id or self._mapping.hvac_mode_enum_dp_id) \
        and self._mapping.value_map:
            # preslikava HVACMode v integer vrednost
            int_value = self._mapping.value_map.get(hvac_mode)
            if int_value is None:
                raise ValueError(f"No mapping for HVAC mode {hvac_mode}")
            dp_id = (self._mapping.hvac_mode_value_dp_id
                    if self._mapping.hvac_mode_value_dp_id
                    else self._mapping.hvac_mode_enum_dp_id)
            dp_type = (TuyaBLEDataPointType.DT_VALUE
                    if self._mapping.hvac_mode_value_dp_id
                    else TuyaBLEDataPointType.DT_ENUM)
            dp = self._device.datapoints.get_or_create(
                dp_id,
                dp_type,
                int_value,
            )
            if dp:
                self._hass.create_task(dp.set_value(int_value))
            return

        # Noben veljaven datapoint ni konfiguriran
        raise NotImplementedError("No valid HVAC mode datapoint configured")


    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode, supporting both ENUM and BOOL datapoints."""
        dp_ids = list(self._mapping.preset_mode_dp_ids.values())

        if dp_ids and all(dp_ids[0] == dp_id for dp_id in dp_ids):
            # ENUM način
            dp_id = dp_ids[0]
            preset_mode_enum_map = {
                PRESET_COMFORT: 0,
                PRESET_ECO: 1,
                PRESET_AWAY: 2,
                PRESET_NONE: 3,
            }
            enum_value = preset_mode_enum_map.get(preset_mode)
            if enum_value is None:
                raise ValueError(f"Unknown preset_mode: {preset_mode}")

            datapoint = self._device.datapoints.get_or_create(
                dp_id, TuyaBLEDataPointType.DT_ENUM, enum_value
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(enum_value))
        else:
            # BOOLEAN način — vsak preset ima svoj dp_id
            for preset, dp_id in self._mapping.preset_mode_dp_ids.items():
                value = (preset == preset_mode)
                datapoint = self._device.datapoints.get_or_create(
                    dp_id, TuyaBLEDataPointType.DT_BOOL, value
                )
                if datapoint:
                    self._hass.create_task(datapoint.set_value(value))

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLEClimate] = []
    for mapping in mappings:
        entities.append(
            TuyaBLEClimate(
                hass,
                data.coordinator,
                data.device,
                data.product,
                mapping,
            )
        )
    async_add_entities(entities)
