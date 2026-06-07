import unittest

from backend.crypto_core import CryptoError, decrypt_text, encrypt_text, normalize_shift


class CaesarByteCryptoTests(unittest.TestCase):
    def test_unicode_text_round_trips_through_byte_caesar(self):
        original = "中文、符号？！ABC 123 🚀"
        encrypted = encrypt_text(original, 7)

        self.assertNotEqual(encrypted, original.encode("utf-8"))
        self.assertEqual(decrypt_text(encrypted, 7), original)

    def test_zero_shift_keeps_existing_plain_text_behavior(self):
        original = "不加密也能兼容旧文件。"
        encrypted = encrypt_text(original, 0)

        self.assertEqual(encrypted, original.encode("utf-8"))
        self.assertEqual(decrypt_text(encrypted, 0), original)

    def test_rejects_invalid_shift(self):
        for value in (-1, 256, "abc", True):
            with self.subTest(value=value):
                with self.assertRaises(CryptoError):
                    normalize_shift(value)


if __name__ == "__main__":
    unittest.main()
