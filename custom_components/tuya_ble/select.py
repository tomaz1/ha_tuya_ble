"""The Tuya BLE integration."""
from __future__ import annotations

from dataclasses import dataclass, field

import logging

from homeassistant.components.select import (
    SelectEntityDescription,
    SelectEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    FINGERBOT_MODE_PROGRAM,
    FINGERBOT_MODE_PUSH,
    FINGERBOT_MODE_SWITCH,
    LED_BRIGHTNESS_HIGH,
    LED_BRIGHTNESS_MID,
    LED_BRIGHTNESS_LOW,
    LED_BRIGHTNESS_ALL,    
    SCREEN_ORIENTATION_UP,
    SCREEN_ORIENTATION_DOWN,
    SCREEN_ORIENTATION_ALL,
    SCREEN_ORIENTATION_VALUE_MAP,
)
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)


@dataclass
class TuyaBLESelectMapping:
    dp_id: int
    description: SelectEntityDescription
    force_add: bool = True
    dp_type: TuyaBLEDataPointType | None = None
    value_map: dict[str, int] | None = None  # za LCD orientacijo, ker delujeta samo vrednosti 0 in 2

@dataclass
class TemperatureUnitDescription(SelectEntityDescription):
    key: str = "temperature_unit"
    icon: str = "mdi:thermometer"
    entity_category: EntityCategory = EntityCategory.CONFIG


@dataclass
class TuyaBLEFingerbotModeMapping(TuyaBLESelectMapping):
    description: SelectEntityDescription = field(
        default_factory=lambda: SelectEntityDescription(
            key="fingerbot_mode",
            entity_category=EntityCategory.CONFIG,
            options=
                [
                    FINGERBOT_MODE_PUSH, 
                    FINGERBOT_MODE_SWITCH,
                    FINGERBOT_MODE_PROGRAM,
                ],
        )
    )


@dataclass
class TuyaBLECategorySelectMapping:
    products: dict[str, list[TuyaBLESelectMapping]] | None = None
    mapping: list[TuyaBLESelectMapping] | None = None


mapping: dict[str, TuyaBLECategorySelectMapping] = {
    "co2bj": TuyaBLECategorySelectMapping(
        products={
            "59s19z5m":  # CO2 Detector
            [
                TuyaBLESelectMapping(
                    dp_id=101,
                    description=TemperatureUnitDescription(
                        options=[
                            UnitOfTemperature.CELSIUS,
                            UnitOfTemperature.FAHRENHEIT,
                        ],
                    )
                ),
            ],
        },
    ),
    "ms": TuyaBLECategorySelectMapping(
        products={
            **dict.fromkeys(
                ["ludzroix", "isk2p555"], # Smart Lock
                [
                    TuyaBLESelectMapping(
                        dp_id=31,
                        description=SelectEntityDescription(
                            key="beep_volume",
                            options=[
                                "mute",
                                "low",
                                "normal",
                                "high",
                            ],
                            entity_category=EntityCategory.CONFIG,
                        ),
                    ),
                ]
            ),
        }
    ),
    "szjqr": TuyaBLECategorySelectMapping(
        products={
            **dict.fromkeys(
                ["3yqdo5yt", "xhf790if"],  # CubeTouch 1s and II
                [
                    TuyaBLEFingerbotModeMapping(dp_id=2),
                ],
            ),
            **dict.fromkeys(
                [
                    "blliqpsj",
                    "ndvkgsrm",
                    "yiihr7zh", 
                    "neq16kgd"
                ],  # Fingerbot Plus
                [
                    TuyaBLEFingerbotModeMapping(dp_id=8),
                ],
            ),
            **dict.fromkeys(
                ["ltak7e1p", "y6kttvd6", "yrnk7mnn",
                    "nvr2rocq", "bnt7wajf", "rvdceqjh",
                    "5xhbk964"],  # Fingerbot
                [
                    TuyaBLEFingerbotModeMapping(dp_id=8),
                ],
            ),
        },
    ),
    "wsdcg": TuyaBLECategorySelectMapping(
        products={
            "ojzlzzsw":  # Soil moisture sensor
            [
                TuyaBLESelectMapping(
                    dp_id=9,
                    description=TemperatureUnitDescription(
                        options=[
                            UnitOfTemperature.CELSIUS,
                            UnitOfTemperature.FAHRENHEIT,
                        ],
                        entity_registry_enabled_default=False,
                    )
                ),
            ],
        },
    ),
    "znhsb": TuyaBLECategorySelectMapping(
        products={
            "cdlandip":  # Smart water bottle
            [
                TuyaBLESelectMapping(
                    dp_id=106,
                    description=TemperatureUnitDescription(
                        options=[
                            UnitOfTemperature.CELSIUS,
                            UnitOfTemperature.FAHRENHEIT,
                        ],
                    )
                ),
                TuyaBLESelectMapping(
                    dp_id=107,
                    description=SelectEntityDescription(
                        key="reminder_mode",
                        options=[
                            "interval_reminder",
                            "schedule_reminder",
                        ],
                        entity_category=EntityCategory.CONFIG,
                    ),
                ),
            ],
        },
    ),
    "znhsb": TuyaBLECategorySelectMapping(
        products={
            "cdlandip":  # Smart water bottle
            [
                TuyaBLESelectMapping(
                    dp_id=106,
                    description=TemperatureUnitDescription(
                        options=[
                            UnitOfTemperature.CELSIUS,
                            UnitOfTemperature.FAHRENHEIT,
                        ],
                    )
                ),
                TuyaBLESelectMapping(
                    dp_id=107,
                    description=SelectEntityDescription(
                        key="reminder_mode",
                        options=[
                            "interval_reminder",
                            "alarm_reminder",
                        ],
                        entity_category=EntityCategory.CONFIG,
                    ),
                ),
            ],
        },
    ),
    "wkf": TuyaBLECategorySelectMapping(
        products={
            "llflaywg": 
            [  # Thermostatic Radiator Valve
                TuyaBLESelectMapping(
                dp_id=111,
                description=SelectEntityDescription(
                    key="led_brightness",
                    name="LED Brightness",
                    icon="mdi:brightness-6",
                    entity_category=EntityCategory.CONFIG,
                    options=LED_BRIGHTNESS_ALL,
                    ),
                ),
                TuyaBLESelectMapping(
                    dp_id=113,
                    description=SelectEntityDescription(
                        key="screen_orientation",
                        name="Screen orientation",
                        icon="mdi:axis-z-rotate-clockwise",  # ali drug primeren mdi
                        entity_category=EntityCategory.CONFIG,
                        options=[SCREEN_ORIENTATION_UP, SCREEN_ORIENTATION_DOWN],
                    ),
                    value_map=SCREEN_ORIENTATION_VALUE_MAP, # Potrebno za pravilno preslikavo vrednosti, ker je na voljo samo 0 in 2
                ),
            ],
        }
    ),

}


