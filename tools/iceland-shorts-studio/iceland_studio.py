from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

import requests

from prompt import MASTER_PROMPT


class StudioError(RuntimeError):
    pass


def require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise StudioError(f"{name} is not installed or is not available in PATH.")
    return path


def _clean_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^\s*```(?:json)?", "", text, flags=re.I)
    text = re.sub(r"```\s*$", "", text)
    first = text.find("{")
    last = text.rfind("}")
    if first < 0 or last < first:
        raise StudioError("The AI response did not contain a JSON object.")
    return json.loads(text[first:last + 1])


def make_plan_with_xai(topic: str, duration: int, api_key: str, model: str) -> dict:
    if not api_key:
        raise StudioError("Add your xAI API key first.")

    prompt = MASTER_PROMPT.format(topic=topic, duration=duration)
    response = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.75,
        },
        timeout=120,
    )
    if not response.ok:
        raise StudioError(f"xAI error {response.status_code}: {response.text[:500]}")

    payload = response.json()
    text = payload["choices"][0]["message"]["content"]
    return normalize_plan(_clean_json(text), topic)


def fallback_plan(topic: str, duration: int) -> dict:
    hook = "DON'T make this Iceland road-trip mistake."
    voice = (
        f"{hook} {topic}. Iceland can change fast, so build your plan around current "
        "conditions, not only the itinerary you saved weeks ago. Check official road "
        "and weather information before you leave, and be ready to change the route. "
        "Would you still drive Iceland yourself?"
    )
    return normalize_plan(
        {
            "title": "Iceland Road Trip Reality Check",
            "hook": hook,
            "voiceover": voice,
            "ending": "Would you still drive Iceland yourself?",
            "caption": "A simple Iceland road-trip habit that can save the day.",
            "hashtags": [
                "#Iceland",
                "#IcelandTravel",
                "#IcelandRoadTrip",
                "#TravelTips",
                "#VisitIceland",
            ],
            "scenes": [
                {"query": "Iceland road mountains", "visual": "POV drive on an Icelandic road"},
                {"query": "Iceland storm road", "visual": "Wind and changing weather on the road"},
                {"query": "Iceland highway landscape", "visual": "Wide Iceland road through open terrain"},
                {"query": "Iceland car road trip", "visual": "Car driving through Icelandic scenery"},
                {"query": "Iceland mountains clouds", "visual": "Fast-moving clouds over mountains"},
                {"query": "Iceland scenic road", "visual": "Final cinematic road shot"},
            ],
        },
        topic,
    )


def normalize_plan(plan: dict, topic: str) -> dict:
    scenes = plan.get("scenes") or []
    cleaned = []
    for scene in scenes[:10]:
        if isinstance(scene, dict):
            query = str(scene.get("query") or "Iceland landscape").strip()
            visual = str(scene.get("visual") or query).strip()
            cleaned.append({"query": query, "visual": visual})
    if not cleaned:
        cleaned = [{"query": "Iceland landscape", "visual": "Authentic Iceland landscape"}] * 6

    hashtags = plan.get("hashtags") or ["#Iceland", "#IcelandTravel", "#TravelTips"]
    if isinstance(hashtags, str):
        hashtags = hashtags.split()

    return {
        "topic": topic,
        "title": str(plan.get("title") or topic),
        "hook": str(plan.get("hook") or "DON'T visit Iceland before you know this."),
        "voiceover": str(plan.get("voiceover") or ""),
        "ending": str(plan.get("ending") or "Would you do this in Iceland?"),
        "caption": str(plan.get("caption") or topic),
        "hashtags": [str(x) for x in hashtags][:8],
        "scenes": cleaned,
    }


def _pexels_pick(video: dict) -> str | None:
    candidates = video.get("video_files") or []
    candidates = [x for x in candidates if x.get("link") and x.get("width") and x.get("height")]
    if not candidates:
        return None
    portrait = [x for x in candidates if int(x["height"]) >= int(x["width"])]
    pool = portrait or candidates
    pool.sort(key=lambda x: abs(int(x["height"]) - 1920) + abs(int(x["width"]) - 1080))
    return pool[0]["link"]


def fetch_pexels_video(query: str, api_key: str, out_path: Path) -> Path:
    if not api_key:
        raise StudioError("Pexels API key is missing.")
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "per_page": 12},
        timeout=60,
    )
    if not r.ok:
        raise StudioError(f"Pexels error {r.status_code}: {r.text[:300]}")
    videos = r.json().get("videos") or []
    if not videos:
        raise StudioError(f"No Pexels video found for: {query}")

    videos.sort(
        key=lambda v: (
            0 if int(v.get("height") or 0) >= int(v.get("width") or 0) else 1,
            -(int(v.get("height") or 0)),
        )
    )
    link = None
    for video in videos:
        link = _pexels_pick(video)
        if link:
            break
    if not link:
        raise StudioError(f"No usable Pexels file found for: {query}")

    with requests.get(link, stream=True, timeout=120) as media:
        media.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in media.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
    return out_path


async def _tts(text: str, out_path: str, voice: str, rate: str) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
    await communicate.save(out_path)


def synthesize_voiceover(text: str, out_path: Path, voice: str, rate: str = "+0%") -> Path:
    if not text.strip():
        raise StudioError("Voice-over text is empty.")
    asyncio.run(_tts(text, str(out_path), voice, rate))
    return out_path


