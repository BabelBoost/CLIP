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
            f"**DŁUGOŚĆ MATERIAŁU:** {clip.duration:.1f} s", "",
            f"**REKOMENDOWANA DŁUGOŚĆ KLIPU:** {clip.suggested_length} s", "",
            f"**CYTAT / NAJMOCNIEJSZE ZDANIE:** {clip.quote}", "",
            f"**HOOK NA PIERWSZE 3 SEKUNDY:** {clip.hook}", "",
            f"**TEKST NA EKRAN:** {clip.screen_text}", "",
            f"**VIRAL SCORE:** {clip.viral_score}/100", "",
            f"**HOOK SCORE:** {clip.hook_score}/100", "",
            f"**EMOTION SCORE:** {clip.emotion_score}/100", "",
            f"**COMMENT POTENTIAL:** {clip.comment_potential}/100", "",
            f"**RETENTION SCORE:** {clip.retention_score}/100", "",
            f"**CONTEXT DEPENDENCY:** {clip.context_dependency}/100", "",
            f"**EMOCJA:** {clip.emotion}", "",
            f"**DLACZEGO TEN FRAGMENT MA POTENCJAŁ:** {clip.reason}", "",
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
        "| # | Timecode | Długość | Viral | Hook | Emocja | Komentarze | Retencja | Kontekst |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for c in candidates[:5]:
        lines.append(
            f"| {c.rank} | {format_time(c.start)}–{format_time(c.end)} | {c.suggested_length}s | "
            f"{c.viral_score:.0f} | {c.hook_score:.0f} | {c.emotion_score:.0f} | {c.comment_potential:.0f} | "
            f"{c.retention_score:.0f} | {c.context_dependency:.0f} |"
        )

    best = candidates[0]
    lines.extend([
        "", "## KLIP Z NAJWYŻSZYM WYNIKIEM", "",
        f"Klip {best.rank}: {format_time(best.start)}–{format_time(best.end)}. Viral Score {best.viral_score:.0f}/100.", "",
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
        writer.writerow([
            "ranking", "start", "end", "duration", "suggested_length", "topic", "hook", "screen_text",
            "viral_score", "hook_score", "emotion_score", "comment_potential", "retention_score", "context_dependency",
        ])
        for c in candidates:
            writer.writerow([
                c.rank, format_time(c.start), format_time(c.end), round(c.duration, 1), c.suggested_length,
                c.topic, c.hook, c.screen_text, c.viral_score, c.hook_score, c.emotion_score,
                c.comment_potential, c.retention_score, c.context_dependency,
            ])

    return {"markdown": md, "json": js, "csv": csv_path}
