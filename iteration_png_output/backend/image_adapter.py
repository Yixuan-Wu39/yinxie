"""JPG/BMP/PNG input adapter that always writes lossless PNG output."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from . import stego_core


SUPPORTED_INPUT_FORMATS = {"JPEG", "PNG", "BMP"}


class ImageAdapterError(ValueError):
    """Raised when an input image cannot be used for this iteration."""


@dataclass(frozen=True)
class ImageInfo:
    input_format: str
    output_format: str
    width: int
    height: int
    source_mode: str
    working_mode: str
    pixel_byte_count: int
    capacity_bytes: int
    max_text_bytes: int

    def to_dict(self) -> dict[str, int | str]:
        return asdict(self)


def inspect_image(image_bytes: bytes) -> ImageInfo:
    with _open_supported_image(image_bytes) as image:
        rgb = image.convert("RGB")
        pixel_byte_count = rgb.width * rgb.height * 3
        return ImageInfo(
            input_format=image.format or "UNKNOWN",
            output_format="PNG",
            width=rgb.width,
            height=rgb.height,
            source_mode=image.mode,
            working_mode="RGB",
            pixel_byte_count=pixel_byte_count,
            capacity_bytes=stego_core.region_capacity_bytes(pixel_byte_count),
            max_text_bytes=stego_core.max_text_bytes(pixel_byte_count),
        )


def hide_text(image_bytes: bytes, text: bytes) -> tuple[bytes, ImageInfo]:
    with _open_supported_image(image_bytes) as image:
        rgb = image.convert("RGB")
        info = _info_from_images(image, rgb)
        pixels = bytearray(rgb.tobytes())
        stego_core.embed_text(pixels, text)
        output_image = Image.frombytes("RGB", rgb.size, bytes(pixels))
        out = BytesIO()
        output_image.save(out, format="PNG", optimize=False)
        return out.getvalue(), info


def extract_text(image_bytes: bytes) -> tuple[bytes, ImageInfo]:
    with _open_supported_image(image_bytes) as image:
        rgb = image.convert("RGB")
        info = _info_from_images(image, rgb)
        return stego_core.extract_text(rgb.tobytes()), info


def _open_supported_image(image_bytes: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(image_bytes))
        image.load()
    except UnidentifiedImageError as exc:
        raise ImageAdapterError("only JPG, PNG, and BMP images are supported") from exc

    image_format = image.format or "UNKNOWN"
    if image_format not in SUPPORTED_INPUT_FORMATS:
        image.close()
        raise ImageAdapterError("only JPG, PNG, and BMP images are supported")
    if image.width <= 0 or image.height <= 0:
        image.close()
        raise ImageAdapterError("invalid image dimensions")
    return image


def _info_from_images(source: Image.Image, rgb: Image.Image) -> ImageInfo:
    pixel_byte_count = rgb.width * rgb.height * 3
    return ImageInfo(
        input_format=source.format or "UNKNOWN",
        output_format="PNG",
        width=rgb.width,
        height=rgb.height,
        source_mode=source.mode,
        working_mode="RGB",
        pixel_byte_count=pixel_byte_count,
        capacity_bytes=stego_core.region_capacity_bytes(pixel_byte_count),
        max_text_bytes=stego_core.max_text_bytes(pixel_byte_count),
    )