def probe_duration(path: Path) -> float:
    require_binary("ffprobe")
    r = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path)
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return max(0.1, float(r.stdout.strip()))


def _run(cmd: list[str]) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise StudioError((e.stderr or e.stdout or str(e))[-1800:]) from e


def prepare_vertical(source: Path, out_path: Path, duration: float) -> Path:
    require_binary("ffmpeg")
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "fps=30,"
        "format=yuv420p"
    )
    _run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(source),
        "-t", f"{duration:.3f}", "-an",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        str(out_path),
    ])
    return out_path


def concat_scenes(scene_paths: Iterable[Path], out_path: Path) -> Path:
    scene_paths = list(scene_paths)
    if not scene_paths:
        raise StudioError("No scene videos are available.")
    concat_file = out_path.with_suffix(".txt")
    lines = []
    for p in scene_paths:
        safe = str(p.resolve()).replace("'", "'\\''")
        lines.append(f"file '{safe}'")
    concat_file.write_text("\n".join(lines), encoding="utf-8")
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(out_path),
    ])
    return out_path


def _split_caption_chunks(text: str, max_words: int = 6) -> list[str]:
    words = re.findall(r"\S+", text)
    return [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)] or ["ICELAND"]


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _escape_ass(text: str) -> str:
    text = text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
    keywords = ["ICELAND", "TOURISTS", "DON'T", "WARNING", "ROAD", "WINTER", "MISTAKE", "RIGHT"]

    for kw in keywords:
        pattern = re.compile(rf"\b({re.escape(kw)})\b", flags=re.I)

        def highlight(match: re.Match[str]) -> str:
            return (
                r"{\c&H00FFFF&\b1}"
                + match.group(1)
                + r"{\c&HFFFFFF&\b1}"
            )

        text = pattern.sub(highlight, text)

    return text


def build_ass(hook: str, voiceover: str, duration: float, out_path: Path) -> Path:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Caption,Arial,70,&H00FFFFFF,&H0000FFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,5,1,2,80,80,285,1
Style: Hook,Arial,82,&H00FFFFFF,&H0000FFFF,&H00101010,&H90000000,-1,0,0,0,100,100,0,0,1,6,1,8,70,70,210,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events = []
    hook_end = min(2.4, duration)
    events.append(
        f"Dialogue: 1,{_ass_time(0)},{_ass_time(hook_end)},Hook,,0,0,0,,{_escape_ass(hook.upper())}"
    )

    chunks = _split_caption_chunks(voiceover, 6)
    start = 0.15
    usable = max(0.5, duration - start)
    step = usable / len(chunks)
    for i, chunk in enumerate(chunks):
        s = start + i * step
        e = min(duration, start + (i + 1) * step + 0.08)
        events.append(
            f"Dialogue: 0,{_ass_time(s)},{_ass_time(e)},Caption,,0,0,0,,{_escape_ass(chunk)}"
        )
    out_path.write_text(header + "\n".join(events), encoding="utf-8-sig")
    return out_path


def _ass_filter_path(path: Path) -> str:
    p = path.resolve().as_posix()
    p = p.replace(":", r"\:")
    p = p.replace("'", r"\'")
    return p


def finish_video(
    video: Path,
    voice: Path,
    ass: Path,
    output: Path,
    music: Path | None = None,
) -> Path:
    require_binary("ffmpeg")
    ass_filter = _ass_filter_path(ass)

    if music:
        _run([
            "ffmpeg", "-y",
            "-i", str(video), "-i", str(voice), "-stream_loop", "-1", "-i", str(music),
            "-filter_complex",
            f"[0:v]ass='{ass_filter}'[v];"
            "[1:a]volume=1.0[voice];"
            "[2:a]volume=0.09[music];"
            "[voice][music]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest", str(output),
        ])
    else:
        _run([
            "ffmpeg", "-y",
            "-i", str(video), "-i", str(voice),
            "-vf", f"ass='{ass_filter}'",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest", str(output),
        ])
    return output


def render_project(
    plan: dict,
    source_videos: list[Path],
    workdir: Path,
    voice_name: str,
    voice_rate: str = "+0%",
    music: Path | None = None,
    pexels_api_key: str = "",
) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    require_binary("ffmpeg")
    require_binary("ffprobe")

    voice_path = synthesize_voiceover(
        plan["voiceover"], workdir / "voiceover.mp3", voice_name, voice_rate
    )
    audio_duration = probe_duration(voice_path)
    scenes = plan["scenes"]
    scene_duration = max(1.0, audio_duration / max(1, len(scenes)))

    raw_sources = list(source_videos)
    if not raw_sources and pexels_api_key:
        for i, scene in enumerate(scenes):
            p = workdir / f"stock_{i:02d}.mp4"
            fetch_pexels_video(scene["query"], pexels_api_key, p)
            raw_sources.append(p)

    if not raw_sources:
        raise StudioError(
            "Upload at least one source video or add a Pexels API key for automatic stock footage."
        )

    prepared = []
    for i, scene in enumerate(scenes):
        src = raw_sources[i % len(raw_sources)]
        dst = workdir / f"scene_{i:02d}.mp4"
        prepare_vertical(src, dst, scene_duration)
        prepared.append(dst)

    visual_track = concat_scenes(prepared, workdir / "visual_track.mp4")
    ass = build_ass(plan["hook"], plan["voiceover"], audio_duration, workdir / "captions.ass")
    return finish_video(visual_track, voice_path, ass, workdir / "iceland_short.mp4", music)
