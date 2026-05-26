"""BMP adapter for the format-agnostic LSB steganography core."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from . import stego_core


class BmpError(ValueError):
    """Raised when the uploaded file is not a supported BMP image."""


@dataclass(frozen=True)
class BmpInfo:
    width: int
    height: int
    bit_depth: int
    pixel_offset: int
    pixel_byte_count: int
    row_stride: int
    file_size: int
    capacity_bytes: int
    max_text_bytes: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def inspect_bmp(image: bytes | bytearray) -> BmpInfo:
    """Parse a 24-bit uncompressed BMP and return the modifiable pixel region."""
    if len(image) < 54:
        raise BmpError("file is too small to be a BMP image")
    if image[0:2] != b"BM":
        raise BmpError("only BMP files are supported in this version")

    declared_size = _u32(image, 2)
    pixel_offset = _u32(image, 10)
    dib_size = _u32(image, 14)
    if dib_size < 40:
        raise BmpError("unsupported BMP header")
    if pixel_offset >= len(image):
        raise BmpError("invalid BMP pixel offset")

    width = _i32(image, 18)
    height = _i32(image, 22)
    planes = _u16(image, 26)
    bit_depth = _u16(image, 28)
    compression = _u32(image, 30)

    if width <= 0 or height == 0:
        raise BmpError("invalid BMP dimensions")
    if planes != 1:
        raise BmpError("invalid BMP color planes")
    if bit_depth != 24:
        raise BmpError("only 24-bit BMP images are supported")
    if compression != 0:
        raise BmpError("compressed BMP images are not supported")

    abs_height = abs(height)
    row_stride = ((width * 3 + 3) // 4) * 4
    pixel_byte_count = row_stride * abs_height
    pixel_end = pixel_offset + pixel_byte_count
    if pixel_end > len(image):
        raise BmpError("BMP pixel data is incomplete")

    capacity = stego_core.region_capacity_bytes(pixel_byte_count)
    return BmpInfo(
        width=width,
        height=height,
        bit_depth=bit_depth,
        pixel_offset=pixel_offset,
        pixel_byte_count=pixel_byte_count,
        row_stride=row_stride,
        file_size=declared_size or len(image),
        capacity_bytes=capacity,
        max_text_bytes=stego_core.max_text_bytes(pixel_byte_count),
    )


def hide_text(image: bytes, text: bytes) -> tuple[bytes, BmpInfo]:
    """Return a new BMP file with text embedded into the pixel array."""
    info = inspect_bmp(image)
    modified = bytearray(image)
    start = info.pixel_offset
    end = start + info.pixel_byte_count
    stego_core.embed_text(modified, start, end, text)
    return bytes(modified), info


def extract_text(image: bytes) -> tuple[bytes, BmpInfo]:
    """Return hidden text bytes from a BMP file."""
    info = inspect_bmp(image)
    start = info.pixel_offset
    end = start + info.pixel_byte_count
    return stego_core.extract_text(image, start, end), info


def _u16(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little", signed=False)


def _u32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little", signed=False)


def _i32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little", signed=True)
