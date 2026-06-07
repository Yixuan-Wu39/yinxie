"""WAV adapter for LSB audio steganography."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from . import stego_core


class WavError(ValueError):
    """Raised when the uploaded file is not a supported WAV file."""


@dataclass(frozen=True)
class WavInfo:
    channels: int
    sample_rate: int
    bits_per_sample: int
    byte_rate: int
    block_align: int
    data_offset: int
    data_byte_count: int
    sample_slot_count: int
    duration_seconds: float
    capacity_bytes: int
    max_text_bytes: int

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def inspect_wav(audio: bytes | bytearray) -> WavInfo:
    if len(audio) < 44:
        raise WavError("文件太小，不是有效的 WAV 音频")
    if audio[0:4] != b"RIFF" or audio[8:12] != b"WAVE":
        raise WavError("WAV 模式只支持 WAV 音频")

    fmt = None
    data_offset = None
    data_size = None
    cursor = 12
    while cursor + 8 <= len(audio):
        chunk_id = bytes(audio[cursor : cursor + 4])
        chunk_size = _u32(audio, cursor + 4)
        chunk_start = cursor + 8
        chunk_end = chunk_start + chunk_size
        if chunk_end > len(audio):
            raise WavError("WAV 数据块不完整")

        if chunk_id == b"fmt ":
            if chunk_size < 16:
                raise WavError("WAV 格式信息块太小")
            fmt = {
                "audio_format": _u16(audio, chunk_start),
                "channels": _u16(audio, chunk_start + 2),
                "sample_rate": _u32(audio, chunk_start + 4),
                "byte_rate": _u32(audio, chunk_start + 8),
                "block_align": _u16(audio, chunk_start + 12),
                "bits_per_sample": _u16(audio, chunk_start + 14),
            }
        elif chunk_id == b"data":
            data_offset = chunk_start
            data_size = chunk_size

        cursor = chunk_end + (chunk_size % 2)

    if fmt is None:
        raise WavError("没有找到 WAV 格式信息块")
    if data_offset is None or data_size is None:
        raise WavError("没有找到 WAV 音频数据块")
    if fmt["audio_format"] != 1:
        raise WavError("当前只支持未压缩 PCM WAV 音频")
    if fmt["bits_per_sample"] not in {8, 16, 24, 32}:
        raise WavError("当前只支持 8、16、24 或 32 位 PCM WAV")

    bytes_per_sample = fmt["bits_per_sample"] // 8
    expected_block_align = fmt["channels"] * bytes_per_sample
    if fmt["block_align"] != expected_block_align:
        raise WavError("不支持这种 WAV 块对齐方式")
    if data_size % bytes_per_sample != 0:
        raise WavError("WAV 采样数据没有正确对齐")

    sample_slot_count = data_size // bytes_per_sample
    duration = data_size / fmt["byte_rate"] if fmt["byte_rate"] else 0
    return WavInfo(
        channels=fmt["channels"],
        sample_rate=fmt["sample_rate"],
        bits_per_sample=fmt["bits_per_sample"],
        byte_rate=fmt["byte_rate"],
        block_align=fmt["block_align"],
        data_offset=data_offset,
        data_byte_count=data_size,
        sample_slot_count=sample_slot_count,
        duration_seconds=round(duration, 3),
        capacity_bytes=stego_core.region_capacity_bytes(sample_slot_count),
        max_text_bytes=stego_core.max_text_bytes(sample_slot_count),
    )


def hide_text(audio: bytes, text: bytes) -> tuple[bytes, WavInfo]:
    info = inspect_wav(audio)
    modified = bytearray(audio)
    slots = _sample_low_byte_slots(info)
    _embed_with_slots(modified, slots, text)
    return bytes(modified), info


def extract_text(audio: bytes) -> tuple[bytes, WavInfo]:
    info = inspect_wav(audio)
    slots = _sample_low_byte_slots(info)
    return _extract_with_slots(audio, slots, info.sample_slot_count), info


def _sample_low_byte_slots(info: WavInfo) -> range:
    bytes_per_sample = info.bits_per_sample // 8
    start = info.data_offset
    stop = info.data_offset + info.data_byte_count
    return range(start, stop, bytes_per_sample)


def _embed_with_slots(audio: bytearray, slots: range, text: bytes) -> None:
    limit = stego_core.max_text_bytes(len(slots))
    if len(text) > limit:
        raise WavError(f"文本过长：当前 {len(text)} 字节，上限 {limit} 字节")

    payload = stego_core.MAGIC + len(text).to_bytes(8, "little") + text
    required = stego_core.slots_required(len(payload))
    if required > len(slots):
        raise WavError("音频采样数量不足，无法隐藏这段文本")

    slot_index = 0
    for value in payload:
        for shift in range(0, 8, stego_core.BITS_PER_SLOT):
            part = (value >> shift) & stego_core.LOW_BITS_MASK
            cursor = slots[slot_index]
            audio[cursor] = (audio[cursor] & stego_core.CLEAR_LOW_BITS_MASK) | part
            slot_index += 1


def _extract_with_slots(audio: bytes | bytearray, slots: range, slot_count: int) -> bytes:
    if slot_count < stego_core.slots_required(stego_core.HEADER_SIZE):
        raise WavError("音频太短，不可能包含隐藏文本")

    slot_index = 0
    magic = bytearray()
    for _ in range(len(stego_core.MAGIC)):
        value, slot_index = _read_byte_from_slots(audio, slots, slot_index)
        magic.append(value)
    if bytes(magic) != stego_core.MAGIC:
        raise WavError("没有找到隐藏文本标记")

    length_bytes = bytearray()
    for _ in range(8):
        value, slot_index = _read_byte_from_slots(audio, slots, slot_index)
        length_bytes.append(value)
    text_length = int.from_bytes(length_bytes, "little")

    limit = stego_core.max_text_bytes(slot_count)
    if text_length > limit:
        raise WavError("隐藏文本长度异常，音频可能已损坏或被重新编码")

    text = bytearray()
    for _ in range(text_length):
        value, slot_index = _read_byte_from_slots(audio, slots, slot_index)
        text.append(value)
    return bytes(text)


def _read_byte_from_slots(
    audio: bytes | bytearray,
    slots: range,
    slot_index: int,
) -> tuple[int, int]:
    value = 0
    for shift in range(0, 8, stego_core.BITS_PER_SLOT):
        value |= (audio[slots[slot_index]] & stego_core.LOW_BITS_MASK) << shift
        slot_index += 1
    return value, slot_index


def _u16(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little", signed=False)


def _u32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little", signed=False)
