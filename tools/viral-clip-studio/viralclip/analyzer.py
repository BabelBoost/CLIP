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


def _score(text: str, duration: float) -> float:
    low = text.lower()
    words = re.findall(r"\w+", low, flags=re.UNICODE)
    if not words:
        return 1.0
    strength = _sentence_strength(_strongest_sentence(text))
    conflict = sum(0.35 for marker in EMOTION_WORDS["konflikt"] if marker in low)
    curiosity = sum(0.25 for marker in QUESTION_MARKERS if re.search(rf"\b{re.escape(marker)}\b", low))
    surprise = sum(0.3 for marker in SURPRISE_MARKERS if marker in low)
    punctuation = min(1.0, text.count("!") * 0.35 + text.count("?") * 0.25)
    density = min(1.2, len(words) / max(duration, 1.0) / 2.6)
    standalone = 0.8 if len(words) >= 12 else 0.2
    ideal_duration = 0.9 if 14 <= duration <= 36 else 0.5 if duration <= 60 else 0.0
    raw = 2.2 + strength * 0.95 + conflict + curiosity + surprise + punctuation + density + standalone + ideal_duration
    return round(max(1.0, min(10.0, raw)), 1)


def _truncate_words(text: str, max_words: int) -> str:
    words = clean_text(text).split()
    return " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")


def _hook(text: str, public_affairs: bool) -> str:
    quote = _strongest_sentence(text).strip()
    if public_affairs:
        return _truncate_words(quote, 14)
    low = quote.lower()
    if any(m in low for m in EMOTION_WORDS["konflikt"]):
        return _truncate_words(f"Tu zaczyna się spór: {quote}", 16)
    if "?" in quote or any(low.startswith(q) for q in QUESTION_MARKERS):
        return _truncate_words(quote, 14)
    if any(m in low for m in SURPRISE_MARKERS):
        return _truncate_words(f"Tego zdania nie da się przeoczyć: {quote}", 16)
    return _truncate_words(quote, 14)


def _screen_text(text: str) -> str:
    return _truncate_words(_strongest_sentence(text), 10)


def _subtitles_for_window(segments: list[TranscriptSegment], start: float, end: float) -> list[dict]:
    out = []
    for seg in segments:
        if seg.end <= start or seg.start >= end:
            continue
        rel_start = max(0.0, seg.start - start)
        rel_end = min(end, seg.end) - start
        out.append({"start": round(rel_start, 2), "end": round(max(rel_start + 0.15, rel_end), 2), "text": clean_text(seg.text)})
    return out


def _reason(text: str, duration: float, public_affairs: bool) -> str:
    features = []
    low = text.lower()
    if any(m in low for m in EMOTION_WORDS["konflikt"]):
        features.append("wyraźne napięcie lub kontrast")
    if any(m in low for m in SURPRISE_MARKERS):
        features.append("nagła zmiana lub zaskoczenie")
    if "?" in text:
        features.append("naturalne pytanie pod komentarze")
    if 14 <= duration <= 35:
        features.append("dobry rytm pod krótki format")
    if not features:
        features.append("samodzielna, krótka wypowiedź z czytelną puentą")
    suffix = ". W trybie publicystycznym zachowano dosłowny sens wypowiedzi" if public_affairs else ""
    return ", ".join(features[:3]).capitalize() + suffix + "."


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
        return f"Fragment wypowiedzi: „{quote}”. Oceń argument, nie nagłówek."
    return f"Najmocniejszy moment: „{quote}”. Jak Ty to odbierasz?"


def _build_candidate(window: list[TranscriptSegment], all_segments: list[TranscriptSegment], content_mode: str) -> ClipCandidate:
    start = window[0].start
    end = window[-1].end
    duration = end - start
    text = clean_text(" ".join(s.text for s in window))
    public_affairs = content_mode == "public_affairs" or (content_mode == "auto" and _auto_public_affairs(text))
    quote = _strongest_sentence(text)
    suggested = min((15, 30, 60), key=lambda d: abs(d - duration))
    return ClipCandidate(
        rank=0,
        start=start,
        end=end,
        duration=duration,
        quote=quote,
        hook=_hook(text, public_affairs),
        screen_text=_screen_text(text),
        reason=_reason(text, duration, public_affairs),
        viral_score=_score(text, duration),
        emotion=_emotion(text),
        suggested_length=suggested,
        cut_before=f"Usuń wszystko przed {format_time(start)}. Zacznij maksymalnie 0,3 s przed pierwszym słowem.",
        cut_after=f"Zakończ przy {format_time(end)}. Usuń dalsze dopowiedzenia bez nowej puenty.",
        subtitles=_subtitles_for_window(all_segments, start, end),
        tiktok_description=_description(text, public_affairs),
        hashtags=_hashtags(text, public_affairs),
        cta="Jak oceniasz ten argument na podstawie tej wypowiedzi?" if public_affairs else "Co o tym myślisz?",
        topic=_topic(text),
        text=text,
    )


def _overlap_ratio(a: ClipCandidate, b: ClipCandidate) -> float:
    inter = max(0.0, min(a.end, b.end) - max(a.start, b.start))
    return 0.0 if inter <= 0 else inter / min(a.duration, b.duration)


def analyze_segments(segments: list[TranscriptSegment], top_n: int = 10, content_mode: str = "auto") -> list[ClipCandidate]:
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
    candidates.sort(key=lambda c: (-c.viral_score, abs(c.duration - c.suggested_length), c.start))
    selected: list[ClipCandidate] = []
    for cand in candidates:
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
            "Materiał może być polityczny/publicystyczny. Zachowaj neutralność, nie dopisuj ocen politycznych, nie zmieniaj znaczenia, hook oprzyj na dosłownej wypowiedzi."
            if public_affairs else "Nie wymyślaj faktów. Hook ma być mocny, ale zgodny z treścią."
        )
        prompt = f"""Jesteś montażystą krótkich form. {safety}
Zwróć WYŁĄCZNIE poprawny JSON z polami: hook, screen_text, reason, emotion, description, hashtags, cta.
Hashtags ma być tablicą 5-7 elementów. screen_text maks. 12 słów. description maks. 2 krótkie zdania.
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
                hook=clean_text(str(data.get("hook", cand.hook)))[:160],
                screen_text=_truncate_words(str(data.get("screen_text", cand.screen_text)), 12),
                reason=clean_text(str(data.get("reason", cand.reason)))[:420],
                emotion=clean_text(str(data.get("emotion", cand.emotion)))[:40],
                tiktok_description=clean_text(str(data.get("description", cand.tiktok_description)))[:300],
                hashtags=[str(x) for x in tags][:7],
                cta=clean_text(str(data.get("cta", cand.cta)))[:160],
            ))
        except Exception:
            updated.append(cand)
    return updated
