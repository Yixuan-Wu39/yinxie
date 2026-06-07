"""Audio adapter: WAV input or MP3 input converted to WAV, WAV output."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from . import wav_adapter


class AudioAdapterError(ValueError):
    """Raised when an audio file cannot be used in the multimedia iteration."""


@dataclass(frozen=True)
class AudioInfo:
    input_format: str
    output_format: str
    conversion: str
    channels: int
    sample_rate: int
    bits_per_sample: int
    duration_seconds: float
    data_byte_count: int
    sample_slot_count: int
    capacity_bytes: int
    max_text_bytes: int

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


def inspect_audio(audio: bytes) -> AudioInfo:
    source_format, wav_bytes = _to_wav(audio)
    wav_info = wav_adapter.inspect_wav(wav_bytes)
    return _audio_info(source_format, wav_info)


def hide_text(audio: bytes, text: bytes) -> tuple[bytes, AudioInfo]:
    source_format, wav_bytes = _to_wav(audio)
    output_wav, wav_info = wav_adapter.hide_text(wav_bytes, text)
    return output_wav, _audio_info(source_format, wav_info)


def extract_text(audio: bytes) -> tuple[bytes, AudioInfo]:
    source_format, wav_bytes = _to_wav(audio)
    text, wav_info = wav_adapter.extract_text(wav_bytes)
    return text, _audio_info(source_format, wav_info)


def _to_wav(audio: bytes) -> tuple[str, bytes]:
    if _looks_like_wav(audio):
        return "WAV", audio
    if _looks_like_mp3(audio):
        return "MP3", _mp3_to_wav(audio)
    raise AudioAdapterError("当前只支持 WAV 和 MP3 音频")


def _mp3_to_wav(audio: bytes) -> bytes:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        raise AudioAdapterError("使用 MP3 功能需要先安装 ffmpeg，或先把 MP3 转成 WAV 再上传")

    input_path = None
    output_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as source:
            source.write(audio)
            input_path = source.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as target:
            output_path = target.name

        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            input_path,
            "-acodec",
            "pcm_s16le",
            output_path,
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioAdapterError("ffmpeg 解码 MP3 超时") from exc
    finally:
        if input_path:
            try:
                Path(input_path).unlink(missing_ok=True)
            except OSError:
                pass

    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        if output_path:
            Path(output_path).unlink(missing_ok=True)
        raise AudioAdapterError(f"ffmpeg 解码 MP3 失败：{detail}" if detail else "ffmpeg 解码 MP3 失败")
    try:
        wav_bytes = Path(output_path).read_bytes() if output_path else b""
    finally:
        if output_path:
            Path(output_path).unlink(missing_ok=True)
    if not wav_bytes:
        raise AudioAdapterError("ffmpeg 没有生成有效的 WAV 文件")
    return wav_bytes


def _find_ffmpeg() -> str | None:
    configured = os.environ.get("FFMPEG_BINARY")
    if configured and Path(configured).exists():
        return configured

    found = shutil.which("ffmpeg")
    if found:
        return found

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        package_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        for path in package_root.glob("Gyan.FFmpeg*/**/ffmpeg.exe"):
            return str(path)
        for path in package_root.glob("BtbN.FFmpeg*/**/ffmpeg.exe"):
            return str(path)

    return None


def _audio_info(source_format: str, wav_info: wav_adapter.WavInfo) -> AudioInfo:
    conversion = "无需转换" if source_format == "WAV" else "MP3 已解码为 PCM WAV"
    return AudioInfo(
        input_format=source_format,
        output_format="WAV",
        conversion=conversion,
        channels=wav_info.channels,
        sample_rate=wav_info.sample_rate,
        bits_per_sample=wav_info.bits_per_sample,
        duration_seconds=wav_info.duration_seconds,
        data_byte_count=wav_info.data_byte_count,
        sample_slot_count=wav_info.sample_slot_count,
        capacity_bytes=wav_info.capacity_bytes,
        max_text_bytes=wav_info.max_text_bytes,
    )


def _looks_like_wav(audio: bytes | bytearray) -> bool:
    return len(audio) >= 12 and bytes(audio[0:4]) == b"RIFF" and bytes(audio[8:12]) == b"WAVE"


def _looks_like_mp3(audio: bytes | bytearray) -> bool:
    if len(audio) < 3:
        return False
    if bytes(audio[:3]) == b"ID3":
        return True
    return len(audio) >= 2 and audio[0] == 0xFF and (audio[1] & 0xE0) == 0xE0
