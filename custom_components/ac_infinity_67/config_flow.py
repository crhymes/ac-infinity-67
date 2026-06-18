"""Config flow for AC Infinity Controller 67."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_ADDRESS, CONF_NAME, DEFAULT_NAME, DOMAIN


class ACInfinity67ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for AC Infinity Controller 67."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a controller manually."""
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={CONF_ADDRESS: address, CONF_NAME: user_input[CONF_NAME]},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle Bluetooth discovery."""
        address = discovery_info.address.upper()
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()
        name = discovery_info.name or discovery_info.advertisement.local_name or DEFAULT_NAME
        self.context["title_placeholders"] = {"name": name}
        return self.async_create_entry(
            title=name,
            data={CONF_ADDRESS: address, CONF_NAME: name},
        )
