"""Protocol helpers for the AC Infinity Controller 67 BLE integration."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


CONTROL_CHARACTERISTIC_UUID = "70d51001-2c7f-4e75-ae8a-d758951ce4e0"
NOTIFY_CHARACTERISTIC_UUID = "70d51002-2c7f-4e75-ae8a-d758951ce4e0"

MIN_SPEED = 0
MAX_SPEED = 10
SPEED_RANGE = range(MIN_SPEED, MAX_SPEED + 1)
SPEED_REPLAY_PREFIX = bytes.fromhex("a5 00 00 03 00 11 f7 79")


@dataclass(frozen=True)
class Telemetry:
    """Parsed recurring telemetry notification."""

    temperature_c: float | None
    raw_temperature: int | None
    speed: int | None
    raw_speed_byte: int | None


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def speed_to_percentage(speed: int) -> int:
    validate_speed(speed)
    return speed * 10


def temperature_to_tenth(temperature_c: float) -> float:
    """Round a Celsius value to the nearest tenth, with halves rounded up."""
    return float(Decimal(str(temperature_c)).quantize(Decimal("0.1"), ROUND_HALF_UP))


def percentage_to_speed(percentage: int | float | None) -> int:
    if percentage is None or percentage <= 0:
        return 0
    if percentage >= 100:
        return MAX_SPEED
    return max(MIN_SPEED, min(MAX_SPEED, round(float(percentage) / 10)))


def validate_speed(speed: int) -> None:
    if speed not in SPEED_RANGE:
        raise ValueError(f"Speed must be between {MIN_SPEED} and {MAX_SPEED}, got {speed}.")


def speed_frame(speed: int) -> bytes:
    validate_speed(speed)
    command_and_payload = bytes([0x00, 0x03, 0x12, 0x01, speed])
    crc = crc16_ccitt_false(command_and_payload)
    return SPEED_REPLAY_PREFIX + command_and_payload + crc.to_bytes(2, "big")


def parse_telemetry(data: bytes | bytearray) -> Telemetry | None:
    value = bytes(data)
    if len(value) != 18 or value[:8] != b"\x1e\xff\x02\x09\x03\x0c\x00\x00":
        return None

    raw_temperature = int.from_bytes(value[8:10], "big")
    temperature_c = None if raw_temperature == 0x8000 else raw_temperature / 100
    raw_speed = value[-1]
    high_nibble = raw_speed >> 4
    low_nibble = raw_speed & 0x0F
    speed = high_nibble if low_nibble == 0x02 and high_nibble in SPEED_RANGE else None
    return Telemetry(
        temperature_c=temperature_c,
        raw_temperature=raw_temperature,
        speed=speed,
        raw_speed_byte=raw_speed,
    )
