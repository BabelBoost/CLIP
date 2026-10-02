from __future__ import annotations

import json
import re
from dataclasses import replace

import requests

from .models import ClipCandidate, TranscriptSegment

EMOTION_WORDS = {
    "konflikt": {"ale", "jednak", "kłam", "bzdur", "absurd", "spór", "atak", "oskarż", "winny", "problem", "nieprawda", "fałsz", "nigdy"},
    "szok": {"szok", "niewiarygod", "niemożliw", "skandal", "masakra", "serio", "naprawdę", "co?!", "wow"},
    "humor": {"śmiesz", "haha", "żart", "zabaw", "komedi", "paradoks"},
    "ciekawość": {"dlaczego", "jak", "co", "czy", "sekret", "prawda", "wiesz", "wyobraź", "okazuje"},
    "niedowierzanie": {"naprawdę", "serio", "nie wierzę", "niemożliwe", "co ty", "bez jaj"},
}
INTENSIFIERS = {
    "bardzo", "totalnie", "absolutnie", "kompletnie", "nigdy", "zawsze", "najgorszy", "najlepszy",
    "skandal", "absurd", "bzdura", "szok", "dramat", "hit", "prawda", "kłamstwo", "milion", "miliard",
}
SURPRISE_MARKERS = {"ale", "jednak", "tymczasem", "nagle", "okazuje się", "właśnie", "serio", "naprawdę"}
QUESTION_MARKERS = {"czy", "dlaczego", "jak", "co", "kto", "po co", "ile"}
OPEN_LOOP_MARKERS = {"za chwilę", "problem w tym", "i wtedy", "ale to nie wszystko", "okazuje się", "najlepsze jest", "najgorsze jest"}
SHARE_MARKERS = {
    "musisz", "warto", "sprawdź", "zobacz", "uważaj", "zapamiętaj", "ważne", "przydat",
    "błąd", "porada", "sposób", "dlaczego", "jak zrobić", "nie rób", "każdy powinien",
}
CONTEXT_MARKERS = {
    "to", "tego", "tym", "ten", "ta", "tam", "tutaj", "wtedy", "wcześniej", "później", "on", "ona", "oni",
    "jego", "jej", "ich", "tak", "takie", "taki", "właśnie", "dalej", "znowu", "również", "natomiast",
}
PUBLIC_AFFAIRS_MARKERS = {
    "rząd", "premier", "prezydent", "minister", "sejm", "senat", "partia", "wybory", "poseł", "polityk",
    "ustawa", "budżet", "podat", "koalicja", "opozycja", "unia europejska", "nato", "kandydat",
}
STOPWORDS = {
    "i", "oraz", "a", "ale", "że", "to", "jest", "są", "był", "była", "było", "w", "na", "do", "z", "za",
    "po", "od", "dla", "się", "nie", "tak", "jak", "co", "czy", "ten", "ta", "te", "o", "u", "już",
}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def format_time(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return round(max(low, min(high, value)), 1)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", clean_text(text))
    return [p.strip(" -") for p in parts if len(p.strip()) >= 5]


def _sentence_strength(sentence: str) -> float:
    low = sentence.lower()
    words = re.findall(r"\w+", low, flags=re.UNICODE)
    score = min(2.0, sentence.count("!") * 0.9 + sentence.count("?") * 0.6)
    score += sum(0.7 for w in INTENSIFIERS if w in low)
    score += sum(0.45 for w in SURPRISE_MARKERS if w in low)
    if 5 <= len(words) <= 22:
        score += 1.2
    if low.startswith(tuple(QUESTION_MARKERS)):
        score += 0.8
    if re.search(r"\b\d+[\d.,%]*\b", sentence):
        score += 0.45
    return score


def _strongest_sentence(text: str) -> str:
    sentences = _sentences(text) or [clean_text(text)]
    return max(sentences, key=_sentence_strength)


def _emotion(text: str) -> str:
    low = text.lower()
    scores = {name: sum(1 for marker in markers if marker in low) for name, markers in EMOTION_WORDS.items()}
    name, value = max(scores.items(), key=lambda item: item[1])
    return name if value else "ciekawość"


def _topic(text: str) -> str:
    words = [w.lower() for w in re.findall(r"[A-Za-zÀ-ž0-9]+", text) if len(w) > 3]
    counts: dict[str, int] = {}
    for w in words:
        if w in STOPWORDS:
            continue
        counts[w] = counts.get(w, 0) + 1
    top = sorted(counts, key=lambda w: (-counts[w], -len(w)))[:3]
    return " / ".join(top) if top else "mocna wypowiedź"


def _auto_public_affairs(text: str) -> bool:
    low = text.lower()
    return sum(1 for marker in PUBLIC_AFFAIRS_MARKERS if marker in low) >= 2


def _hook_score(text: str) -> float:
    quote = _strongest_sentence(text)
    low = quote.lower()
    words = re.findall(r"\w+", quote, flags=re.UNICODE)
    score = 28 + _sentence_strength(quote) * 10
    if "?" in quote:
        score += 9
    if "!" in quote:
        score += 7
    if re.search(r"\b\d+[\d.,%]*\b", quote):
        score += 7
    if any(marker in low for marker in SURPRISE_MARKERS):
        score += 9
    if 5 <= len(words) <= 16:
        score += 8
    if len(words) > 28:
        score -= 14
    return _clamp(score)


def _emotion_score(text: str) -> float:
    low = text.lower()
    marker_hits = sum(sum(1 for marker in markers if marker in low) for markers in EMOTION_WORDS.values())
    intensifiers = sum(1 for marker in INTENSIFIERS if marker in low)
    punctuation = min(18, text.count("!") * 8 + text.count("?") * 4)
    return _clamp(18 + marker_hits * 9 + intensifiers * 5 + punctuation)


def _comment_potential(text: str) -> float:
    low = text.lower()
    score = 20.0
    if "?" in text:
        score += 25
    score += min(24, sum(1 for marker in EMOTION_WORDS["konflikt"] if marker in low) * 6)
    score += min(14, sum(1 for marker in QUESTION_MARKERS if re.search(rf"\b{re.escape(marker)}\b", low)) * 4)
    if any(marker in low for marker in {"nigdy", "zawsze", "najlepszy", "najgorszy", "prawda", "kłamstwo"}):
        score += 10
    if 10 <= len(text.split()) <= 75:
        score += 7
    return _clamp(score)


def _context_dependency(text: str) -> float:
    low = clean_text(text).lower()
    words = re.findall(r"\w+", low, flags=re.UNICODE)
    if not words:
        return 100.0
    first = words[:6]
    hits = sum(1 for word in words if word in CONTEXT_MARKERS)
    score = 8 + min(45, hits * 5)
    if first and first[0] in {"ale", "więc", "bo", "i", "natomiast", "wtedy", "dlatego"}:
        score += 20
    if any(word in CONTEXT_MARKERS for word in first):
        score += 12
    if len(words) < 12:
        score += 18
    if len(_sentences(text)) >= 2:
        score -= 8
    if re.search(r"\b[A-ZŁŚŻŹĆŃÓ][a-ząćęłńóśźż]{3,}\b", text):
        score -= 8
    return _clamp(score)


def _retention_score(text: str, duration: float) -> float:
    low = text.lower()
    words = re.findall(r"\w+", low, flags=re.UNICODE)
    words_per_second = len(words) / max(duration, 1.0)
    score = 24.0
    if 1.6 <= words_per_second <= 3.6:
        score += 18
    elif 1.1 <= words_per_second <= 4.3:
        score += 10
    score += min(18, sum(1 for marker in SURPRISE_MARKERS if marker in low) * 6)
    score += min(16, sum(1 for marker in OPEN_LOOP_MARKERS if marker in low) * 8)
    if "?" in text:
        score += 8
    if 12 <= duration <= 36:
        score += 15
    elif duration <= 60:
        score += 8
    if len(_sentences(text)) >= 2:
        score += 7
    return _clamp(score)


def _share_potential(text: str, context_dependency: float) -> float:
    low = text.lower()
    words = re.findall(r"\w+", low, flags=re.UNICODE)
    surprise_hits = sum(1 for marker in SURPRISE_MARKERS if marker in low)
    emotion_hits = sum(sum(1 for marker in markers if marker in low) for markers in EMOTION_WORDS.values())
    utility_hits = sum(1 for marker in SHARE_MARKERS if marker in low)

    score = 18.0
    score += min(24, surprise_hits * 8)
    score += min(18, emotion_hits * 4)
    score += min(20, utility_hits * 7)
    if re.search(r"\b\d+[\d.,%]*\b", text):
        score += 8
    if 8 <= len(words) <= 90:
        score += 8
    if "!" in text:
        score += 5
    if context_dependency <= 35:
        score += 12
    elif context_dependency >= 65:
        score -= 12
    return _clamp(score)


def _quality_label(viral_score: float) -> str:
    if viral_score >= 85:
        return "PUBLIKUJ NAJPIERW"
    if viral_score >= 70:
        return "DOBRY MATERIAŁ"
    if viral_score >= 55:
        return "POPRAW HOOK LUB SKRÓĆ"
    return "ODRZUĆ / PRZEMONTUJ"


def _score(
    text: str,
    duration: float,
    hook_override: float | None = None,
) -> tuple[float, float, float, float, float, float, float]:
    hook = _hook_score(text) if hook_override is None else _clamp(hook_override)
    emotion = _emotion_score(text)
    comments = _comment_potential(text)
    retention = _retention_score(text, duration)
    context = _context_dependency(text)
    share = _share_potential(text, context)

    # Pięć głównych sygnałów ma równą wagę. Context Dependency pozostaje
    # osobnym sygnałem jakości i pomaga ocenić, czy klip działa samodzielnie.
    viral = (hook + retention + emotion + comments + share) / 5
    return _clamp(viral), hook, emotion, comments, retention, share, context


def _truncate_words(text: str, max_words: int) -> str:
    words = clean_text(text).split()
    return " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")


