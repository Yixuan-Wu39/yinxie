from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "static" / "data" / "audio_recommendation.json"
CACHE_STEM = OUTPUT_PATH.with_name("audio_recommendation")
APPLE_MUSIC_CHART_URL = "https://rss.marketingtools.apple.com/api/v2/cn/music/most-played/10/songs.json"
ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup"


def main() -> int:
    today = recommendation_date()
    payload = fetch_recommendation(today)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {OUTPUT_PATH}")
    print(f"Audio date: {payload.get('date')}; status: {payload.get('status')}")
    return 0


def recommendation_date() -> str:
    override = os.environ.get("AUDIO_RECOMMENDATION_DATE")
    if override:
        return override
    return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()


def fetch_recommendation(today: str) -> dict:
    errors: list[str] = []

    try:
        return fetch_apple_music_preview(today)
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"Apple Music 榜单试听片段：{exc}")

    return normalize_error(today, "; ".join(errors) or "没有可用音频")


def fetch_apple_music_preview(today: str) -> dict:
    chart_request = Request(APPLE_MUSIC_CHART_URL, headers={"User-Agent": "multimedia-stego-lab/1.0"})
    with urlopen(chart_request, timeout=30) as response:
        chart_raw = response.read().decode("utf-8")
    chart = json.loads(chart_raw)
    results = chart.get("feed", {}).get("results") or []
    if not results:
        raise ValueError("Apple Music 榜单为空")

    lookup_errors: list[str] = []
    for index, item in enumerate(results, start=1):
        try:
            preview = lookup_preview(item["id"])
            if not preview.get("previewUrl"):
                raise ValueError("没有试听片段")
            cached_url, cached_name, mime_type = cache_audio(preview["previewUrl"], "audio/x-m4a")
            return apple_payload(today, chart, item, preview, index, cached_url, cached_name, mime_type)
        except (HTTPError, URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            lookup_errors.append(f"{item.get('name', item.get('id', 'unknown'))}: {exc}")

    raise ValueError("; ".join(lookup_errors) or "榜单中没有可用试听片段")


def lookup_preview(song_id: str) -> dict:
    params = {"id": song_id, "country": "cn", "entity": "song"}
    request = Request(f"{ITUNES_LOOKUP_URL}?{urlencode(params)}", headers={"User-Agent": "multimedia-stego-lab/1.0"})
    with urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
    data = json.loads(raw)
    for result in data.get("results", []):
        if result.get("kind") == "song" and result.get("previewUrl"):
            return result
    raise ValueError("iTunes lookup 没有返回试听片段")


def apple_payload(
    today: str,
    chart: dict,
    item: dict,
    preview: dict,
    rank: int,
    cached_url: str,
    cached_name: str,
    mime_type: str,
) -> dict:
    feed = chart.get("feed", {})
    artwork_url = item.get("artworkUrl100") or preview.get("artworkUrl100") or ""
    if artwork_url:
        artwork_url = artwork_url.replace("100x100bb", "600x600bb")
    return {
        "status": "ready",
        "source": "Apple Music / iTunes preview",
        "sourceUrl": item.get("url") or preview.get("trackViewUrl"),
        "apiUrl": APPLE_MUSIC_CHART_URL,
        "selectionPolicy": "每天抓取 Apple Music 国区热门歌曲榜，选择榜单中第一个可用 30 秒试听片段；只缓存试听片段，不缓存完整歌曲。",
        "date": today,
        "chartName": feed.get("title") or "Apple Music 热门歌曲排行",
        "chartCountry": "CN",
        "chartRank": rank,
        "title": item.get("name") or preview.get("trackName") or "Apple Music 试听片段",
        "artist": item.get("artistName") or preview.get("artistName") or "Apple Music",
        "album": preview.get("collectionName") or "",
        "license": preview.get("copyright") or "试听片段版权归唱片方所有",
        "durationSeconds": 30.0,
        "mimeType": mime_type,
        "audioUrl": preview["previewUrl"],
        "cachedAudioUrl": cached_url,
        "cachedFilename": cached_name,
        "artworkUrl": artwork_url,
        "description": "来自 Apple Music 国区热门歌曲榜的 30 秒试听片段，适合现场播放和音频隐写测试。",
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def cache_audio(audio_url: str, mime_type: str) -> tuple[str, str, str]:
    request = Request(audio_url, headers={"User-Agent": "multimedia-stego-lab/1.0"})
    with urlopen(request, timeout=60) as response:
        content_type = response.headers.get("content-type") or mime_type
        audio_bytes = response.read()
    response_mime = content_type.split(";")[0].strip() or mime_type

    suffix = audio_suffix(content_type, audio_url)
    cache_path = CACHE_STEM.with_suffix(suffix)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(audio_bytes)
    remove_old_cache_files(cache_path)
    return f"/static/data/{cache_path.name}", cache_path.name, response_mime


def audio_suffix(content_type: str, audio_url: str) -> str:
    normalized = content_type.split(";")[0].strip().lower()
    if normalized == "audio/mpeg":
        return ".mp3"
    if normalized in {"audio/mp4", "audio/x-m4a", "audio/x-m4p", "audio/aac", "audio/x-aac"}:
        return ".m4a"
    if normalized in {"audio/wav", "audio/x-wav"}:
        return ".wav"
    if normalized in {"audio/ogg", "application/ogg"}:
        return ".ogg"

    suffix = Path(urlparse(audio_url).path).suffix.lower()
    if suffix in {".m4a", ".aac", ".mp3", ".wav", ".ogg", ".oga"}:
        if suffix == ".aac":
            return ".m4a"
        return ".ogg" if suffix == ".oga" else suffix
    return ".m4a"


def remove_old_cache_files(active_path: Path) -> None:
    for old_path in OUTPUT_PATH.parent.glob(f"{CACHE_STEM.name}.*"):
        if old_path != active_path:
            old_path.unlink(missing_ok=True)


def normalize_error(today: str, error: str) -> dict:
    previous = load_previous_payload()
    if previous and previous.get("cachedAudioUrl"):
        previous["status"] = "stale"
        previous["error"] = error
        previous["fetchedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        previous["selectionPolicy"] = "本次音频推荐更新失败，保留上一段可用音频。"
        return previous

    return {
        "status": "error",
        "source": "Apple Music / iTunes preview",
        "sourceUrl": "https://music.apple.com/cn/new",
        "apiUrl": APPLE_MUSIC_CHART_URL,
        "selectionPolicy": "每天抓取 Apple Music 国区热门歌曲榜，选择榜单中第一个可用 30 秒试听片段。",
        "date": today,
        "title": "今日音频推荐暂不可用",
        "artist": "",
        "album": "",
        "license": "",
        "durationSeconds": 0,
        "mimeType": "",
        "audioUrl": "",
        "cachedAudioUrl": "",
        "cachedFilename": "",
        "artworkUrl": "",
        "description": "",
        "error": error,
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def load_previous_payload() -> dict | None:
    if not OUTPUT_PATH.exists():
        return None
    try:
        payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and payload.get("status") in {"ready", "stale"}:
        return payload
    return None


if __name__ == "__main__":
    raise SystemExit(main())
