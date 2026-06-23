"""Sensor platform for AC Infinity Controller 67."""

from __future__ import annotations

import datetime as dt
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .client import ACInfinity67Client
from .const import CONF_ADDRESS, CONF_NAME, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)
RETRY_INTERVAL = dt.timedelta(seconds=60)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up temperature sensor."""
    client: ACInfinity67Client = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ACInfinity67TemperatureSensor(entry, client)])


class ACInfinity67TemperatureSensor(SensorEntity):
    """Temperature reported by the Controller 67 probe."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, entry: ConfigEntry, client: ACInfinity67Client) -> None:
        self._client = client
        self._remove_callback = None
        self._remove_retry = None
        self._logged_initial_failure = False
        name = entry.data.get(CONF_NAME, DEFAULT_NAME)
        self._attr_name = f"{name} Temperature"
        self._attr_unique_id = f"{entry.data[CONF_ADDRESS]}-temperature"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data[CONF_ADDRESS])},
            "manufacturer": "AC Infinity",
            "model": "Controller 67 BLE",
            "name": name,
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
    def native_value(self) -> float | None:
        return self._client.temperature_c