def _hook_variant_score(hook: str, source_text: str, public_affairs: bool) -> float:
    hook = clean_text(hook)
    low = hook.lower()
    words = re.findall(r"\w+", low, flags=re.UNICODE)
    source_words = {
        w for w in re.findall(r"\w+", source_text.lower(), flags=re.UNICODE)
        if len(w) > 3 and w not in STOPWORDS
    }
    hook_words = {
        w for w in words
        if len(w) > 3 and w not in STOPWORDS
    }
    overlap = len(source_words & hook_words) / max(1, len(hook_words))

    score = 20.0 + _sentence_strength(hook) * 7
    if 5 <= len(words) <= 14:
        score += 25
    elif 15 <= len(words) <= 18:
        score += 14
    elif len(words) > 22:
        score -= 18
    if "?" in hook:
        score += 9
    if any(marker in low for marker in SURPRISE_MARKERS):
        score += 7
    if re.search(r"\b\d+[\d.,%]*\b", hook):
        score += 6
    score += min(24.0, overlap * 24.0)

    if public_affairs:
        # W publicystyce premiujemy zgodność ze źródłem bardziej niż emocjonalny framing.
        score += min(18.0, overlap * 18.0)
        if overlap < 0.35:
            score -= 20
        if any(marker in low for marker in {"szok", "skandal", "masakra", "bezczel", "kompromit"}):
            score -= 18
    return _clamp(score)


