from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.switch import SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_DEFAULT_POWER,
    CONF_MAX_POWER,
    CONF_POLL_INTERVAL,
    DEFAULT_POWER,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch", "sensor"]
DEFAULT_RESET_DELAY = 2


class SmartPlugHub:
    def __init__(self, config: dict) -> None:
        self.config = config
        self.is_on = False
        self.power = 0.0
        self.energy = 0.0
        self.voltage = config.get("voltage", 220.0)
        self.current = 0.0
        self.default_power = config.get(CONF_DEFAULT_POWER, DEFAULT_POWER)
        self.max_power = config.get(CONF_MAX_POWER, 0.0)
        self.poll_interval = config.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        self.last_update = datetime.now()
        self.on_time = timedelta()
        self._energy_update_unsub = None

    def turn_on(self) -> None:
        if not self.is_on:
            self.is_on = True
            self.power = self.default_power
            self.current = self.power / self.voltage if self.voltage > 0 else 0.0
            self.last_update = datetime.now()

    def turn_off(self) -> None:
        if self.is_on:
            self._accumulate_energy()
            self.is_on = False
            self.power = 0.0
            self.current = 0.0

    def _accumulate_energy(self) -> None:
        now = datetime.now()
        duration = now - self.last_update
        hours = duration.total_seconds() / 3600.0
        energy_kwh = (self.power / 1000.0) * hours
        self.energy += energy_kwh
        self.last_update = now

    def update_energy(self) -> None:
        if self.is_on:
            self._accumulate_energy()

    def get_state(self) -> dict[str, Any]:
        return {
            "is_on": self.is_on,
            "power": self.power,
            "energy": round(self.energy, 4),
            "voltage": self.voltage,
            "current": round(self.current, 4),
            "default_power": self.default_power,
            "max_power": self.max_power,
        }


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def handle_reset(call: ServiceCall) -> None:
        _LOGGER.info("Handling reset service call: %s", call.data)
        entity_ids = call.data.get(ATTR_ENTITY_ID, [])
        delay = call.data.get("delay", DEFAULT_RESET_DELAY)

        if not entity_ids:
            _LOGGER.warning("No entities specified for reset service")
            return

        await hass.services.async_call(
            "switch", SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_ids}, blocking=True
        )
        await asyncio.sleep(delay)
        await hass.services.async_call(
            "switch", SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_ids}, blocking=True
        )

    hass.services.async_register(DOMAIN, "reset", handle_reset)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Setting up smart plug: %s", entry.title)
    hub = SmartPlugHub(entry.data)
    hass.data[DOMAIN][entry.entry_id] = hub
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _update_energy(now: datetime) -> None:
        hub.update_energy()
        _LOGGER.debug("Energy updated for %s: %.4f kWh", entry.title, hub.energy)

    hub._energy_update_unsub = async_track_time_interval(
        hass, _update_energy, timedelta(seconds=hub.poll_interval)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub = hass.data[DOMAIN][entry.entry_id]
    if hub._energy_update_unsub:
        hub._energy_update_unsub()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
