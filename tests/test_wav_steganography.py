import math
import struct
import unittest
import wave
from io import BytesIO

from backend.wav_adapter import WavError, extract_text, hide_text, inspect_wav


def make_wav(duration_seconds=1.0, sample_rate=8000, frequency=440):
    buffer = BytesIO()
    sample_count = int(duration_seconds * sample_rate)
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(sample_count):
            value = int(12000 * math.sin(2 * math.pi * frequency * index / sample_rate))
            frames += struct.pack("<h", value)
        wav.writeframes(bytes(frames))
    return buffer.getvalue()


class WavSteganographyTests(unittest.TestCase):
    def test_inspect_wav_reports_capacity(self):
        audio = make_wav()
        info = inspect_wav(audio)
        self.assertEqual(info.channels, 1)
        self.assertEqual(info.sample_rate, 8000)
        self.assertEqual(info.bits_per_sample, 16)
        self.assertGreater(info.max_text_bytes, 0)

    def test_hide_then_extract_round_trips_utf8_text(self):
        audio = make_wav()
        original = "你好，WAV 音频隐写第一版。".encode("utf-8")
        modified, _ = hide_text(audio, original)
        restored, _ = extract_text(modified)
        self.assertEqual(restored, original)
        self.assertNotEqual(modified, audio)

    def test_rejects_non_wav_input(self):
        with self.assertRaises(WavError):
            inspect_wav(b"not a wav")

    def test_rejects_audio_without_hidden_marker(self):
        audio = make_wav()
        with self.assertRaises(WavError):
            extract_text(audio)


if __name__ == "__main__":
    unittest.main()