def _hook_variants(text: str, public_affairs: bool) -> list[dict]:
    quote = _strongest_sentence(text).strip()
    direct = _truncate_words(quote, 14)

    if public_affairs:
        raw = [
            ("cytat", direct),
            ("kontekst", _truncate_words(f"Najważniejszy fragment wypowiedzi: {quote}", 16)),
            ("analiza", _truncate_words(f"Co dokładnie wynika z tej wypowiedzi? {quote}", 16)),
        ]
    else:
        low = quote.lower()
        curiosity = (
            direct
            if "?" in quote or any(low.startswith(q) for q in QUESTION_MARKERS)
            else _truncate_words(f"Co wydarzyło się w tym momencie? {quote}", 16)
        )
        tension = (
            _truncate_words(f"Tu zaczyna się spór: {quote}", 16)
            if any(m in low for m in EMOTION_WORDS["konflikt"])
            else _truncate_words(f"Tego fragmentu nie da się przeoczyć: {quote}", 16)
        )
        raw = [
            ("cytat", direct),
            ("ciekawość", curiosity),
            ("napięcie", tension),
        ]

    variants: list[dict] = []
    seen: set[str] = set()
    for kind, value in raw:
        value = clean_text(value)
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        variants.append({
            "kind": kind,
            "text": value,
            "score": _hook_variant_score(value, text, public_affairs),
        })

    fallbacks = [
        ("alternatywa", _truncate_words(f"Najmocniejszy moment: {quote}", 16)),
        ("pytanie", _truncate_words(f"Co jest tu najważniejsze? {quote}", 16)),
    ]
    for kind, value in fallbacks:
        if len(variants) >= 3:
            break
        value = clean_text(value)
        if value.lower() in seen:
            continue
        seen.add(value.lower())
        variants.append({
            "kind": kind,
            "text": value,
            "score": _hook_variant_score(value, text, public_affairs),
        })

    variants.sort(key=lambda item: (-float(item["score"]), len(str(item["text"]))))
    return variants[:3]


