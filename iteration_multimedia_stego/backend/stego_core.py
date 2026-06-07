"""Format-agnostic LSB steganography helpers for image bytes."""

from __future__ import annotations


BITS_PER_SLOT = 2
SLOTS_PER_BYTE = 8 // BITS_PER_SLOT
LOW_BITS_MASK = 0x03
CLEAR_LOW_BITS_MASK = 0xFC
MAGIC = b"LSB2IMG1"
HEADER_SIZE = len(MAGIC) + 8


class StegoError(ValueError):
    """Raised when text cannot be embedded or extracted safely."""


def region_capacity_bytes(slot_count: int) -> int:
    if slot_count <= 0:
        return 0
    return slot_count * BITS_PER_SLOT // 8


def max_text_bytes(slot_count: int) -> int:
    return max(0, region_capacity_bytes(slot_count) - HEADER_SIZE)


def slots_required(byte_count: int) -> int:
    return byte_count * SLOTS_PER_BYTE


def embed_text(region: bytearray, text: bytes) -> None:
    """Embed text bytes into a contiguous mutable byte region."""
    limit = max_text_bytes(len(region))
    if len(text) > limit:
        raise StegoError(f"文本过长：当前 {len(text)} 字节，上限 {limit} 字节")

    payload = MAGIC + len(text).to_bytes(8, "little") + text
    required = slots_required(len(payload))
    if required > len(region):
        raise StegoError("可写入的数据区域太小，无法隐藏这段文本")

    cursor = 0
    for value in payload:
        for shift in range(0, 8, BITS_PER_SLOT):
            part = (value >> shift) & LOW_BITS_MASK
            region[cursor] = (region[cursor] & CLEAR_LOW_BITS_MASK) | part
            cursor += 1


def extract_text(region: bytes | bytearray) -> bytes:
    """Extract hidden text from a contiguous byte region."""
    if len(region) < slots_required(HEADER_SIZE):
        raise StegoError("文件太小，不可能包含隐藏文本")

    cursor = 0
    magic = bytearray()
    for _ in range(len(MAGIC)):
        value, cursor = _read_byte(region, cursor)
        magic.append(value)
    if bytes(magic) != MAGIC:
        raise StegoError("没有找到隐藏文本标记")

    length_bytes = bytearray()
    for _ in range(8):
        value, cursor = _read_byte(region, cursor)
        length_bytes.append(value)
    text_length = int.from_bytes(length_bytes, "little")

    limit = max_text_bytes(len(region))
    if text_length > limit:
        raise StegoError("隐藏文本长度异常，文件可能已损坏或被重新压缩")

    text = bytearray()
    for _ in range(text_length):
        value, cursor = _read_byte(region, cursor)
        text.append(value)
    return bytes(text)


def _read_byte(region: bytes | bytearray, cursor: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 8, BITS_PER_SLOT):
        value |= (region[cursor] & LOW_BITS_MASK) << shift
        cursor += 1
    return value, cursor
