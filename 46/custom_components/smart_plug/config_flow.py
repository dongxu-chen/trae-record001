from __future__ import annotations

import asyncio
import ipaddress
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import (
    CONF_DEFAULT_POWER,
    CONF_MAX_POWER,
    CONF_POLL_INTERVAL,
    CONF_VOLTAGE,
    DEFAULT_POWER,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_VOLTAGE,
    DOMAIN,
)

DEFAULT_TIMEOUT = 5
ERROR_CONNECTION_FAILED = "connection_failed"
ERROR_INVALID_IP = "invalid_ip"
ERROR_TIMEOUT = "timeout"
ERROR_INVALID_POWER = "invalid_power"
ERROR_INVALID_VOLTAGE = "invalid_voltage"


class SmartPlugConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._errors = {}
        self._user_data = {}

    async def _validate_ip(self, ip_address: str) -> bool:
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False

    async def _validate_power(self, power: float) -> bool:
        return power > 0 and power <= 10000

    async def _validate_voltage(self, voltage: float) -> bool:
        return voltage > 0 and voltage <= 400

    async def _test_connection(self, ip_address: str) -> bool:
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with session.get(f"http://{ip_address}", timeout=DEFAULT_TIMEOUT):
                    return True
        except asyncio.TimeoutError:
            self._errors["base"] = ERROR_TIMEOUT
            return False
        except Exception:
            return True

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        self._errors = {}

        if user_input is not None:
            if not await self._validate_ip(user_input["ip_address"]):
                self._errors["ip_address"] = ERROR_INVALID_IP
            else:
                await self.async_set_unique_id(user_input["name"])
                self._abort_if_unique_id_configured()
                self._user_data = user_input
                return await self.async_step_advanced()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default="Smart Plug"): str,
                    vol.Required("ip_address"): str,
                }
            ),
            errors=self._errors,
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        self._errors = {}

        if user_input is not None:
            if not await self._validate_power(user_input.get(CONF_DEFAULT_POWER, DEFAULT_POWER)):
                self._errors[CONF_DEFAULT_POWER] = ERROR_INVALID_POWER
            elif not await self._validate_voltage(user_input.get(CONF_VOLTAGE, DEFAULT_VOLTAGE)):
                self._errors[CONF_VOLTAGE] = ERROR_INVALID_VOLTAGE
            else:
                data = {**self._user_data, **user_input}
                return self.async_create_entry(title=data["name"], data=data)

        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_DEFAULT_POWER, default=DEFAULT_POWER): vol.All(
                        vol.Coerce(float), vol.Clamp(min=1, max=10000)
                    ),
                    vol.Optional(CONF_VOLTAGE, default=DEFAULT_VOLTAGE): vol.All(
                        vol.Coerce(float), vol.Clamp(min=1, max=400)
                    ),
                    vol.Optional(CONF_MAX_POWER, default=0): vol.All(
                        vol.Coerce(float), vol.Clamp(min=0, max=10000)
                    ),
                    vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
                        vol.Coerce(int), vol.Clamp(min=10, max=3600)
                    ),
                }
            ),
            errors=self._errors,
        )
