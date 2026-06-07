import math
import struct
import subprocess
import unittest
import wave
from io import BytesIO

from backend.crypto_core import decrypt_text, encrypt_text
from backend.audio_adapter import _find_ffmpeg, extract_text, hide_text, inspect_audio


def make_wav(duration_seconds=1.2, sample_rate=8000, frequency=440):
    buffer = BytesIO()
    sample_count = int(duration_seconds * sample_rate)
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(sample_count):
            value = int(11000 * math.sin(2 * math.pi * frequency * index / sample_rate))
            frames += struct.pack("<h", value)
        wav.writeframes(bytes(frames))
    return buffer.getvalue()


def make_mp3_from_wav(wav_bytes):
    return make_compressed_audio_from_wav(wav_bytes, "libmp3lame", "mp3", "128k")


def make_m4a_from_wav(wav_bytes):
    return make_compressed_audio_from_wav(wav_bytes, "aac", "ipod", "96k")


def make_compressed_audio_from_wav(wav_bytes, codec, output_format, bitrate):
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return None
    proc = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-codec:a",
            codec,
            "-b:a",
            bitrate,
            "-f",
            output_format,
            "pipe:1",
        ],
        input=wav_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


class AudioConversionStegoTests(unittest.TestCase):
    def test_wav_hide_then_extract_round_trips_text(self):
        wav_bytes = make_wav()
        original = "WAV 直接隐写。".encode("utf-8")
        output, info = hide_text(wav_bytes, original)
        self.assertEqual(info.input_format, "WAV")
        self.assertEqual(output[:4], b"RIFF")
        restored, _ = extract_text(output)
        self.assertEqual(restored, original)

    def test_caesar_encrypts_unicode_text_before_audio_stego(self):
        wav_bytes = make_wav()
        original = "音频中文、符号？！ABC 123 🎵"
        encrypted = encrypt_text(original, 29)

        output, _ = hide_text(wav_bytes, encrypted)
        restored, _ = extract_text(output)

        self.assertNotEqual(restored, original.encode("utf-8"))
        self.assertEqual(decrypt_text(restored, 29), original)

    def test_mp3_input_is_converted_to_wav_output(self):
        mp3_bytes = make_mp3_from_wav(make_wav())
        if mp3_bytes is None:
            self.skipTest("ffmpeg is not available for MP3 conversion")

        original = "MP3 输入先转 WAV 再隐写。".encode("utf-8")
        analyzed = inspect_audio(mp3_bytes)
        output, info = hide_text(mp3_bytes, original)
        self.assertEqual(analyzed.input_format, "MP3")
        self.assertEqual(info.output_format, "WAV")
        self.assertEqual(output[:4], b"RIFF")
        restored, restored_info = extract_text(output)
        self.assertEqual(restored_info.input_format, "WAV")
        self.assertEqual(restored, original)

    def test_m4a_input_is_converted_to_wav_output(self):
        m4a_bytes = make_m4a_from_wav(make_wav())
        if m4a_bytes is None:
            self.skipTest("ffmpeg is not available for M4A conversion")

        original = "M4A 试听片段先转 WAV 再隐写。".encode("utf-8")
        analyzed = inspect_audio(m4a_bytes)
        output, info = hide_text(m4a_bytes, original)
        self.assertEqual(analyzed.input_format, "M4A")
        self.assertEqual(info.output_format, "WAV")
        self.assertEqual(output[:4], b"RIFF")
        restored, restored_info = extract_text(output)
        self.assertEqual(restored_info.input_format, "WAV")
        self.assertEqual(restored, original)


if __name__ == "__main__":
    unittest.main()
