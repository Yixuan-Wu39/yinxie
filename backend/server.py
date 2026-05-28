"""Small standard-library HTTP server for the BMP steganography prototype."""

from __future__ import annotations

import base64
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .bmp_adapter import (
    BmpError,
    extract_text as extract_bmp_text,
    hide_text as hide_bmp_text,
    inspect_bmp,
)
from .stego_core import StegoError
from .wav_adapter import (
    WavError,
    extract_text as extract_wav_text,
    hide_text as hide_wav_text,
    inspect_wav,
)


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"
MAX_JSON_BYTES = 40 * 1024 * 1024


class AppHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json({"ok": True})
            return
        if path in {"", "/"}:
            self._send_file(STATIC_DIR / "index.html")
            return
        if path.startswith("/static/"):
            rel = unquote(path.removeprefix("/static/"))
            target = (STATIC_DIR / rel).resolve()
            if STATIC_DIR.resolve() not in target.parents:
                self._send_json({"error": "invalid static path"}, status=400)
                return
            self._send_file(target)
            return
        self._send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/analyze":
                payload = self._read_json()
                image = _decode_base64(payload.get("imageBase64"))
                info = inspect_bmp(image)
                self._send_json({"bmp": info.to_dict()})
                return

            if path == "/api/hide":
                payload = self._read_json()
                image = _decode_base64(payload.get("imageBase64"))
                text = payload.get("text", "")
                if not isinstance(text, str):
                    raise ValueError("text must be a string")
                text_bytes = text.encode("utf-8")
                modified, info = hide_bmp_text(image, text_bytes)
                self._send_json(
                    {
                        "bmp": info.to_dict(),
                        "textBytes": len(text_bytes),
                        "filename": _output_name(payload.get("filename")),
                        "imageBase64": base64.b64encode(modified).decode("ascii"),
                    }
                )
                return

            if path == "/api/extract":
                payload = self._read_json()
                image = _decode_base64(payload.get("imageBase64"))
                text_bytes, info = extract_bmp_text(image)
                self._send_json(
                    {
                        "bmp": info.to_dict(),
                        "textBytes": len(text_bytes),
                        "text": text_bytes.decode("utf-8", errors="replace"),
                    }
                )
                return

            if path == "/api/audio/analyze":
                payload = self._read_json()
                audio = _decode_base64(payload.get("audioBase64"))
                info = inspect_wav(audio)
                self._send_json({"wav": info.to_dict()})
                return

            if path == "/api/audio/hide":
                payload = self._read_json()
                audio = _decode_base64(payload.get("audioBase64"))
                text = payload.get("text", "")
                if not isinstance(text, str):
                    raise ValueError("text must be a string")
                text_bytes = text.encode("utf-8")
                modified, info = hide_wav_text(audio, text_bytes)
                self._send_json(
                    {
                        "wav": info.to_dict(),
                        "textBytes": len(text_bytes),
                        "filename": _output_audio_name(payload.get("filename")),
                        "audioBase64": base64.b64encode(modified).decode("ascii"),
                    }
                )
                return

            if path == "/api/audio/extract":
                payload = self._read_json()
                audio = _decode_base64(payload.get("audioBase64"))
                text_bytes, info = extract_wav_text(audio)
                self._send_json(
                    {
                        "wav": info.to_dict(),
                        "textBytes": len(text_bytes),
                        "text": text_bytes.decode("utf-8", errors="replace"),
                    }
                )
                return

            self._send_json({"error": "not found"}, status=404)
        except (BmpError, WavError, StegoError, ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, status=400)

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[server] {self.address_string()} - {fmt % args}")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("empty request body")
        if length > MAX_JSON_BYTES:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
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
            self._send_json({"error": "not found"}, status=404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"BMP steganography server running at http://{host}:{port}")
    server.serve_forever()


def _decode_base64(value: object) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError("imageBase64 is required")
    if "," in value:
        value = value.split(",", 1)[1]
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError("invalid base64 image data") from exc


def _output_name(filename: object) -> str:
    if not isinstance(filename, str) or not filename.strip():
        return "stego-output.bmp"
    name = Path(filename).stem
    return f"{name}-stego.bmp"


def _output_audio_name(filename: object) -> str:
    if not isinstance(filename, str) or not filename.strip():
        return "stego-output.wav"
    name = Path(filename).stem
    return f"{name}-stego.wav"
