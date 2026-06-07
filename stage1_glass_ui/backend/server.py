"""HTTP server for the iteration 2 PNG-output image steganography prototype."""

from __future__ import annotations

import base64
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .audio_adapter import (
    AudioAdapterError,
    extract_text as extract_audio_text,
    hide_text as hide_audio_text,
    inspect_audio,
)
from .image_adapter import (
    ImageAdapterError,
    extract_text as extract_image_text,
    hide_text as hide_image_text,
    inspect_image,
)
from .stego_core import StegoError


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
MAX_JSON_BYTES = 80 * 1024 * 1024


class AppHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({"ok": True, "version": "stage1-glass-ui"})
            return
        if path in {"", "/"}:
            self._send_file(STATIC_DIR / "index.html")
            return
        if path.startswith("/static/"):
            rel = unquote(path.removeprefix("/static/"))
            target = (STATIC_DIR / rel).resolve()
            if STATIC_DIR.resolve() not in target.parents:
                self._send_json({"error": "静态资源路径无效"}, status=400)
                return
            self._send_file(target)
            return
        self._send_json({"error": "没有找到这个页面或接口"}, status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/image/analyze":
                payload = self._read_json()
                image = _decode_base64(payload.get("imageBase64"))
                info = inspect_image(image)
                self._send_json({"image": info.to_dict()})
                return

            if path == "/api/image/hide":
                payload = self._read_json()
                image = _decode_base64(payload.get("imageBase64"))
                text = payload.get("text", "")
                if not isinstance(text, str):
                    raise ValueError("文本内容必须是字符串")
                text_bytes = text.encode("utf-8")
                modified, info = hide_image_text(image, text_bytes)
                self._send_json(
                    {
                        "image": info.to_dict(),
                        "textBytes": len(text_bytes),
                        "filename": _output_name(payload.get("filename")),
                        "imageBase64": base64.b64encode(modified).decode("ascii"),
                    }
                )
                return

            if path == "/api/image/extract":
                payload = self._read_json()
                image = _decode_base64(payload.get("imageBase64"))
                text_bytes, info = extract_image_text(image)
                self._send_json(
                    {
                        "image": info.to_dict(),
                        "textBytes": len(text_bytes),
                        "text": text_bytes.decode("utf-8", errors="replace"),
                    }
                )
                return

            if path == "/api/audio/analyze":
                payload = self._read_json()
                audio = _decode_base64(payload.get("audioBase64"), "audioBase64")
                info = inspect_audio(audio)
                self._send_json({"audio": info.to_dict()})
                return

            if path == "/api/audio/hide":
                payload = self._read_json()
                audio = _decode_base64(payload.get("audioBase64"), "audioBase64")
                text = payload.get("text", "")
                if not isinstance(text, str):
                    raise ValueError("文本内容必须是字符串")
                text_bytes = text.encode("utf-8")
                modified, info = hide_audio_text(audio, text_bytes)
                self._send_json(
                    {
                        "audio": info.to_dict(),
                        "textBytes": len(text_bytes),
                        "filename": _output_audio_name(payload.get("filename")),
                        "audioBase64": base64.b64encode(modified).decode("ascii"),
                    }
                )
                return

            if path == "/api/audio/extract":
                payload = self._read_json()
                audio = _decode_base64(payload.get("audioBase64"), "audioBase64")
                text_bytes, info = extract_audio_text(audio)
                self._send_json(
                    {
                        "audio": info.to_dict(),
                        "textBytes": len(text_bytes),
                        "text": text_bytes.decode("utf-8", errors="replace"),
                    }
                )
                return

            self._send_json({"error": "没有找到这个接口"}, status=404)
        except (AudioAdapterError, ImageAdapterError, StegoError, ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, status=400)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[多媒体隐写] {self.address_string()} - {fmt % args}")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("请求内容为空")
        if length > MAX_JSON_BYTES:
            raise ValueError("上传内容太大")
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("请求格式不正确")
        return payload

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "没有找到这个文件"}, status=404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8031) -> None:
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"阶段1玻璃拟态版已启动：http://{host}:{port}")
    server.serve_forever()


def _decode_base64(value: object, field_name: str = "imageBase64") -> bytes:
    if not isinstance(value, str) or not value:
        label = "图片数据" if field_name == "imageBase64" else "音频数据"
        raise ValueError(f"缺少{label}")
    if "," in value:
        value = value.split(",", 1)[1]
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        label = "图片数据" if field_name == "imageBase64" else "音频数据"
        raise ValueError(f"{label}格式无效") from exc


def _output_name(filename: object) -> str:
    if not isinstance(filename, str) or not filename.strip():
        return "stego-output.png"
    return f"{Path(filename).stem}-stego.png"


def _output_audio_name(filename: object) -> str:
    if not isinstance(filename, str) or not filename.strip():
        return "stego-output.wav"
    return f"{Path(filename).stem}-stego.wav"
