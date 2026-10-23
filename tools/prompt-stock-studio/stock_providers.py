"""Pixabay stock search with 24-hour local response caching per API guidance."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

PIXABAY_IMAGE = "https://pixabay.com/api/"
PIXABAY_VIDEO = "https://pixabay.com/api/videos/"
CACHE_TTL_SECONDS = 24 * 60 * 60


class StockSearchError(RuntimeError):
    pass


def _pixabay_json(endpoint: str, key: str, params: dict, cache_dir: Path) -> dict:
    """Fetch at most once per request combination / 24h. Never store the API key."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256(json.dumps(
        {"endpoint": endpoint, "params": params, "key_fingerprint": hashlib.sha256(key.encode()).hexdigest()},
        sort_keys=True, ensure_ascii=False
    ).encode("utf-8")).hexdigest()
    path = cache_dir / (identity + ".json")
    if path.exists() and 0 <= time.time() - path.stat().st_mtime < CACHE_TTL_SECONDS:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    try:
        response = requests.get(endpoint, params={"key": key, **params}, timeout=25)
        if response.status_code == 429:
            raise StockSearchError("Pixabay: osiągnięto limit API.")
        if not response.ok:
            raise StockSearchError("Pixabay API zwrócił kod " + str(response.status_code))
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        # Do not expose the request URL; it includes the private API key.
        raise StockSearchError("Błąd połączenia z Pixabay. Sprawdź internet i klucz API.") from exc
    if not isinstance(data, dict):
        raise StockSearchError("Pixabay zwrócił nieprawidłowe dane.")
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
    except OSError:
        pass  # Cache failure is not fatal to the current render.
    return data


def _candidate_image(hit: dict) -> dict | None:
    url = hit.get("fullHDURL") or hit.get("largeImageURL") or hit.get("webformatURL")
    if not url:
        return None
    return {
        "kind": "photo", "id": "pixabay:photo:" + str(hit.get("id")),
        "provider": "Pixabay", "url": url, "page": hit.get("pageURL", ""),
        "credit": hit.get("user", "Pixabay creator"),
        "media_type": hit.get("type", "photo"),
    }


def _candidate_video(hit: dict) -> dict | None:
    videos = hit.get("videos", {})
    for size in ("medium", "small", "large"):
        stream = videos.get(size) or {}
        url = stream.get("url")
        if url and (not stream.get("size") or stream["size"] <= 145 * 1024 * 1024):
            return {
                "kind": "video", "id": "pixabay:video:" + str(hit.get("id")),
                "provider": "Pixabay", "url": url, "page": hit.get("pageURL", ""),
                "credit": hit.get("user", "Pixabay creator"), "media_type": hit.get("type", "film"),
            }
    return None


def search_pixabay(query: str, key: str, format_name: str, preference: str,
                   seen: set, cache_dir: Path) -> dict | None:
    """Return single unique stock asset or None. 'Grafiki i ilustracje' forces illustrations."""
    if not key:
        return None
    query = query.strip()[:100]
    kinds = ["photo"] if preference == "Grafiki i ilustracje" else (
        ["video"] if preference == "Tylko wideo" else
        ["photo"] if preference == "Tylko zdjęcia" else
        ["video", "photo"]
    )
    for kind in kinds:
        params = {"q": query, "per_page": 20, "safesearch": "true", "order": "popular"}
        if kind == "photo":
            params["image_type"] = "illustration" if preference == "Grafiki i ilustracje" else "photo"
        raw = _pixabay_json(PIXABAY_VIDEO if kind == "video" else PIXABAY_IMAGE,
                            key, params, cache_dir)
        candidates = []
        for hit in raw.get("hits", []):
            if not isinstance(hit, dict):
                continue
            item = _candidate_video(hit) if kind == "video" else _candidate_image(hit)
            if item and item["id"] not in seen:
                if kind == "video":
                    size = (hit.get("videos", {}).get("medium") or hit.get("videos", {}).get("small") or {})
                    w, h = size.get("width", 1), size.get("height", 1)
                else:
                    w, h = hit.get("imageWidth", 1), hit.get("imageHeight", 1)
                ratio = w / max(h, 1)
                target = {"9:16": 9/16, "16:9": 16/9, "1:1": 1}[format_name]
                candidates.append((abs(ratio - target), item))
        if candidates:
            candidates.sort(key=lambda pair: pair[0])
            selected = candidates[0][1]
            seen.add(selected["id"])
            return selected
    return None
