from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .analyzer import clean_text, format_time
from .models import ClipCandidate


CRITERIA_LABELS = {
    "strong_statement": "Mocna / zaskakująca wypowiedź",
    "emotion": "Emocje",
    "hook_sentence": "Zdanie działające jako hook",
    "contradiction_absurd": "Sprzeczność / absurd / pomyłka",
    "strong_answer": "Mocna odpowiedź na pytanie",
    "standalone_context": "Zrozumiałe bez pełnego kontekstu",
    "comment_potential": "Potencjał komentarzy i dyskusji",
    "really_said": "Potencjał: Czy naprawdę to powiedział?",
    "cold_open": "Możliwość startu od najmocniejszego zdania",
    "tone_topic_shift": "Nagła zmiana tonu / emocji / tematu",
}

CONFLICT_MARKERS = {
    "absurd", "bzdur", "skandal", "kłam", "fałsz", "nieprawda", "sprzecz",
    "pomył", "błąd", "atak", "oskarż", "bez sensu", "nigdy", "zawsze",
}
SURPRISE_MARKERS = {
    "naprawdę", "serio", "nagle", "okazuje się", "tymczasem", "jednak", "ale",
    "szok", "niewiarygod", "niemożliw", "co?!", "wow",
}
QUESTION_MARKERS = {"czy", "dlaczego", "jak", "co", "kto", "po co", "ile", "gdzie", "kiedy"}
SHIFT_MARKERS = {
    "ale", "jednak", "tymczasem", "nagle", "po chwili", "i wtedy", "a potem",
    "okazuje się", "z drugiej strony", "natomiast", "mimo to", "właśnie wtedy",
}
ANSWER_MARKERS = {
    "tak", "nie", "dlatego", "ponieważ", "bo", "problem polega", "odpowiedź brzmi",
    "prawda jest", "fakt jest", "moim zdaniem", "uważam",
}


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _hits(text: str, markers: set[str]) -> int:
    low = text.lower()
    return sum(1 for marker in markers if marker in low)


def _sentence_count(text: str) -> int:
    parts = re.split(r"(?<=[.!?])\s+|\n+", clean_text(text))
    return len([p for p in parts if len(p.strip()) >= 5])


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def _question_present(text: str) -> bool:
    low = text.lower()
    if "?" in text:
        return True
    words = re.findall(r"\w+", low, flags=re.UNICODE)
    return bool(words and words[0] in QUESTION_MARKERS)


def _short_quote_bonus(quote: str) -> float:
    words = _word_count(quote)
    if 5 <= words <= 16:
        return 18.0
    if 17 <= words <= 24:
        return 10.0
    if words > 32:
        return -10.0
    return 4.0


@dataclass
class ClipEvaluation:
    rank: int
    overall_score: float
    criteria: dict[str, float]
    clip: ClipCandidate

    def to_dict(self) -> dict[str, Any]:
        data = {
            "rank": self.rank,
            "overall_score": self.overall_score,
            "criteria": self.criteria,
            "criteria_labels": CRITERIA_LABELS,
            "clip": self.clip.to_dict(),
        }
        return data


