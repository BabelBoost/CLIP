from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: list[dict[str, Any]] = field(default_factory=list)

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
    hook_score: float
    emotion_score: float
    comment_potential: float
    retention_score: float
    share_potential: float
    context_dependency: float
    quality_label: str
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
    hook_variants: list[dict[str, Any]] = field(default_factory=list)
    selected_hook_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
