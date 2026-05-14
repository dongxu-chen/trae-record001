from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_CURRENT,
    ATTR_ENERGY,
    ATTR_POWER,
    ATTR_VOLTAGE,
    DOMAIN,
    ICON_POWER,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    hub = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([SmartPlugSwitch(hub, config_entry)])


class SmartPlugSwitch(SwitchEntity):
    _attr_icon = ICON_POWER

    def __init__(self, hub, config_entry: ConfigEntry) -> None:
        self._hub = hub
        self._config_entry = config_entry
        self._attr_name = config_entry.data.get("name", "Smart Plug")
        self._attr_unique_id = f"{config_entry.entry_id}_switch"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=self._attr_name,
            manufacturer="Smart Plug",
            model="Smart Plug with Energy Monitoring",
            sw_version="1.1",
        )

    @property
    def is_on(self) -> bool:
        return self._hub.is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self._hub.get_state()
        return {
            ATTR_POWER: state["power"],
            ATTR_ENERGY: state["energy"],
            ATTR_VOLTAGE: state["voltage"],
            ATTR_CURRENT: state["current"],
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        _LOGGER.info("Turning on smart plug: %s", self._attr_name)
        self._hub.turn_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        _LOGGER.info("Turning off smart plug: %s", self._attr_name)
        self._hub.turn_off()
        self.async_write_ha_state()
