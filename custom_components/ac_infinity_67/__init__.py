"""AC Infinity Controller 67 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .client import ACInfinity67Client
from .const import CONF_ADDRESS, DOMAIN

PLATFORMS = [Platform.FAN]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AC Infinity Controller 67 from a config entry."""
    client = ACInfinity67Client(hass, entry.data[CONF_ADDRESS])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an AC Infinity Controller 67 config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    client: ACInfinity67Client | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if client:
        await client.disconnect()
    return unload_ok
