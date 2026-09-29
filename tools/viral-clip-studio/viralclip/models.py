from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClipCandidate:
    rank: int
    start: float
    end: float
    duration: float
    quote: str
    hook: str
    screen_text: str
    reason: str
    viral_score: float
    emotion: str
    suggested_length: int
    cut_before: str
    cut_after: str
    subtitles: list[dict[str, Any]]
    tiktok_description: str
    hashtags: list[str]
    cta: str
    topic: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
