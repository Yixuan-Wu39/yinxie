import unittest
from io import BytesIO

from PIL import Image

from backend.crypto_core import decrypt_text, encrypt_text
from backend.image_adapter import ImageAdapterError, extract_text, hide_text, inspect_image


def make_image_bytes(fmt="PNG", size=(48, 32)):
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = ((x * 5) % 256, (y * 7) % 256, ((x + y) * 3) % 256)
    out = BytesIO()
    image.save(out, format=fmt)
    return out.getvalue()


class PngOutputImageSteganographyTests(unittest.TestCase):
    def test_accepts_png_bmp_and_jpg_inputs(self):
        for fmt in ("PNG", "BMP", "JPEG"):
            with self.subTest(fmt=fmt):
                info = inspect_image(make_image_bytes(fmt))
                self.assertEqual(info.output_format, "PNG")
                self.assertGreater(info.max_text_bytes, 0)

    def test_hide_outputs_png_and_extract_round_trips_text(self):
        text = "第二版：JPG/BMP/PNG 输入，PNG 输出。".encode("utf-8")
        for fmt in ("PNG", "BMP", "JPEG"):
            with self.subTest(fmt=fmt):
                output, info = hide_text(make_image_bytes(fmt), text)
                self.assertEqual(info.output_format, "PNG")
                self.assertEqual(output[:8], b"\x89PNG\r\n\x1a\n")
                restored, restored_info = extract_text(output)
                self.assertEqual(restored_info.input_format, "PNG")
                self.assertEqual(restored, text)

    def test_caesar_encrypts_unicode_text_before_image_stego(self):
        original = "中文、符号？！ABC 123 🚀"
        encrypted = encrypt_text(original, 17)

        output, _ = hide_text(make_image_bytes("PNG"), encrypted)
        restored, _ = extract_text(output)

        self.assertNotEqual(restored, original.encode("utf-8"))
        self.assertEqual(decrypt_text(restored, 17), original)

    def test_rejects_non_image_input(self):
        with self.assertRaises(ImageAdapterError):
            inspect_image(b"not an image")


if __name__ == "__main__":
    unittest.main()