def _screen_text(text: str) -> str:
    strongest = _strongest_sentence(text)
    words = strongest.split()
    if len(words) <= 8:
        return strongest
    return _truncate_words(strongest, 8)


def _suggested_length(duration: float, hook_score: float, context_dependency: float, retention_score: float) -> int:
    if hook_score >= 76 and context_dependency <= 38 and duration <= 28:
        return 15
    if context_dependency >= 65 and duration >= 42:
        return 60
    if retention_score >= 62 or duration >= 22:
        return 30
    return 15


def _subtitles_for_window(segments: list[TranscriptSegment], start: float, end: float) -> list[dict]:
    out = []
    for seg in segments:
        if seg.end <= start or seg.start >= end:
            continue
        rel_start = max(0.0, seg.start - start)
        rel_end = min(end, seg.end) - start
        out.append({"start": round(rel_start, 2), "end": round(max(rel_start + 0.15, rel_end), 2), "text": clean_text(seg.text)})
    return out


def _reason(text: str, duration: float, public_affairs: bool, scores: tuple[float, float, float, float, float, float, float]) -> str:
    viral, hook, emotion, comments, retention, share, context = scores
    features: list[str] = []
    if hook >= 70:
        features.append("mocne otwarcie")
    if emotion >= 65:
        features.append("wyraźna emocja")
    if comments >= 65:
        features.append("wysoki potencjał komentarzy")
    if retention >= 65:
        features.append("dobry rytm utrzymania uwagi")
    if share >= 65:
        features.append("wysoki potencjał udostępnień")
    if context <= 35:
        features.append("fragment działa bez dużego kontekstu")
    elif context >= 65:
        features.append("fragment wymaga krótkiego wprowadzenia")
    if not features:
        features.append("czytelna wypowiedź z możliwą puentą")
    suffix = " W trybie publicystycznym hook zachowuje sens źródłowej wypowiedzi." if public_affairs else ""
    return f"Viral Score {viral:.0f}/100. " + ", ".join(features[:3]).capitalize() + "." + suffix


def _hashtags(text: str, public_affairs: bool) -> list[str]:
    topic_words = [w for w in _topic(text).split(" / ") if w]
    base = ["#publicystyka", "#wiadomosci", "#dyskusja"] if public_affairs else ["#tiktok", "#shorts", "#reels"]
    tags = base + ["#" + re.sub(r"\W+", "", w.lower()) for w in topic_words]
    out = []
    for tag in tags:
        if tag not in out and len(tag) > 1:
            out.append(tag)
    return out[:7]


def _description(text: str, public_affairs: bool) -> str:
    quote = _truncate_words(_strongest_sentence(text), 15)
    if public_affairs:
        return f"Fragment wypowiedzi: „{quote}”. Oceń argument na podstawie pełnego kontekstu."
    return f"Najmocniejszy moment: „{quote}”. Jak Ty to odbierasz?"


def _build_candidate(window: list[TranscriptSegment], all_segments: list[TranscriptSegment], content_mode: str) -> ClipCandidate:
    start = window[0].start
    end = window[-1].end
    duration = end - start
    text = clean_text(" ".join(s.text for s in window))
    public_affairs = content_mode == "public_affairs" or (content_mode == "auto" and _auto_public_affairs(text))
    quote = _strongest_sentence(text)
    hook_variants = _hook_variants(text, public_affairs)
    best_hook = hook_variants[0] if hook_variants else {
        "kind": "cytat",
        "text": _truncate_words(quote, 14),
        "score": _hook_score(text),
    }
    scores = _score(text, duration, hook_override=float(best_hook["score"]))
    viral_score, hook_score, emotion_score, comment_potential, retention_score, share_potential, context_dependency = scores
    suggested = _suggested_length(duration, hook_score, context_dependency, retention_score)
    return ClipCandidate(
        rank=0,
        start=start,
        end=end,
        duration=duration,
        quote=quote,
        hook=str(best_hook["text"]),
        screen_text=_screen_text(text),
        reason=_reason(text, duration, public_affairs, scores),
        viral_score=viral_score,
        hook_score=hook_score,
        emotion_score=emotion_score,
        comment_potential=comment_potential,
        retention_score=retention_score,
        share_potential=share_potential,
        context_dependency=context_dependency,
        quality_label=_quality_label(viral_score),
        emotion=_emotion(text),
        suggested_length=suggested,
        cut_before=f"Usuń wszystko przed {format_time(start)}. Zacznij maksymalnie 0,3 s przed pierwszym słowem.",
        cut_after=f"Zakończ przy {format_time(end)}. Usuń dalsze dopowiedzenia bez nowej puenty.",
        subtitles=_subtitles_for_window(all_segments, start, end),
        tiktok_description=_description(text, public_affairs),
        hashtags=_hashtags(text, public_affairs),
        cta="Jak oceniasz ten argument na podstawie pełnej wypowiedzi?" if public_affairs else "Co o tym myślisz?",
        topic=_topic(text),
        text=text,
        hook_variants=hook_variants,
        selected_hook_score=float(best_hook["score"]),
    )


