"""Diagnostics support for AC Infinity Controller 67."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import ACInfinity67Client
from .const import CONF_ADDRESS, DOMAIN

TO_REDACT = {CONF_ADDRESS, "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    client: ACInfinity67Client | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "client": client.diagnostics() if client else None,
    }