def get_mapping_by_device(
    device: TuyaBLEDevice
) -> list[TuyaBLECategorySelectMapping]:
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


class TuyaBLESelect(TuyaBLEEntity, SelectEntity):
    """Representation of a Tuya BLE select."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: DataUpdateCoordinator,
        device: TuyaBLEDevice,
        product: TuyaBLEProductInfo,
        mapping: TuyaBLESelectMapping,
    ) -> None:
        super().__init__(
            hass,
            coordinator,
            device,
            product,
            mapping.description
        )
        self._mapping = mapping
        self._attr_options = mapping.description.options

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        datapoint = self._device.datapoints[self._mapping.dp_id]
        if not datapoint or datapoint.value is None:
            return None

        # Če je podan value_map, obratno preslikaj vrednost
        if self._mapping.value_map:
            for k, v in self._mapping.value_map.items():
                if v == datapoint.value:
                    return k
            return str(datapoint.value)  # fallback
        else:
            # Privzet način z options seznamom
            if 0 <= datapoint.value < len(self._attr_options):
                return self._attr_options[datapoint.value]
            return str(datapoint.value)

    def select_option(self, value: str) -> None:
        """Change the selected option."""
        # Če imamo value_map jo uporabimo
        if self._mapping.value_map:
            if value not in self._mapping.value_map:
                raise ValueError(f"Unsupported option: {value}")
            int_value = self._mapping.value_map[value]
        else:
            if value not in self._attr_options:
                raise ValueError(f"Unsupported option: {value}")
            int_value = self._attr_options.index(value)

        datapoint = self._device.datapoints.get_or_create(
            self._mapping.dp_id,
            TuyaBLEDataPointType.DT_ENUM,
            int_value,
        )
        if datapoint:
            self._hass.create_task(datapoint.set_value(int_value))

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLESelect] = []
    for mapping in mappings:
        if (
            mapping.force_add or
            data.device.datapoints.has_id(mapping.dp_id, mapping.dp_type)
        ):
            entities.append(TuyaBLESelect(
                hass,
                data.coordinator,
                data.device,
                data.product,
                mapping,
            ))
    async_add_entities(entities)
