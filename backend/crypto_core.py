"""Shared Caesar-style byte encryption for hidden text."""

from __future__ import annotations


BYTE_MODULUS = 256


class CryptoError(ValueError):
    """Raised when encrypted hidden text cannot be decoded."""


def normalize_shift(value: object) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        raise CryptoError("凯撒偏移量必须是 0 到 255 之间的整数")
    if isinstance(value, int):
        shift = value
    elif isinstance(value, str):
        try:
            shift = int(value.strip())
        except ValueError as exc:
            raise CryptoError("凯撒偏移量必须是 0 到 255 之间的整数") from exc
    else:
        raise CryptoError("凯撒偏移量必须是 0 到 255 之间的整数")

    if shift < 0 or shift >= BYTE_MODULUS:
        raise CryptoError("凯撒偏移量必须是 0 到 255 之间的整数")
    return shift


def encrypt_text(text: str, shift: int) -> bytes:
    if not isinstance(text, str):
        raise CryptoError("文本内容必须是字符串")
    return shift_bytes(text.encode("utf-8"), shift)


def decrypt_text(payload: bytes, shift: int) -> str:
    decrypted = shift_bytes(payload, -shift)
    try:
        return decrypted.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CryptoError("解密失败：请确认凯撒偏移量是否正确") from exc


def shift_bytes(payload: bytes, shift: int) -> bytes:
    normalized_shift = shift % BYTE_MODULUS
    if normalized_shift == 0:
        return bytes(payload)
    return bytes((value + normalized_shift) % BYTE_MODULUS for value in payload)
