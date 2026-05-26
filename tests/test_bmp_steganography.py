import unittest

from backend.bmp_adapter import BmpError, extract_text, hide_text, inspect_bmp
from backend.stego_core import StegoError


def make_bmp(width=24, height=24):
    row_stride = ((width * 3 + 3) // 4) * 4
    image_size = row_stride * height
    file_size = 54 + image_size

    file_header = bytearray()
    file_header += b"BM"
    file_header += file_size.to_bytes(4, "little")
    file_header += (0).to_bytes(2, "little")
    file_header += (0).to_bytes(2, "little")
    file_header += (54).to_bytes(4, "little")

    dib_header = bytearray()
    dib_header += (40).to_bytes(4, "little")
    dib_header += width.to_bytes(4, "little", signed=True)
    dib_header += height.to_bytes(4, "little", signed=True)
    dib_header += (1).to_bytes(2, "little")
    dib_header += (24).to_bytes(2, "little")
    dib_header += (0).to_bytes(4, "little")
    dib_header += image_size.to_bytes(4, "little")
    dib_header += (2835).to_bytes(4, "little", signed=True)
    dib_header += (2835).to_bytes(4, "little", signed=True)
    dib_header += (0).to_bytes(4, "little")
    dib_header += (0).to_bytes(4, "little")

    pixels = bytearray()
    for y in range(height):
        row = bytearray()
        for x in range(width):
            row += bytes(((x * 7) % 256, (y * 11) % 256, ((x + y) * 5) % 256))
        row += b"\x00" * (row_stride - width * 3)
        pixels += row

    return bytes(file_header + dib_header + pixels)


class BmpSteganographyTests(unittest.TestCase):
    def test_inspect_bmp_reports_capacity(self):
        bmp = make_bmp(10, 10)
        info = inspect_bmp(bmp)
        self.assertEqual(info.width, 10)
        self.assertEqual(info.height, 10)
        self.assertEqual(info.bit_depth, 24)
        self.assertEqual(info.pixel_offset, 54)
        self.assertGreater(info.max_text_bytes, 0)

    def test_hide_then_extract_round_trips_utf8_text(self):
        bmp = make_bmp()
        original = "你好，BMP-only 隐写第一版。".encode("utf-8")
        modified, _ = hide_text(bmp, original)
        restored, _ = extract_text(modified)
        self.assertEqual(restored, original)
        self.assertNotEqual(modified, bmp)

    def test_rejects_non_bmp_input(self):
        with self.assertRaises(BmpError):
            inspect_bmp(b"not a bmp")

    def test_rejects_text_that_exceeds_capacity(self):
        bmp = make_bmp(4, 4)
        info = inspect_bmp(bmp)
        too_long = b"x" * (info.max_text_bytes + 1)
        with self.assertRaises(StegoError):
            hide_text(bmp, too_long)

    def test_rejects_image_without_hidden_marker(self):
        bmp = make_bmp()
        with self.assertRaises(StegoError):
            extract_text(bmp)


if __name__ == "__main__":
    unittest.main()
