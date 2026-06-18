"""Fan platform for AC Infinity Controller 67."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .client import ACInfinity67Client
from .const import CONF_ADDRESS, CONF_NAME, DEFAULT_NAME, DOMAIN
from .protocol import percentage_to_speed, speed_to_percentage

_LOGGER = logging.getLogger(__name__)
RETRY_INTERVAL = dt.timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up fan entity."""
    client: ACInfinity67Client = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ACInfinity67Fan(entry, client)])


class ACInfinity67Fan(FanEntity):
    """AC Infinity Controller 67 fan entity."""

    _attr_supported_features = FanEntityFeature.SET_SPEED
    _attr_percentage_step = 10

    def __init__(self, entry: ConfigEntry, client: ACInfinity67Client) -> None:
        self._entry = entry
        self._client = client
        self._remove_callback = None
        self._remove_retry = None
        self._logged_initial_failure = False
        self._attr_name = entry.data.get(CONF_NAME, DEFAULT_NAME)
        self._attr_unique_id = entry.data[CONF_ADDRESS]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data[CONF_ADDRESS])},
            "manufacturer": "AC Infinity",
            "model": "Controller 67 BLE",
            "name": self._attr_name,
        }

    async def async_added_to_hass(self) -> None:
        """Connect when entity is added."""
        self._remove_callback = self._client.add_callback(self.async_write_ha_state)
        self._remove_retry = async_track_time_interval(
            self.hass, self._async_retry_connect, RETRY_INTERVAL
        )
        await self._async_retry_connect()

    async def _async_retry_connect(self, _now: dt.datetime | None = None) -> None:
        """Retry connecting until Home Assistant sees the BLE device."""
        if self._client.available:
            return
        try:
            await self._client.connect()
        except Exception as exc:
            if self._logged_initial_failure:
                _LOGGER.debug("AC Infinity BLE reconnect retry failed: %s", exc)
            else:
                _LOGGER.warning("Initial AC Infinity BLE connection failed: %s", exc)
                self._logged_initial_failure = True
            self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect callbacks when removed."""
        if self._remove_retry:
            self._remove_retry()
            self._remove_retry = None
        if self._remove_callback:
            self._remove_callback()
            self._remove_callback = None

    @property
    def available(self) -> bool:
        return self._client.available

    @property
    def is_on(self) -> bool | None:
        if self._client.speed is None:
            return None
        return self._client.speed > 0

    @property
    def percentage(self) -> int | None:
        if self._client.speed is None:
            return None
        return speed_to_percentage(self._client.speed)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "speed": self._client.speed,
            "raw_speed_byte": self._client.raw_speed_byte,
            "protocol": "experimental_replay_prefix",
        }

    async def async_set_percentage(self, percentage: int) -> None:
        speed = percentage_to_speed(percentage)
        await self._client.set_speed(speed)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        speed = percentage_to_speed(percentage) if percentage is not None else 1
        await self._client.set_speed(speed)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.set_speed(0)
