import re
from dataclasses import dataclass

from .speech import SpeechSegment, transcript_for_window


@dataclass
class ViralScore:
    total: float
    hook: float
    emotion: float
    comment_potential: float
    context_dependency: float
    pace: float
    speech: float
    visual: float
    punch: float
    words_per_second: float
    eligible: bool
    reasons: list[str]
    reject_reasons: list[str]


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

EMOTION_PATTERNS = [
    r"\bszok\b", r"\bszokujące\b", r"\babsurd\b", r"\bskandal\b", r"\bdramat\b",
    r"\bśmieszne\b", r"\bśmiech\b", r"\bnie wierzę\b", r"\bniemożliwe\b",
    r"\bwkurz\w*\b", r"\bzły\b", r"\bzłość\b", r"\boburz\w*\b", r"\bstrach\b",
    r"\bnapię\w*\b", r"\bzaskocz\w*\b", r"\bniedowierz\w*\b", r"\bserio\b",
    r"\bshock\w*\b", r"\bunbelievable\b", r"\bimpossible\b", r"\babsurd\b",
    r"\bscandal\b", r"\bangry\b", r"\bfurious\b", r"\bafraid\b", r"\bfear\b",
    r"\bsurpris\w*\b", r"\bseriously\b", r"\bno way\b", r"\bwow\b",
]

COMMENT_PATTERNS = [
    r"\bzgadzasz\b", r"\bzgadzacie\b", r"\bco sądzisz\b", r"\bco sądzicie\b",
    r"\bco myślisz\b", r"\bco myślicie\b", r"\bkto ma rację\b", r"\bczy naprawdę\b",
    r"\bpowinien\b", r"\bpowinna\b", r"\bpowinni\b", r"\bkażdy\b", r"\bnikt\b",
    r"\bzawsze\b", r"\bnigdy\b", r"\bwiększość\b", r"\bkontrowers\w*\b",
    r"\bdo you agree\b", r"\bwhat do you think\b", r"\bwho is right\b",
    r"\bshould\b", r"\beveryone\b", r"\bnobody\b", r"\balways\b", r"\bnever\b",
    r"\bcontrovers\w*\b", r"\breally\b",
]

CONTEXT_OPENING_PATTERNS = [
    r"^(i|a|ale|więc|bo|dlatego|natomiast|jednak|no i|wtedy|potem)\b",
    r"^(and|but|so|because|therefore|however|then|also|anyway)\b",
    r"^(on|ona|oni|one|jego|jej|ich|to|tego|temu|tam|tutaj)\b",
    r"^(he|she|they|it|this|that|these|those|there)\b",
]

