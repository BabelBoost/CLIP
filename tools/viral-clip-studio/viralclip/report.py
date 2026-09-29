from __future__ import annotations

import csv
import json
from pathlib import Path

from .analyzer import format_time
from .models import ClipCandidate


def _montage_plan(clip: ClipCandidate) -> str:
    d = max(1, int(round(clip.duration)))
    p1 = min(3, d)
    p2 = min(8, d)
    p3 = min(15, d)
    lines = [
        f"0:00 do 0:{p1:02d}  hook: {clip.hook}",
        f"0:{p1:02d} do 0:{p2:02d}  wejście w najmocniejszą wypowiedź",
        f"0:{p2:02d} do 0:{p3:02d}  rozwinięcie i kontekst",
    ]
    if d > p3:
        lines.append(f"0:{p3:02d} do 0:{d:02d}  puenta + CTA: {clip.cta}")
    return "\n".join(lines)


def render_markdown(candidates: list[ClipCandidate]) -> str:
    if not candidates:
        return "# Brak kandydatów\n"

    lines = ["# Raport Viral Clip Studio", "", "## TOP 5", ""]
    for clip in candidates[:5]:
        lines.extend([
            f"### NUMER KLIPU {clip.rank}", "",
            f"**TIMECODE START:** {format_time(clip.start)}", "",
            f"**TIMECODE KONIEC:** {format_time(clip.end)}", "",
            f"**DŁUGOŚĆ:** {clip.duration:.1f} s", "",
            f"**CYTAT / NAJMOCNIEJSZE ZDANIE:** {clip.quote}", "",
            f"**HOOK NA PIERWSZE 3 SEKUNDY:** {clip.hook}", "",
            f"**TEKST NA EKRAN:** {clip.screen_text}", "",
            f"**DLACZEGO TEN FRAGMENT MA POTENCJAŁ:** {clip.reason}", "",
            f"**VIRAL SCORE:** {clip.viral_score}/10", "",
            f"**EMOCJA:** {clip.emotion}", "",
            f"**SUGEROWANA DŁUGOŚĆ FINALNEGO KLIPU:** {clip.suggested_length} s", "",
            f"**SUGEROWANE CIĘCIE:** {clip.cut_before} {clip.cut_after}", "",
            "**NAPISY:**",
        ])
        for sub in clip.subtitles:
            lines.append(f"- {sub['start']:.2f}-{sub['end']:.2f}s: {sub['text']}")
        lines.extend([
            "",
            f"**OPIS DO TIKTOKA:** {clip.tiktok_description}", "",
            f"**HASHTAGI:** {' '.join(clip.hashtags)}", "",
            f"**CTA:** {clip.cta}", "",
        ])

    lines.extend([
        "## Ranking", "",
        "| Ranking | Timecode | Długość | Temat | Hook | Viral Score |",
        "| --- | --- | ---: | --- | --- | ---: |",
    ])
    for c in candidates[:5]:
        hook = c.hook.replace("|", "/")
        topic = c.topic.replace("|", "/")
        lines.append(f"| {c.rank} | {format_time(c.start)}–{format_time(c.end)} | {c.duration:.1f}s | {topic} | {hook} | {c.viral_score}/10 |")

    best = candidates[0]
    lines.extend([
        "", "## NAJLEPSZY KLIP DO PUBLIKACJI JAKO PIERWSZY", "",
        f"Klip {best.rank}: {format_time(best.start)}–{format_time(best.end)}. Viral Score {best.viral_score}/10.", "",
        "### Montaż sekunda po sekundzie", "", _montage_plan(best), "",
    ])
    return "\n".join(lines)


def save_reports(candidates: list[ClipCandidate], output_dir: str | Path) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    md = out / "viral_report.md"
    js = out / "viral_report.json"
    csv_path = out / "viral_ranking.csv"

    md.write_text(render_markdown(candidates), encoding="utf-8")
    js.write_text(json.dumps([c.to_dict() for c in candidates], ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["ranking", "start", "end", "duration", "topic", "hook", "viral_score"])
        for c in candidates:
            writer.writerow([c.rank, format_time(c.start), format_time(c.end), round(c.duration, 1), c.topic, c.hook, c.viral_score])

    return {"markdown": md, "json": js, "csv": csv_path}
