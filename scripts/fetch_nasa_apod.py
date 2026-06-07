from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlencode
from urllib.request import ProxyHandler, Request, build_opener, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "static" / "data" / "nasa_apod.json"
CACHE_STEM = OUTPUT_PATH.with_name("nasa_apod_image")
APOD_ENDPOINT = "https://api.nasa.gov/planetary/apod"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
NO_PROXY_OPENER = build_opener(ProxyHandler({}))

NASA_COMMONS_FALLBACK_IMAGES = [
    {
        "title": "File:The_Blue_Marble_(remastered).jpg",
        "displayTitle": "The Blue Marble",
        "reason": "NASA 经典地球图像，细节丰富，适合图片隐写演示。",
    },
    {
        "title": "File:Hubble_ultra_deep_field.jpg",
        "displayTitle": "Hubble Ultra Deep Field",
        "reason": "哈勃深空图像包含大量星系细节，适合展示隐写前后肉眼差异很小。",
    },
    {
        "title": "File:Saturn_during_Equinox.jpg",
        "displayTitle": "Saturn During Equinox",
        "reason": "NASA 土星图像结构清晰，适合做天文主题演示素材。",
    },
    {
        "title": "File:Jupiter_and_its_shrunken_Great_Red_Spot.jpg",
        "displayTitle": "Jupiter and the Great Red Spot",
        "reason": "NASA 木星图像色彩和纹理明显，适合现场对比展示。",
    },
    {
        "title": "File:Mars_Valles_Marineris.jpeg",
        "displayTitle": "Mars Valles Marineris",
        "reason": "NASA 火星峡谷图像纹理复杂，适合作为隐写输入图片。",
    },
    {
        "title": "File:NASA-Apollo8-Dec24-Earthrise.jpg",
        "displayTitle": "Earthrise",
        "reason": "NASA 阿波罗 8 号地出照片，辨识度高，适合摊位讲解。",
    },
]


def main() -> int:
    api_key = os.environ.get("NASA_API_KEY") or "DEMO_KEY"
    eastern_now = datetime.now(ZoneInfo("America/New_York"))
    apod_date = os.environ.get("NASA_APOD_DATE", eastern_now.date().isoformat())

    payload = fetch_apod(api_key, apod_date)
    if payload.get("status") == "ready" and payload.get("imageUrl"):
        cache_image(payload)
        if payload.get("cacheError"):
            payload = fetch_commons_fallback(apod_date, f"NASA 图片缓存失败：{payload['cacheError']}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {OUTPUT_PATH}")
    print(f"APOD date: {payload.get('date')}; status: {payload.get('status')}")
    return 0


def fetch_apod(api_key: str, apod_date: str) -> dict:
    query = urlencode({"api_key": api_key, "date": apod_date, "thumbs": "true"})
    request = Request(f"{APOD_ENDPOINT}?{query}", headers={"User-Agent": "multimedia-stego-lab/1.0"})

    try:
        with open_url(request, timeout=30, bypass_proxy=True) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        return normalize_success(data)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return normalize_error(apod_date, exc)