CONTEXT_REFERENCE_PATTERNS = [
    r"\bjak mówiłem\b", r"\bjak mówiłam\b", r"\bwspominałem\b", r"\bwspominałam\b",
    r"\bwcześniej\b", r"\bprzed chwilą\b", r"\bjak już\b", r"\bten człowiek\b",
    r"\bta osoba\b", r"\bw tej sprawie\b", r"\bw tym przypadku\b",
    r"\bas i said\b", r"\bas i mentioned\b", r"\bearlier\b", r"\bpreviously\b",
    r"\bthis person\b", r"\bthat person\b", r"\bin this case\b", r"\babout that\b",
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


def emotion_score(text: str) -> tuple[float, list[str]]:
    sample = (text or "").strip()
    if not sample:
        return 0.0, []

    pattern_value, matches = pattern_score(sample, EMOTION_PATTERNS, cap=3)
    score = pattern_value * 0.78
    reasons = []

    if matches:
        reasons.append("emocjonalne słownictwo")
    if "!" in sample:
        score += 0.10
        reasons.append("mocny ton")
    if "?!" in sample or "!?" in sample:
        score += 0.08
        reasons.append("niedowierzanie")
    if re.search(r"\b(nie|never|no)\b.{0,35}\b(wierzę|believe|way)\b", sample, re.IGNORECASE):
        score += 0.12
        reasons.append("reakcja niedowierzania")

    return clamp(score), reasons


def comment_potential_score(text: str, *, emotion: float = 0.0, punch: float = 0.0) -> tuple[float, list[str]]:
    sample = (text or "").strip()
    if not sample:
        return 0.0, []

    pattern_value, matches = pattern_score(sample, COMMENT_PATTERNS, cap=3)
    score = pattern_value * 0.58 + clamp(emotion) * 0.17 + clamp(punch) * 0.15
    reasons = []

    if matches:
        reasons.append("teza prowokująca odpowiedź")
    if "?" in sample:
        score += 0.16
        reasons.append("naturalne pytanie do widza")
    if re.search(r"\b\d+(?:[.,]\d+)?\b", sample):
        score += 0.07
        reasons.append("konkret do dyskusji")
    if re.search(r"\b(zawsze|nigdy|każdy|nikt|always|never|everyone|nobody)\b", sample, re.IGNORECASE):
        score += 0.08
        reasons.append("mocne uogólnienie")

    return clamp(score), reasons


def context_dependency_score(text: str) -> tuple[float, list[str]]:
    sample = (text or "").strip()
    if not sample:
        return 1.0, ["brak samodzielnej wypowiedzi"]

    lower = sample.lower()
    opening = lower[:180]
    score = 0.0
    reasons = []

    if any(re.search(pattern, opening, re.IGNORECASE) for pattern in CONTEXT_OPENING_PATTERNS):
        score += 0.36
        reasons.append("zaczyna się od odwołania do wcześniejszego kontekstu")

    reference_matches = sum(
        1 for pattern in CONTEXT_REFERENCE_PATTERNS
        if re.search(pattern, lower, re.IGNORECASE)
    )
    if reference_matches:
        score += min(0.42, 0.24 + 0.10 * reference_matches)
        reasons.append("odwołuje się do wcześniejszej części rozmowy")

    first_sentence = re.split(r"[.!?]", sample, maxsplit=1)[0].strip()
    first_words = len(first_sentence.split())
    if first_words <= 4:
        score += 0.14
        reasons.append("bardzo krótki początek")

    pronouns = len(re.findall(
        r"\b(on|ona|oni|one|to|tego|tam|he|she|they|it|this|that|there)\b",
        opening,
        flags=re.IGNORECASE,
    ))
    if pronouns >= 3:
        score += 0.16
        reasons.append("dużo niejasnych odniesień")

    hook, _ = hook_score(sample)
    if hook >= 0.55:
        score -= 0.16
    if "?" in first_sentence or re.search(r"\d", first_sentence):
        score -= 0.08

    return clamp(score), reasons


def quality_gate(score: ViralScore) -> tuple[bool, list[str]]:
    reject_reasons = []

    if score.context_dependency >= 0.78:
        reject_reasons.append("za duża zależność od wcześniejszego kontekstu")
    if score.speech < 0.45:
        reject_reasons.append("za mało mowy")
    if score.total < 0.36:
        reject_reasons.append("za niski łączny potencjał")
    if score.hook < 0.15 and score.emotion < 0.20 and score.comment_potential < 0.25:
        reject_reasons.append("brak mocnego hooka, emocji i potencjału komentarzy")

    return not reject_reasons, reject_reasons


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

    hook, hook_reasons = hook_score(text)
    emotion, emotion_reasons = emotion_score(text)
    pace = clamp(pace_score(wps))
    punch, punch_matches = pattern_score(text, PUNCH_PATTERNS, cap=3)
    comments, comment_reasons = comment_potential_score(text, emotion=emotion, punch=punch)
    context_dependency, context_reasons = context_dependency_score(text)

    reasons = hook_reasons + emotion_reasons + comment_reasons
    if punch_matches:
        reasons.append("kontrast lub mocne sformułowanie")
    if wps >= 2.0:
        reasons.append("dynamiczne tempo mowy")
    if speech_ratio >= 0.82:
        reasons.append("mało ciszy")
    if context_dependency <= 0.24:
        reasons.append("fragment zrozumiały bez dużego kontekstu")

    visual = clamp(
        clamp(face_ratio) * 0.40
        + clamp(motion_score) * 0.40
        + clamp(scene_score) * 0.20
    )

    weighted = (
        hook * 0.24
        + emotion * 0.16
        + comments * 0.15
        + pace * 0.14
        + clamp(speech_ratio) * 0.12
        + punch * 0.08
        + visual * 0.11
    )
    total = clamp(weighted - context_dependency * 0.15)

    preliminary = ViralScore(
        total=total,
        hook=hook,
        emotion=emotion,
        comment_potential=comments,
        context_dependency=context_dependency,
        pace=pace,
        speech=clamp(speech_ratio),
        visual=visual,
        punch=punch,
        words_per_second=wps,
        eligible=True,
        reasons=reasons[:8],
        reject_reasons=[],
    )
    eligible, reject_reasons = quality_gate(preliminary)
    preliminary.eligible = eligible
    preliminary.reject_reasons = reject_reasons + context_reasons[:1] if not eligible else []
    return preliminary


def rerank_candidates(
    candidates,
    segments: list[SpeechSegment],
    max_count: int,
    *,
    filter_weak: bool = True,
):
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
        if filter_weak and not viral.eligible:
            continue
        scored.append((viral.total, candidate, viral))

    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[: max(1, int(max_count))]
