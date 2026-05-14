from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ELECTRIC_CURRENT_AMPERE,
    ELECTRIC_POTENTIAL_VOLT,
    ENERGY_KILO_WATT_HOUR,
    POWER_WATT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ICON_CURRENT,
    ICON_ENERGY,
    ICON_POWER,
    ICON_VOLTAGE,
)

_LOGGER = logging.getLogger(__name__)


SENSOR_TYPES = [
    {
        "key": "power",
        "name": "Power",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": POWER_WATT,
        "icon": ICON_POWER,
    },
    {
        "key": "energy",
        "name": "Energy",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": ENERGY_KILO_WATT_HOUR,
        "icon": ICON_ENERGY,
    },
    {
        "key": "voltage",
        "name": "Voltage",
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": ELECTRIC_POTENTIAL_VOLT,
        "icon": ICON_VOLTAGE,
    },
    {
        "key": "current",
        "name": "Current",
        "device_class": SensorDeviceClass.CURRENT,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": ELECTRIC_CURRENT_AMPERE,
        "icon": ICON_CURRENT,
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][config_entry.entry_id]
    entities = [
        SmartPlugSensor(hub, config_entry, sensor_type)
        for sensor_type in SENSOR_TYPES
    ]
    async_add_entities(entities)


class SmartPlugSensor(SensorEntity):
    def __init__(self, hub, config_entry: ConfigEntry, sensor_type: dict) -> None:
        self._hub = hub
        self._config_entry = config_entry
        self._sensor_type = sensor_type
        self._key = sensor_type["key"]
        self._attr_name = f"{config_entry.data.get('name', 'Smart Plug')} {sensor_type['name']}"
        self._attr_unique_id = f"{config_entry.entry_id}_{self._key}"
        self._attr_device_class = sensor_type["device_class"]
        self._attr_state_class = sensor_type["state_class"]
        self._attr_native_unit_of_measurement = sensor_type["unit"]
        self._attr_icon = sensor_type["icon"]
        self._attr_entity_registry_enabled_default = True

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=self._config_entry.data.get("name", "Smart Plug"),
            manufacturer="Smart Plug",
            model="Smart Plug with Energy Monitoring",
            sw_version="1.1",
        )

    @property
    def native_value(self) -> float:
        state = self._hub.get_state()
        return state.get(self._key, 0)

    @property
    def available(self) -> bool:
        return True
