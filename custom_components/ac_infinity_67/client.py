"""BLE client for the AC Infinity Controller 67."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import datetime as dt
import logging

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

try:
    from bleak_retry_connector import establish_connection
except ImportError:  # pragma: no cover - depends on the Home Assistant runtime.
    establish_connection = None

from .protocol import (
    CONTROL_CHARACTERISTIC_UUID,
    NOTIFY_CHARACTERISTIC_UUID,
    Telemetry,
    parse_telemetry,
    speed_frame,
    temperature_to_tenth,
)

_LOGGER = logging.getLogger(__name__)

StateCallback = Callable[[], None]


class ACInfinity67Client:
    """Small async BLE wrapper around the controller."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        self.hass = hass
        self.address = address.upper()
        self.temperature_c: float | None = None
        self.raw_temperature: int | None = None
        self.speed: int | None = None
        self.raw_speed_byte: int | None = None
        self.available = False
        self.connection_attempts = 0
        self.last_connect_attempt: str | None = None
        self.last_connect_success: str | None = None
        self.last_error: str | None = None
        self.last_device_source: str | None = None
        self._client: BleakClient | None = None
        self._callbacks: set[StateCallback] = set()
        self._lock = asyncio.Lock()

    def add_callback(self, callback: StateCallback) -> Callable[[], None]:
        self._callbacks.add(callback)

        def remove_callback() -> None:
            self._callbacks.discard(callback)

        return remove_callback

    async def connect(self) -> None:
        async with self._lock:
            if self._client and self._client.is_connected:
                return

            self.connection_attempts += 1
            self.last_connect_attempt = self._now()
            self.last_error = None
            self.last_device_source = None

            device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if device is not None:
                self.last_device_source = "home_assistant_bluetooth"
            if device is None:
                _LOGGER.debug(
                    "Home Assistant Bluetooth cache has not seen %s; falling back to scan",
                    self.address,
                )
                device = await BleakScanner.find_device_by_address(
                    self.address, timeout=20
                )
                if device is not None:
                    self.last_device_source = "bleak_scanner"
            if device is None:
                self.available = False
                self.last_error = f"Could not find BLE device {self.address}"
                self._notify_state()
                raise RuntimeError(self.last_error)

            client = BleakClient(device, timeout=20)
            try:
                if establish_connection is not None:
                    client = await establish_connection(
                        BleakClient,
                        device,
                        self.address,
                        max_attempts=3,
                    )
                else:
                    await client.connect()
                await client.start_notify(
                    NOTIFY_CHARACTERISTIC_UUID, self._handle_notify
                )
                self._client = client
                self.available = True
                self.last_connect_success = self._now()
                self.last_error = None
                _LOGGER.info(
                    "Connected to AC Infinity Controller 67 %s via %s",
                    self.address,
                    self.last_device_source,
                )
                self._notify_state()
            except Exception as exc:
                self.available = False
                self.last_error = str(exc)
                self._notify_state()
                try:
                    await client.disconnect()
                except Exception:
                    pass
                raise

    async def disconnect(self) -> None:
        async with self._lock:
            client = self._client
            self._client = None
            if not client:
                return
            try:
                if client.is_connected:
                    await client.stop_notify(NOTIFY_CHARACTERISTIC_UUID)
                    await client.disconnect()
            finally:
                self.available = False
                self._notify_state()

    async def set_speed(self, speed: int) -> None:
        await self.connect()
        assert self._client is not None
        try:
            await self._client.write_gatt_char(
                CONTROL_CHARACTERISTIC_UUID, speed_frame(speed), response=True
            )
            self.speed = speed
            self.available = True
            self.last_error = None
            self._notify_state()
        except Exception as exc:
            self.available = False
            self.last_error = str(exc)
            self._notify_state()
            raise

    def diagnostics(self) -> dict[str, object]:
        """Return non-secret runtime state for Home Assistant diagnostics."""
        return {
            "available": self.available,
            "connection_attempts": self.connection_attempts,
            "last_connect_attempt": self.last_connect_attempt,
            "last_connect_success": self.last_connect_success,
            "last_device_source": self.last_device_source,
            "last_error": self.last_error,
            "temperature_c": self.temperature_c,
            "raw_temperature": self.raw_temperature,
            "speed": self.speed,
            "raw_speed_byte": self.raw_speed_byte,
        }

    def _handle_notify(
        self, _characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        telemetry = parse_telemetry(data)
        if telemetry is None:
            return
        self._apply_telemetry(telemetry)

    def _apply_telemetry(self, telemetry: Telemetry) -> None:
        state_changed = not self.available
        self.raw_temperature = telemetry.raw_temperature
        if telemetry.temperature_c is not None:
            temperature_c = temperature_to_tenth(telemetry.temperature_c)
            if temperature_c != self.temperature_c:
                self.temperature_c = temperature_c
                state_changed = True
        self.raw_speed_byte = telemetry.raw_speed_byte
        if telemetry.speed is not None and telemetry.speed != self.speed:
            self.speed = telemetry.speed
            state_changed = True
        self.available = True
        if state_changed:
            self._notify_state()

    def _notify_state(self) -> None:
        for callback in list(self._callbacks):
            try:
                callback()
            except Exception:  # pragma: no cover - defensive callback isolation.
                _LOGGER.exception("AC Infinity callback failed")

    @staticmethod
    def _now() -> str:
        return dt.datetime.now(dt.UTC).isoformat()
