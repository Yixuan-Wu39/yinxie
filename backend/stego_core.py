"""Format-agnostic LSB steganography helpers.

This module deliberately knows nothing about BMP, PNG, or JPG. It only writes
and reads bytes from a mutable byte region using the lowest two bits of each
slot. Image-specific adapters decide which byte region is safe to modify.
"""

from __future__ import annotations


BITS_PER_SLOT = 2
SLOTS_PER_BYTE = 8 // BITS_PER_SLOT
LOW_BITS_MASK = 0x03
CLEAR_LOW_BITS_MASK = 0xFC
MAGIC = b"LSB2BMP1"
HEADER_SIZE = len(MAGIC) + 8


class StegoError(ValueError):
    """Raised when text cannot be embedded or extracted safely."""


def region_capacity_bytes(slot_count: int) -> int:
    """Return raw payload capacity in bytes for a region with slot_count bytes."""
    if slot_count <= 0:
        return 0
    return slot_count * BITS_PER_SLOT // 8


def max_text_bytes(slot_count: int) -> int:
    """Return maximum user text bytes after reserving magic and length fields."""
    return max(0, region_capacity_bytes(slot_count) - HEADER_SIZE)


def slots_required(byte_count: int) -> int:
    return byte_count * SLOTS_PER_BYTE


def embed_text(region: bytearray, start: int, end: int, text: bytes) -> None:
    """Embed UTF-8 or arbitrary text bytes into region[start:end]."""
    _validate_bounds(region, start, end)
    slot_count = end - start
    limit = max_text_bytes(slot_count)
    if len(text) > limit:
        raise StegoError(f"text too long: {len(text)} bytes, max {limit} bytes")

    payload = MAGIC + len(text).to_bytes(8, "little") + text
    required = slots_required(len(payload))
    if required > slot_count:
        raise StegoError("image region is too small for payload")

    cursor = start
    for value in payload:
        cursor = _write_byte(region, cursor, value)


def extract_text(region: bytes | bytearray, start: int, end: int) -> bytes:
    """Extract embedded text bytes from region[start:end]."""
    _validate_bounds(region, start, end)
    slot_count = end - start
    if slot_count < slots_required(HEADER_SIZE):
        raise StegoError("image is too small to contain hidden text")

    cursor = start
    magic = bytearray()
    for _ in range(len(MAGIC)):
        value, cursor = _read_byte(region, cursor)
        magic.append(value)
    if bytes(magic) != MAGIC:
        raise StegoError("no hidden text marker found")

    length_bytes = bytearray()
    for _ in range(8):
        value, cursor = _read_byte(region, cursor)
        length_bytes.append(value)
    text_length = int.from_bytes(length_bytes, "little")

    limit = max_text_bytes(slot_count)
    if text_length > limit:
        raise StegoError("hidden text length is invalid or corrupted")

    text = bytearray()
    for _ in range(text_length):
        value, cursor = _read_byte(region, cursor)
        text.append(value)
    return bytes(text)


def _write_byte(region: bytearray, cursor: int, value: int) -> int:
    for shift in range(0, 8, BITS_PER_SLOT):
        part = (value >> shift) & LOW_BITS_MASK
        region[cursor] = (region[cursor] & CLEAR_LOW_BITS_MASK) | part
        cursor += 1
    return cursor


def _read_byte(region: bytes | bytearray, cursor: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 8, BITS_PER_SLOT):
        value |= (region[cursor] & LOW_BITS_MASK) << shift
        cursor += 1
    return value, cursor


def _validate_bounds(region: bytes | bytearray, start: int, end: int) -> None:
    if start < 0 or end < start or end > len(region):
        raise StegoError("invalid steganography region")