def _overlap_ratio(a: ClipCandidate, b: ClipCandidate) -> float:
    inter = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    return 0.0 if inter <= 0 else inter / min(a.duration, b.duration)


def analyze_segments(
    segments: list[TranscriptSegment],
    top_n: int = 10,
    content_mode: str = "auto",
    min_viral_score: float = 55.0,
    include_weak: bool = False,
) -> list[ClipCandidate]:
    if not segments:
        return []
    candidates: list[ClipCandidate] = []
    targets = (15, 30, 60)
    n = len(segments)
    for i in range(n):
        for target in targets:
            window: list[TranscriptSegment] = []
            for j in range(i, n):
                window.append(segments[j])
                duration = window[-1].end - window[0].start
                if duration >= target * 0.72:
                    if duration <= min(64, target * 1.28):
                        text = clean_text(" ".join(s.text for s in window))
                        if len(text.split()) >= 10:
                            candidates.append(_build_candidate(window, segments, content_mode))
                    break
                if duration > 64:
                    break
    candidates.sort(
        key=lambda c: (
            -c.viral_score,
            -c.share_potential,
            -c.retention_score,
            c.context_dependency,
            -c.hook_score,
            c.start,
        )
    )
    selected: list[ClipCandidate] = []
    for cand in candidates:
        if not include_weak and cand.viral_score < min_viral_score:
            continue
        if any(_overlap_ratio(cand, existing) > 0.62 for existing in selected):
            continue
        selected.append(cand)
        if len(selected) >= top_n:
            break
    return [replace(c, rank=i + 1) for i, c in enumerate(selected)]


def enrich_with_ollama(candidates: list[ClipCandidate], model: str = "qwen3:8b", endpoint: str = "http://localhost:11434/api/generate", content_mode: str = "auto") -> list[ClipCandidate]:
    if not candidates:
        return candidates
    updated: list[ClipCandidate] = []
    for cand in candidates:
        public_affairs = content_mode == "public_affairs" or (content_mode == "auto" and _auto_public_affairs(cand.text))
        safety = (
            "Materiał może być polityczny lub publicystyczny. Zachowaj neutralność, nie dopisuj ocen politycznych, nie zmieniaj znaczenia i oprzyj hook na źródłowej wypowiedzi."
            if public_affairs else "Nie wymyślaj faktów. Hook ma być mocny, ale zgodny z treścią."
        )
        prompt = f"""Jesteś montażystą krótkich form. {safety}
Zwróć WYŁĄCZNIE poprawny JSON z polami: screen_text, reason, emotion, description, hashtags, cta.
Hashtags ma być tablicą 5-7 elementów. screen_text maks. 10 słów. description maks. 2 krótkie zdania.
Nie zmieniaj wybranego hooka. Viral Clip Studio 3.3 wybiera go osobnym scoringiem.
Tekst fragmentu:\n{cand.text}\nNajmocniejszy cytat:\n{cand.quote}
"""
        try:
            r = requests.post(endpoint, json={"model": model, "prompt": prompt, "stream": False}, timeout=90)
            r.raise_for_status()
            raw = r.json().get("response", "").strip()
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if not match:
                raise ValueError("Brak JSON w odpowiedzi Ollama")
            data = json.loads(match.group(0))
            tags = data.get("hashtags") if isinstance(data.get("hashtags"), list) else cand.hashtags
            updated.append(replace(
                cand,
                screen_text=_truncate_words(str(data.get("screen_text", cand.screen_text)), 10),
                reason=clean_text(str(data.get("reason", cand.reason)))[:420],
                emotion=clean_text(str(data.get("emotion", cand.emotion)))[:40],
                tiktok_description=clean_text(str(data.get("description", cand.tiktok_description)))[:300],
                hashtags=[str(x) for x in tags][:7],
                cta=clean_text(str(data.get("cta", cand.cta)))[:160],
            ))
        except Exception:
            updated.append(cand)
    return updated