def normalize_success(data: dict) -> dict:
    media_type = data.get("media_type") or "unknown"
    is_image = media_type == "image"
    image_url = data.get("url") if is_image else data.get("thumbnail_url")

    return {
        "status": "ready" if is_image and image_url else "not_image",
        "source": "NASA Astronomy Picture of the Day",
        "sourceUrl": "https://apod.nasa.gov/apod/astropix.html",
        "apiUrl": "https://api.nasa.gov/planetary/apod",
        "selectionPolicy": "APOD 每天只有一个官方推荐；如果当天不是图片，前端会提示暂不作为图片素材。",
        "date": data.get("date"),
        "title": data.get("title") or "NASA 今日天文图",
        "copyright": data.get("copyright") or "NASA / Public domain where applicable",
        "mediaType": media_type,
        "cacheSourceUrl": image_url,
        "imageUrl": image_url,
        "hdImageUrl": data.get("hdurl") if is_image else None,
        "thumbnailUrl": data.get("thumbnail_url"),
        "explanation": data.get("explanation") or "",
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def normalize_error(apod_date: str, exc: Exception) -> dict:
    fallback = fetch_commons_fallback(apod_date, f"NASA APOD 抓取失败：{exc}")
    if fallback.get("status") == "ready":
        return fallback

    previous = load_previous_payload()
    if previous and previous.get("imageUrl"):
        previous["status"] = "stale"
        previous["error"] = str(exc)
        previous["fetchedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        previous["selectionPolicy"] = "本次抓取失败，保留上一张可用 NASA APOD 图片，避免前端推荐区空白。"
        return previous

    return {
        "status": "error",
        "source": "NASA Astronomy Picture of the Day",
        "sourceUrl": "https://apod.nasa.gov/apod/astropix.html",
        "apiUrl": "https://api.nasa.gov/planetary/apod",
        "selectionPolicy": "APOD 每天只有一个官方推荐；如果抓取失败，前端会显示离线提示。",
        "date": apod_date,
        "title": "NASA 今日天文图暂不可用",
        "copyright": "",
        "mediaType": "unknown",
        "imageUrl": "",
        "hdImageUrl": None,
        "thumbnailUrl": None,
        "explanation": "",
        "error": str(exc),
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


def fetch_commons_fallback(apod_date: str, source_error: str) -> dict:
    start = date_index(apod_date, len(NASA_COMMONS_FALLBACK_IMAGES))
    ordered = NASA_COMMONS_FALLBACK_IMAGES[start:] + NASA_COMMONS_FALLBACK_IMAGES[:start]
    errors: list[str] = []

    for candidate in ordered:
        try:
            payload = fetch_commons_image(candidate, apod_date, source_error)
            cache_image(payload)
            if not payload.get("cacheError"):
                return payload
            errors.append(f"{candidate['title']}: {payload['cacheError']}")
        except (HTTPError, URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{candidate['title']}: {exc}")

    return {
        "status": "error",
        "source": "Wikimedia Commons NASA fallback",
        "sourceUrl": "https://commons.wikimedia.org/wiki/Category:Images_by_NASA",
        "apiUrl": COMMONS_API,
        "selectionPolicy": "NASA APOD 不可达时，从 Wikimedia Commons 的 NASA 授权天文图片中按日期轮换。",
        "date": apod_date,
        "title": "NASA 图片推荐暂不可用",
        "copyright": "",
        "mediaType": "unknown",
        "imageUrl": "",
        "hdImageUrl": None,
        "thumbnailUrl": None,
        "explanation": "",
        "error": f"{source_error}; {'; '.join(errors)}",
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def fetch_commons_image(candidate: dict, apod_date: str, source_error: str) -> dict:
    params = {
        "action": "query",
        "titles": candidate["title"],
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": "1200",
        "format": "json",
    }
    request = Request(f"{COMMONS_API}?{urlencode(params)}", headers={"User-Agent": "multimedia-stego-lab/1.0"})

    with open_url(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
    data = json.loads(raw)

    page = next(iter(data["query"]["pages"].values()))
    info = page["imageinfo"][0]
    mime_type = info.get("mime", "")
    if not mime_type.startswith("image/"):
        raise ValueError("兜底文件不是图片")

    metadata = info.get("extmetadata", {})
    title = candidate.get("displayTitle") or metadata_value(metadata, "ObjectName") or page.get("title", candidate["title"]).replace("File:", "")
    credit = (
        metadata_value(metadata, "Artist")
        or metadata_value(metadata, "Credit")
        or metadata_value(metadata, "LicenseShortName")
        or "NASA / Wikimedia Commons"
    )
    usage_terms = metadata_value(metadata, "UsageTerms") or metadata_value(metadata, "LicenseShortName")
    explanation = candidate["reason"]
    if usage_terms:
        explanation = f"{explanation} 授权：{usage_terms}。"

    return {
        "status": "ready",
        "source": "Wikimedia Commons NASA fallback",
        "sourceUrl": info.get("descriptionurl"),
        "apiUrl": COMMONS_API,
        "selectionPolicy": "优先抓取 NASA APOD；如果 NASA 官方域名不可达，则从 Wikimedia Commons 的 NASA 授权天文图片中按日期轮换，避免推荐区停在旧图。",
        "date": apod_date,
        "title": title,
        "copyright": credit,
        "mediaType": "image",
        "cacheSourceUrl": info.get("thumburl") or info.get("url"),
        "imageUrl": info.get("thumburl") or info.get("url"),
        "hdImageUrl": info.get("url"),
        "thumbnailUrl": info.get("thumburl"),
        "explanation": explanation,
        "fallbackReason": source_error,
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def cache_image(payload: dict) -> None:
    image_url = payload.get("cacheSourceUrl") or payload.get("hdImageUrl") or payload.get("imageUrl")
    if not image_url:
        return

    request = Request(image_url, headers={"User-Agent": "multimedia-stego-lab/1.0"})
    try:
        with open_url(request, timeout=45, bypass_proxy=should_bypass_proxy(image_url)) as response:
            content_type = response.headers.get("content-type", "")
            image_bytes = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        payload["cacheError"] = str(exc)
        return

    suffix = image_suffix(content_type, image_url)
    cache_path = CACHE_STEM.with_suffix(suffix)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(image_bytes)
    remove_old_cache_files(cache_path)
    payload["cachedImageUrl"] = f"/static/data/{cache_path.name}"


def image_suffix(content_type: str, image_url: str) -> str:
    normalized = content_type.split(";")[0].strip().lower()
    if normalized in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if normalized == "image/png":
        return ".png"
    if normalized == "image/gif":
        return ".gif"
    if normalized == "image/webp":
        return ".webp"

    suffix = Path(urlparse(image_url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


def remove_old_cache_files(active_path: Path) -> None:
    for old_path in OUTPUT_PATH.parent.glob(f"{CACHE_STEM.name}.*"):
        if old_path != active_path:
            old_path.unlink(missing_ok=True)


def open_url(request: Request, timeout: int, bypass_proxy: bool = False):
    if bypass_proxy:
        return NO_PROXY_OPENER.open(request, timeout=timeout)
    return urlopen(request, timeout=timeout)


def should_bypass_proxy(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return hostname == "api.nasa.gov" or hostname.endswith(".nasa.gov")


def metadata_value(metadata: dict, key: str) -> str:
    value = metadata.get(key, {}).get("value", "")
    if not isinstance(value, str):
        return ""
    return clean_html(value)


def clean_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", value)
    return html.unescape(without_tags).strip()


def date_index(value: str, length: int) -> int:
    return sum(ord(char) for char in value) % length


if __name__ == "__main__":
    raise SystemExit(main())
