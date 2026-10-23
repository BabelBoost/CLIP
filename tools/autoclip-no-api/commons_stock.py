"""Optional CC0 photo discovery from public Wikimedia Commons web pages, no API/key.

This is best effort HTML search. Only files with a recognizable CC0 1.0 link
on their own Commons file page are accepted. No CC BY-SA auto re-licensing.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "BabelBoost-AutoClip/3.0 (https://github.com/BabelBoost/CLIP)"
COMMONS_HOST = "commons.wikimedia.org"
MAX_DOWNLOAD = 20 * 1024 * 1024


def _html(url: str) -> BeautifulSoup:
    res = requests.get(url, timeout=(5, 12), headers={"User-Agent": USER_AGENT})
    res.raise_for_status()
    if urlparse(res.url).hostname != COMMONS_HOST:
        raise ValueError("Outside Commons")
    return BeautifulSoup(res.text, "html.parser")


def _file_pages(doc: BeautifulSoup) -> list[str]:
    candidates = []
    for a in doc.select("div.mw-search-result-heading a[href], a[href^='/wiki/File:']"):
        path = str(a.get("href", ""))
        if path.startswith("/wiki/File:"):
            full = urljoin("https://commons.wikimedia.org", path)
            if full not in candidates:
                candidates.append(full)
    return candidates[:6]


def _cc0_photo(doc: BeautifulSoup, page: str) -> tuple[str, dict] | None:
    # A CC0 badge on this exact file description page is required.
    licenses = [
        a.get("href", "") for a in doc.select("a[href]")
        if re.search(r"creativecommons\.org/publicdomain/zero/1\.0", str(a.get("href", "")), re.I)
    ]
    if not licenses:
        return None
    image_meta = doc.find("meta", attrs={"property": "og:image"})
    image_url = image_meta.get("content", "") if image_meta else ""
    parsed = urlparse(image_url)
    if parsed.scheme != "https" or parsed.hostname != "upload.wikimedia.org":
        return None
    if not re.search(r"\.(jpe?g|png|webp)(?:\?|$)", image_url, flags=re.I):
        return None
    title_tag = doc.select_one("#firstHeading") or doc.find("title")
    title = title_tag.get_text(" ",strip=True) if title_tag else "Commons file"
    return image_url, {
        "creator": "Zobacz informacje o autorze na stronie pliku Wikimedia Commons",
        "url": page,
        "license": "CC0 1.0",
        "title": title,
        "license_url": urljoin(page, licenses[0]),
    }


def _download(url: str, target: Path) -> None:
    with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True,
                      timeout=(7, 24), allow_redirects=True) as res:
        res.raise_for_status()
        parsed = urlparse(res.url)
        if parsed.scheme != "https" or parsed.hostname != "upload.wikimedia.org":
            raise ValueError("Invalid image redirect")
        if int(res.headers.get("Content-Length", "0") or "0") > MAX_DOWNLOAD:
            raise ValueError("Image too large")
        received = 0
        with target.open("wb") as out:
            for chunk in res.iter_content(131072):
                received += len(chunk)
                if received > MAX_DOWNLOAD:
                    raise ValueError("Image too large")
                out.write(chunk)
        if received < 1000:
            raise ValueError("Image too small")


def search_commons_image(query: str, work: Path, index: int,
                         seen: set[str]) -> tuple[Path, dict] | None:
    """Search human-readable HTML on Commons; no external API endpoints used."""
    keywords = " ".join(query.split()[:7])[:100]
    if not keywords:
        return None
    url = ("https://commons.wikimedia.org/w/index.php?title=Special:Search&"
           "ns6=1&fulltext=1&search=" + quote_plus(keywords))
    doc = _html(url)
    for page in _file_pages(doc):
        if page in seen:
            continue
        try:
            result = _cc0_photo(_html(page), page)
            if not result:
                continue
            image_url, info = result
            suffix = Path(urlparse(image_url).path).suffix.lower()
            destination = work / f"commons_{index}{suffix}"
            _download(image_url, destination)
            seen.add(page)
            return destination, info
        except (requests.RequestException, OSError, ValueError):
            continue
    return None
