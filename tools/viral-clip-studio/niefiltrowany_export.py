"""Automatyczny eksport klipów @niefiltrowanypl z oryginalnym dźwiękiem.

Plansza komentarza jest osobnym ujęciem. Lektor TTS jest opcjonalny.
Nie następuje automatyczna publikacja ani weryfikacja faktów.
"""
from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
import textwrap
import zipfile
from dataclasses import replace
from pathlib import Path

from viralclip.models import ClipCandidate, TranscriptSegment
from viralclip.renderer import render_clip, write_srt


def safe_caption(text: str, limit: int = 320) -> str:
    """Usuwa niedrukowalne znaki i ogranicza długość tekstu planszy."""
    value = " ".join(str(text).split())
    return "".join(c for c in value if c.isprintable())[:limit].strip()


def ass_escape(text: str) -> str:
    """Tekst użytkownika jako zwykły napis, bez możliwości dodania komend ASS."""
    return (
        str(text)
        .replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def _time_ass(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cents = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cents:02d}"


def write_commentary_ass(path: Path, commentary: str, duration: float) -> None:
    chunks = textwrap.wrap(safe_caption(commentary), width=30, break_long_words=False)
    message = r"\N".join(ass_escape(chunk) for chunk in chunks)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Label,Arial,51,&H0000D7FF,&H0000D7FF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,2,0,8,85,85,260,1
Style: Body,Arial,52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,2,0,5,90,90,0,1
Style: Footer,Arial,36,&H00DDDDDD,&H00DDDDDD,&H00000000,&H60000000,0,0,0,0,100,100,0,0,1,1,0,2,90,90,225,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    end = _time_ass(duration)
    events = [
        f"Dialogue: 0,0:00:00.00,{end},Label,,0,0,0,,NIEFILTROWANYPL  |  KOMENTARZ",
        f"Dialogue: 0,0:00:00.00,{end},Body,,0,0,0,,{message}",
        f"Dialogue: 0,0:00:00.00,{end},Footer,,0,0,0,,Oryginalne nagranie i źródło: patrz opis",
    ]
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    if proc.returncode:
        raise RuntimeError("FFmpeg: " + (proc.stderr or proc.stdout)[-1200:])


def _probe_duration(path: Path) -> float:
    output = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(output.stdout.strip())


async def _tts_save(text: str, output: Path) -> None:
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("Brakuje edge-tts. Uruchom ponownie instalator Windows.") from exc
    await edge_tts.Communicate(text, voice="pl-PL-MarekNeural").save(str(output))


def make_commentary_card(folder: Path, comment: str, use_tts: bool) -> Path:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Zainstaluj FFmpeg i FFprobe, a następnie dodaj je do PATH.")
    speech_path = folder / "narrator.mp3"
    if use_tts:
        try:
            asyncio.run(_tts_save(comment, speech_path))
        except Exception as exc:
            raise RuntimeError(
                "Nie udało się wygenerować lektora online. Sprawdź internet albo wyłącz lektora AI."
            ) from exc
        voice_length = _probe_duration(speech_path)
        if voice_length > 29.0:
            raise ValueError("Lektor trwa ponad 29 sekund. Skróć komentarz.")
        duration = max(5.0, voice_length + 0.9)
    else:
        duration = 7.0
    write_commentary_ass(folder / "commentary.ass", comment, duration)
    output = folder / "komentarz.mp4"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=0x172133:s=1080x1920:r=30",
    ]
    if use_tts:
        cmd += ["-i", str(speech_path), "-af", "apad"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += [
        "-t", f"{duration:.3f}", "-vf", "ass=commentary.ass",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(output),
    ]
    _run(cmd, folder)
    return output


def merge_clips(original: Path, commentary_card: Path, destination: Path) -> None:
    """Konkatenacja z ponownym kodowaniem, by uniknąć błędów różnych ścieżek audio."""
    graph = (
        "[0:v]fps=30,setpts=PTS-STARTPTS,format=yuv420p[v0];"
        "[1:v]fps=30,setpts=PTS-STARTPTS,format=yuv420p[v1];"
        "[0:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a0];"
        "[1:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a1];"
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
    )
    _run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(original), "-i", str(commentary_card),
        "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", str(destination),
    ], destination.parent)


def make_clip(
    video_path: Path,
    clip: ClipCandidate,
    segments: list[TranscriptSegment],
    output_root: Path,
    hook: str,
    comment: str,
    source_url: str,
    use_tts: bool = False,
) -> tuple[Path, Path, Path]:
    """Zwraca MP4, napisy źródłowe SRT i tekst redakcyjny."""
    comment = safe_caption(comment)
    if len(comment) < 8:
        raise ValueError("Komentarz jest za krótki.")
    output_root.mkdir(parents=True, exist_ok=True)
    folder = output_root / f"clip_{clip.rank:02d}"
    folder.mkdir(parents=True, exist_ok=True)

    # Hook jest zawsze własnym opisem redakcji, nigdy podszyciem się pod polityka.
    short_hook = safe_caption(hook, 85) or "Co wynika z tej wypowiedzi?"
    editorial_clip = replace(clip, hook=short_hook)
    raw = render_clip(
        video_path, editorial_clip, folder, burn_subtitles=True, show_hook=True,
        dynamic_subtitles=True, segments=segments, highlight_words=True,
        auto_zoom=False, trim_silence=False,
    )
    srt = write_srt(editorial_clip, folder / f"clip_{clip.rank:02d}.srt")
    card = make_commentary_card(folder, comment, use_tts)
    final_path = folder / f"niefiltrowany_{clip.rank:02d}_final.mp4"
    merge_clips(raw, card, final_path)

    url = source_url.strip()
    note = folder / f"niefiltrowany_{clip.rank:02d}_opis.txt"
    note.write_text(
        "NIEFILTROWANYPL\n\n"
        f"Źródłowy timecode: {clip.start:.2f}–{clip.end:.2f} s\n"
        f"Cytat (sprawdź odsłuchem): {clip.quote}\n"
        f"Hook redakcyjny: {short_hook}\n"
        f"Komentarz redakcyjny: {comment}\n"
        f"Źródło pełnego nagrania: {url or '[uzupełnij przed publikacją]'}\n"
        f"Opis: {clip.tiktok_description}\n"
        "Hashtagi: #niefiltrowanypl #polityka #publicystyka #komentarz\n\n"
        "Przed publikacją: zweryfikuj transkrypcję, kontekst, datę i prawa do materiału.\n"
        "Nie publikuj bez przeglądu redakcyjnego.\n",
        encoding="utf-8",
    )
    return final_path, srt, note


def make_zip(files: list[Path], output: Path) -> Path:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, arcname=f"{file.parent.name}/{file.name}")
    return output