def score_clip(clip: ClipCandidate) -> dict[str, float]:
    text = clean_text(clip.text)
    low = text.lower()
    conflict_hits = _hits(text, CONFLICT_MARKERS)
    surprise_hits = _hits(text, SURPRISE_MARKERS)
    shift_hits = _hits(text, SHIFT_MARKERS)
    answer_hits = _hits(text, ANSWER_MARKERS)
    sentence_count = _sentence_count(text)
    question = _question_present(text)
    independence = 100.0 - clip.context_dependency

    strong_statement = _clamp(
        clip.hook_score * 0.46
        + clip.emotion_score * 0.26
        + min(24.0, (conflict_hits + surprise_hits) * 6.0)
        + _short_quote_bonus(clip.quote) * 0.35
    )

    emotion = _clamp(clip.emotion_score)
    hook_sentence = _clamp(clip.hook_score)

    contradiction_absurd = _clamp(
        12.0
        + min(54.0, conflict_hits * 13.0)
        + min(20.0, shift_hits * 5.0)
        + (10.0 if "?" in text and "!" in text else 0.0)
    )

    strong_answer = _clamp(
        18.0
        + (28.0 if question else 0.0)
        + min(26.0, answer_hits * 8.0)
        + clip.hook_score * 0.22
        + (8.0 if sentence_count >= 2 else 0.0)
    )

    standalone_context = _clamp(independence)
    comment_potential = _clamp(clip.comment_potential)

    really_said = _clamp(
        clip.hook_score * 0.38
        + clip.emotion_score * 0.26
        + clip.comment_potential * 0.18
        + min(18.0, (conflict_hits + surprise_hits) * 4.5)
        + _short_quote_bonus(clip.quote) * 0.35
    )

    cold_open = _clamp(
        clip.hook_score * 0.55
        + independence * 0.32
        + clip.retention_score * 0.13
        + min(10.0, surprise_hits * 2.5)
    )

    tone_topic_shift = _clamp(
        16.0
        + min(48.0, shift_hits * 12.0)
        + min(18.0, surprise_hits * 4.5)
        + (10.0 if sentence_count >= 3 else 0.0)
        + (8.0 if "?" in text and "!" in text else 0.0)
    )

    return {
        "strong_statement": strong_statement,
        "emotion": emotion,
        "hook_sentence": hook_sentence,
        "contradiction_absurd": contradiction_absurd,
        "strong_answer": strong_answer,
        "standalone_context": standalone_context,
        "comment_potential": comment_potential,
        "really_said": really_said,
        "cold_open": cold_open,
        "tone_topic_shift": tone_topic_shift,
    }


def evaluate_candidates(candidates: list[ClipCandidate], limit: int = 10) -> list[ClipEvaluation]:
    scored: list[tuple[float, ClipCandidate, dict[str, float]]] = []
    for clip in candidates:
        criteria = score_clip(clip)
        overall = _clamp(sum(criteria.values()) / len(criteria))
        scored.append((overall, clip, criteria))

    scored.sort(
        key=lambda item: (
            -item[0],
            -item[1].hook_score,
            -item[1].comment_potential,
            item[1].context_dependency,
            item[1].start,
        )
    )

    result: list[ClipEvaluation] = []
    for idx, (overall, clip, criteria) in enumerate(scored[: max(1, limit)], start=1):
        result.append(ClipEvaluation(rank=idx, overall_score=overall, criteria=criteria, clip=clip))
    return result


def render_evaluation_markdown(evaluations: list[ClipEvaluation]) -> str:
    if not evaluations:
        return "# Brak fragmentów do oceny\n"

    lines = [
        "# Viral Video Evaluator",
        "",
        "Analiza całego materiału i ranking fragmentów pod TikTok, Reels i YouTube Shorts.",
        "",
    ]

    for item in evaluations:
        clip = item.clip
        lines.extend([
            f"## NUMER KLIPU {item.rank}",
            "",
            f"**TIMECODE START:** {format_time(clip.start)}",
            "",
            f"**TIMECODE KONIEC:** {format_time(clip.end)}",
            "",
            f"**DŁUGOŚĆ:** {clip.duration:.1f} sekundy",
            "",
            f"**REKOMENDOWANA WERSJA:** {clip.suggested_length} sekund",
            "",
            f"**CYTAT / NAJMOCNIEJSZE ZDANIE:** {clip.quote}",
            "",
            f"**HOOK NA PIERWSZE 3 SEKUNDY:** {clip.hook}",
            "",
            f"**TEKST NA EKRAN:** {clip.screen_text}",
            "",
            f"**OCENA VIRAL:** {item.overall_score:.0f}/100",
            "",
            "### Ocena według 10 kryteriów",
            "",
        ])
        for key, label in CRITERIA_LABELS.items():
            lines.append(f"- {label}: {item.criteria[key]:.0f}/100")
        lines.extend([
            "",
            f"**DLACZEGO:** {clip.reason}",
            "",
            f"**SUGEROWANE CIĘCIE:** {clip.cut_before} {clip.cut_after}",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)
