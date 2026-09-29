import math
import re
from dataclasses import dataclass

from .speech import SpeechSegment, transcript_for_window


@dataclass
class ViralScore:
    total: float
    hook: float
    pace: float
    speech: float
    visual: float
    punch: float
    words_per_second: float
    reasons: list[str]


HOOK_PATTERNS = [
    r"\bjak\b", r"\bdlaczego\b", r"\bco jeśli\b", r"\buwaga\b", r"\bzobacz\b",
    r"\bnie uwierzysz\b", r"\bnikt ci nie powie\b", r"\boto\b", r"\bsekret\b",
    r"\bhow\b", r"\bwhy\b", r"\bwhat if\b", r"\bwatch\b", r"\bhere'?s\b",
    r"\bthe truth\b", r"\bmost people\b", r"\byou need to know\b",
]

PUNCH_PATTERNS = [
    r"\bale\b", r"\bjednak\b", r"\bproblem\b", r"\bbłąd\b", r"\bprawda\b",
    r"\bwiększość\b", r"\bnigdy\b", r"\bzawsze\b", r"\bważne\b", r"\bserio\b",
    r"\bbut\b", r"\bhowever\b", r"\bmistake\b", r"\btruth\b", r"\bnever\b",
    r"\balways\b", r"\bimportant\b", r"\bactually\b", r"\bmost\b",
]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(max(float(value), low), high)


def words_in_window(segments: list[SpeechSegment], start: float, end: float) -> int:
    count = 0
    for segment in segments:
        if segment.end <= start or segment.start >= end:
            continue
        count += len(re.findall(r"\b\w+[’'-]?\w*\b", segment.text or "", flags=re.UNICODE))
    return count


def pace_score(words_per_second: float) -> float:
    """Reward energetic but still understandable speech, roughly 2–4 words/s."""
    value = max(0.0, float(words_per_second))
    if value <= 0.7:
        return 0.15 * (value / 0.7)
    if value < 2.0:
        return 0.15 + (value - 0.7) / 1.3 * 0.70
    if value <= 4.0:
        return 0.85 + (value - 2.0) / 2.0 * 0.15
    if value <= 5.2:
        return 1.0 - (value - 4.0) / 1.2 * 0.30
    return max(0.25, 0.70 - (value - 5.2) * 0.12)


def pattern_score(text: str, patterns: list[str], cap: int = 3) -> tuple[float, int]:
    lower = (text or "").lower()
    matches = sum(1 for pattern in patterns if re.search(pattern, lower, flags=re.IGNORECASE))
    return clamp(matches / max(1, cap)), matches


def hook_score(text: str) -> tuple[float, list[str]]:
    opening = (text or "").strip()[:220]
    if not opening:
        return 0.0, []

    score, matches = pattern_score(opening, HOOK_PATTERNS, cap=2)
    reasons = []

    if "?" in opening:
        score += 0.22
        reasons.append("pytanie na początku")
    if re.search(r"\d", opening):
        score += 0.18
        reasons.append("konkret/liczba")
    if "!" in opening:
        score += 0.10
        reasons.append("mocna interpunkcja")
    if matches:
        reasons.append("hook językowy")

    first_sentence = re.split(r"[.!?]", opening, maxsplit=1)[0].strip()
    first_words = len(first_sentence.split())
    if 3 <= first_words <= 14:
        score += 0.15
        reasons.append("krótki pierwszy komunikat")

    return clamp(score), reasons


def viral_score_for_window(
    segments: list[SpeechSegment],
    start: float,
    end: float,
    *,
    speech_ratio: float,
    face_ratio: float,
    motion_score: float,
    scene_score: float,
) -> ViralScore:
    duration = max(0.001, float(end) - float(start))
    text = transcript_for_window(segments, start, end, max_chars=1200)
    words = words_in_window(segments, start, end)
    wps = words / duration

    hook, reasons = hook_score(text)
    pace = clamp(pace_score(wps))
    punch, punch_matches = pattern_score(text, PUNCH_PATTERNS, cap=3)

    if punch_matches:
        reasons.append("kontrast lub mocne sformułowanie")
    if wps >= 2.0:
        reasons.append("dynamiczne tempo mowy")
    if speech_ratio >= 0.82:
        reasons.append("mało ciszy")

    visual = clamp(
        clamp(face_ratio) * 0.40
        + clamp(motion_score) * 0.40
        + clamp(scene_score) * 0.20
    )

    total = (
        hook * 0.30
        + pace * 0.22
        + clamp(speech_ratio) * 0.20
        + punch * 0.13
        + visual * 0.15
    )

    return ViralScore(
        total=clamp(total),
        hook=hook,
        pace=pace,
        speech=clamp(speech_ratio),
        visual=visual,
        punch=punch,
        words_per_second=wps,
        reasons=reasons[:5],
    )


def rerank_candidates(candidates, segments: list[SpeechSegment], max_count: int):
    scored = []
    for candidate in candidates:
        viral = viral_score_for_window(
            segments,
            candidate.start,
            candidate.end,
            speech_ratio=candidate.speech_ratio,
            face_ratio=candidate.face_ratio,
            motion_score=candidate.motion_score,
            scene_score=candidate.scene_score,
        )
        scored.append((viral.total, candidate, viral))

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[: max(1, int(max_count))]
