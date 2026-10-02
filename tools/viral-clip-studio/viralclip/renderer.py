from __future__ import annotations

import shutil
import subprocess
import zipfile
from dataclasses import replace
from pathlib import Path

from .models import ClipCandidate, TranscriptSegment


def _srt_time(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def _ass_time(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    h, rem = divmod(cs, 360_000)
    m, rem = divmod(rem, 6_000)
    s, centi = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{centi:02d}"


def _ass_escape(text: str) -> str:
    return (
        str(text)
        .replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
        .strip()
    )


def _chunks(text: str, words_per_chunk: int = 3) -> list[str]:
    words = str(text).split()
    return [" ".join(words[i : i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def write_srt(clip: ClipCandidate, path: str | Path) -> Path:
    path = Path(path)
    lines: list[str] = []
    for i, item in enumerate(clip.subtitles, start=1):
        lines.extend([
            str(i),
            f"{_srt_time(float(item['start']))} --> {_srt_time(float(item['end']))}",
            str(item["text"]),
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _fallback_words(clip: ClipCandidate) -> list[dict]:
    words: list[dict] = []
    for item in clip.subtitles:
        start = max(0.0, float(item.get("start", 0.0)))
        end = min(clip.duration, float(item.get("end", start)))
        tokens = str(item.get("text", "")).split()
        if not tokens or end <= start:
            continue
        step = (end - start) / len(tokens)
        for idx, token in enumerate(tokens):
            words.append(
                {
                    "start": start + idx * step,
                    "end": start + (idx + 1) * step,
                    "text": token,
                }
            )
    return words


def words_for_clip(clip: ClipCandidate, segments: list[TranscriptSegment] | None = None) -> list[dict]:
    """Return word timestamps relative to the selected clip."""
    if not segments:
        return _fallback_words(clip)

    words: list[dict] = []
    for seg in segments:
        if seg.end <= clip.start or seg.start >= clip.end:
            continue
        for word in getattr(seg, "words", None) or []:
            start = float(word.get("start", seg.start))
            end = float(word.get("end", start))
            text = str(word.get("text", "")).strip()
            if not text or end <= clip.start or start >= clip.end:
                continue
            words.append(
                {
                    "start": max(0.0, start - clip.start),
                    "end": min(clip.duration, end - clip.start),
                    "text": text,
                }
            )
    return sorted(words, key=lambda item: (item["start"], item["end"])) or _fallback_words(clip)


def build_speech_ranges(
    clip: ClipCandidate,
    words: list[dict] | None = None,
    silence_threshold: float = 0.8,
    padding: float = 0.10,
) -> list[tuple[float, float]]:
    """Build ranges that keep speech while removing only longer pauses."""
    words = words or _fallback_words(clip)
    if not words:
        return [(0.0, clip.duration)]

    ordered = sorted(words, key=lambda item: float(item["start"]))
    ranges: list[tuple[float, float]] = []
    current_start = max(0.0, float(ordered[0]["start"]) - padding)
    previous_end = min(clip.duration, float(ordered[0]["end"]))

    for word in ordered[1:]:
        start = max(0.0, float(word["start"]))
        end = min(clip.duration, float(word["end"]))
        if start - previous_end > silence_threshold:
            ranges.append((current_start, min(clip.duration, previous_end + padding)))
            current_start = max(0.0, start - padding)
        previous_end = max(previous_end, end)

    ranges.append((current_start, min(clip.duration, previous_end + padding)))

    cleaned: list[tuple[float, float]] = []
    for start, end in ranges:
        if end - start >= 0.15:
            cleaned.append((round(start, 3), round(end, 3)))
    return cleaned or [(0.0, clip.duration)]


def _range_duration(ranges: list[tuple[float, float]]) -> float:
    return sum(max(0.0, end - start) for start, end in ranges)


def _remap_time(value: float, ranges: list[tuple[float, float]]) -> float:
    elapsed = 0.0
    for start, end in ranges:
        if start <= value <= end:
            return elapsed + value - start
        if value < start:
            return elapsed
        elapsed += end - start
    return elapsed


def remap_words(words: list[dict], ranges: list[tuple[float, float]]) -> list[dict]:
    remapped: list[dict] = []
    for word in words:
        start = float(word["start"])
        end = float(word["end"])
        midpoint = (start + end) / 2
        if not any(a <= midpoint <= b for a, b in ranges):
            continue
        new_start = _remap_time(start, ranges)
        new_end = max(new_start + 0.05, _remap_time(end, ranges))
        remapped.append({"start": new_start, "end": new_end, "text": word["text"]})
    return remapped


def _word_groups(words: list[dict], words_per_chunk: int) -> list[list[dict]]:
    groups: list[list[dict]] = []
    current: list[dict] = []
    for word in words:
        if current and (
            len(current) >= words_per_chunk
            or float(word["start"]) - float(current[-1]["end"]) > 0.65
        ):
            groups.append(current)
            current = []
        current.append(word)
    if current:
        groups.append(current)
    return groups


def _highlight_line(group: list[dict], active_index: int) -> str:
    parts: list[str] = []
    for idx, word in enumerate(group):
        text = _ass_escape(str(word["text"]))
        if idx == active_index:
            parts.append(r"{\c&H0000FFFF&\fscx112\fscy112}" + text + r"{\rCaption}")
        else:
            parts.append(text)
    return " ".join(parts)


def write_dynamic_ass(
    clip: ClipCandidate,
    path: str | Path,
    show_hook: bool = True,
    words_per_chunk: int = 4,
    word_timeline: list[dict] | None = None,
    highlight_words: bool = True,
) -> Path:
    """Create TikTok captions with a 3-second hook and optional active-word highlighting."""
    path = Path(path)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Hook,Arial,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,3,3,0,8,80,80,170,1
Style: Caption,Arial,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H50000000,-1,0,0,0,100,100,0,0,3,3,0,2,90,90,245,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events: list[str] = []

    if show_hook and clip.hook:
        hook_end = min(3.0, max(0.8, clip.duration))
        events.append(
            f"Dialogue: 1,{_ass_time(0)},{_ass_time(hook_end)},Hook,,0,0,0,,{_ass_escape(clip.hook)}"
        )

    words = word_timeline or []
    if highlight_words and words:
        for group in _word_groups(words, max(2, words_per_chunk)):
            for idx, word in enumerate(group):
                start = max(0.0, float(word["start"]))
                if idx + 1 < len(group):
                    end = max(float(word["end"]), float(group[idx + 1]["start"]))
                else:
                    end = float(word["end"])
                end = min(clip.duration, max(start + 0.08, end))
                events.append(
                    f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Caption,,0,0,0,,{_highlight_line(group, idx)}"
                )
    else:
        for item in clip.subtitles:
            start = max(0.0, float(item.get("start", 0.0)))
            end = min(clip.duration, float(item.get("end", start + 0.4)))
            if end <= start:
                continue
            parts = _chunks(str(item.get("text", "")), max(1, words_per_chunk))
            if not parts:
                continue
            step = (end - start) / len(parts)
            for idx, part in enumerate(parts):
                part_start = start + idx * step
                part_end = end if idx == len(parts) - 1 else start + (idx + 1) * step
                events.append(
                    f"Dialogue: 0,{_ass_time(part_start)},{_ass_time(part_end)},Caption,,0,0,0,,{_ass_escape(part)}"
                )

    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")
    return path


def _write_word_srt(words: list[dict], path: str | Path, words_per_caption: int = 7) -> Path:
    path = Path(path)
    lines: list[str] = []
    for idx, group in enumerate(_word_groups(words, words_per_caption), start=1):
        lines.extend(
            [
                str(idx),
                f"{_srt_time(float(group[0]['start']))} --> {_srt_time(float(group[-1]['end']))}",
                " ".join(str(word["text"]) for word in group),
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _has_audio(video_path: Path) -> bool:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return True
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index", "-of", "csv=p=0", str(video_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip())


def _detect_face_layout(video_path: Path, clip: ClipCandidate) -> tuple[int, int, int, int] | None:
    """Return foreground width, height and overlay x/y focused on the dominant visible face."""
    try:
        import cv2
    except Exception:
        return None

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return None
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if width <= 0 or height <= 0:
        capture.release()
        return None

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    observations: list[tuple[float, float, float]] = []
    for fraction in (0.12, 0.30, 0.50, 0.70, 0.88):
        when = clip.start + clip.duration * fraction
        capture.set(cv2.CAP_PROP_POS_MSEC, when * 1000.0)
        ok, frame = capture.read()
        if not ok or frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))
        if len(faces) == 0:
            continue
        x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
        area = float(w * h)
        observations.append(((x + w / 2) / width, (y + h / 2) / height, area))
    capture.release()

    if observations:
        weight = sum(item[2] for item in observations) or 1.0
        focus_x = sum(item[0] * item[2] for item in observations) / weight
        focus_y = sum(item[1] * item[2] for item in observations) / weight
        zoom = 1.16
    else:
        focus_x, focus_y, zoom = 0.5, 0.5, 1.06

    factor = min(1080 / width, 1920 / height) * zoom
    fg_w = max(2, int(round(width * factor / 2) * 2))
    fg_h = max(2, int(round(height * factor / 2) * 2))

    desired_x = int(round(540 - focus_x * fg_w))
    desired_y = int(round(960 - focus_y * fg_h))
    x_low, x_high = (1080 - fg_w, 0) if fg_w > 1080 else (0, 1080 - fg_w)
    y_low, y_high = (1920 - fg_h, 0) if fg_h > 1920 else (0, 1920 - fg_h)
    overlay_x = int(_clamp(desired_x, x_low, x_high))
    overlay_y = int(_clamp(desired_y, y_low, y_high))
    return fg_w, fg_h, overlay_x, overlay_y


def _trim_graph(ranges: list[tuple[float, float]], has_audio: bool) -> tuple[list[str], str, str | None]:
    parts: list[str] = []
    video_labels: list[str] = []
    audio_labels: list[str] = []
    for idx, (start, end) in enumerate(ranges):
        parts.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{idx}]")
        video_labels.append(f"[v{idx}]")
        if has_audio:
            parts.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{idx}]")
            audio_labels.append(f"[a{idx}]")

    if len(ranges) == 1:
        parts.append("[v0]null[vcut]")
        if has_audio:
            parts.append("[a0]anull[acut]")
    elif has_audio:
        inputs = "".join(v + a for v, a in zip(video_labels, audio_labels))
        parts.append(f"{inputs}concat=n={len(ranges)}:v=1:a=1[vcut][acut]")
    else:
        parts.append(f"{''.join(video_labels)}concat=n={len(ranges)}:v=1:a=0[vcut]")
    return parts, "[vcut]", "[acut]" if has_audio else None


def _vertical_graph(
    video_label: str,
    caption_filter: str | None,
    face_layout: tuple[int, int, int, int] | None,
) -> list[str]:
    parts = [
        f"{video_label}split=2[bg][fg]",
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=24[bg2]",
    ]
    if face_layout:
        fg_w, fg_h, overlay_x, overlay_y = face_layout
        parts.append(f"[fg]scale={fg_w}:{fg_h}[fg2]")
        parts.append(f"[bg2][fg2]overlay={overlay_x}:{overlay_y}[composed]")
    else:
        parts.append("[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg2]")
        parts.append("[bg2][fg2]overlay=(W-w)/2:(H-h)/2[composed]")

    if caption_filter:
        parts.append(f"[composed]{caption_filter}[v]")
    else:
        parts.append("[composed]null[v]")
    return parts


def render_clip(
    video_path: str | Path,
    clip: ClipCandidate,
    output_dir: str | Path,
    burn_subtitles: bool = True,
    show_hook: bool = True,
    dynamic_subtitles: bool = True,
    segments: list[TranscriptSegment] | None = None,
    highlight_words: bool = True,
    auto_zoom: bool = True,
    trim_silence: bool = True,
    silence_threshold: float = 0.8,
) -> Path:
    if not ffmpeg_available():
        raise RuntimeError("Nie znaleziono FFmpeg w PATH. Zainstaluj FFmpeg i uruchom aplikację ponownie.")

    video_path = Path(video_path).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    stem = f"clip_{clip.rank:02d}_{int(clip.start):06d}_{int(clip.end):06d}"
    original_words = words_for_clip(clip, segments)
    ranges = build_speech_ranges(clip, original_words, silence_threshold=silence_threshold) if trim_silence else [(0.0, clip.duration)]
    compact_duration = _range_duration(ranges)
    compact_words = remap_words(original_words, ranges) if trim_silence else original_words
    caption_clip = replace(clip, duration=compact_duration)

    caption_filter: str | None = None
    if burn_subtitles:
        if dynamic_subtitles:
            ass_name = f"{stem}.ass"
            write_dynamic_ass(
                caption_clip,
                out / ass_name,
                show_hook=show_hook,
                word_timeline=compact_words,
                highlight_words=highlight_words,
            )
            caption_filter = f"ass='{ass_name}'"
        else:
            srt_name = f"{stem}.srt"
            if compact_words:
                _write_word_srt(compact_words, out / srt_name)
            else:
                write_srt(caption_clip, out / srt_name)
            caption_filter = (
                f"subtitles='{srt_name}':force_style="
                "'FontName=Arial,FontSize=18,Bold=1,Outline=2,Shadow=0,Alignment=2,MarginV=170'"
            )

    meaningful_trim = trim_silence and (
        len(ranges) > 1
        or ranges[0][0] > 0.03
        or ranges[0][1] < clip.duration - 0.03
    )
    has_audio = _has_audio(video_path)
    filter_parts: list[str] = []
    audio_label: str | None = None
    if meaningful_trim:
        trim_parts, video_label, audio_label = _trim_graph(ranges, has_audio)
        filter_parts.extend(trim_parts)
    else:
        video_label = "[0:v]"

    face_layout = _detect_face_layout(video_path, clip) if auto_zoom else None
    filter_parts.extend(_vertical_graph(video_label, caption_filter, face_layout))

    target = out / f"{stem}_tiktok.mp4"
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{clip.start:.3f}", "-i", str(video_path), "-t", f"{clip.duration:.3f}",
        "-filter_complex", ";".join(filter_parts),
        "-map", "[v]",
    ]
    if meaningful_trim and audio_label:
        cmd += ["-map", audio_label]
    elif not meaningful_trim:
        cmd += ["-map", "0:a?"]

    cmd += [
        "-r", "30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(target),
    ]
    subprocess.run(cmd, check=True, cwd=str(out))
    return target


def render_top_clips(
    video_path: str | Path,
    candidates: list[ClipCandidate],
    output_dir: str | Path,
    count: int = 5,
    burn_subtitles: bool = True,
    show_hook: bool = True,
    dynamic_subtitles: bool = True,
    segments: list[TranscriptSegment] | None = None,
    highlight_words: bool = True,
    auto_zoom: bool = True,
    trim_silence: bool = True,
    silence_threshold: float = 0.8,
) -> list[Path]:
    rendered: list[Path] = []
    for clip in candidates[: max(0, count)]:
        rendered.append(
            render_clip(
                video_path,
                clip,
                output_dir,
                burn_subtitles=burn_subtitles,
                show_hook=show_hook,
                dynamic_subtitles=dynamic_subtitles,
                segments=segments,
                highlight_words=highlight_words,
                auto_zoom=auto_zoom,
                trim_silence=trim_silence,
                silence_threshold=silence_threshold,
            )
        )
    return rendered


def write_social_copy(clip: ClipCandidate, path: str | Path) -> Path:
    path = Path(path)
    content = (
        f"KLIP #{clip.rank}\n"
        f"Źródło: {clip.start:.1f}s–{clip.end:.1f}s\n\n"
        f"WYBRANY HOOK:\n{clip.hook}\n"
        f"WYNIK HOOKA: {clip.selected_hook_score:.0f}/100\n\n"
        f"3 WARIANTY HOOKA:\n"
        + "\n".join(
            f"{idx}. [{item.get('kind', 'hook')}] {item.get('score', 0):.0f}/100 — {item.get('text', '')}"
            + ("  <- WYBRANY" if item.get("text") == clip.hook else "")
            for idx, item in enumerate(clip.hook_variants, start=1)
        )
        + f"\n\nOPIS TIKTOK:\n{clip.tiktok_description}\n\n"
        f"HASHTAGI:\n{' '.join(clip.hashtags)}\n\n"
        f"CTA:\n{clip.cta}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def write_top5_copy(candidates: list[ClipCandidate], output_dir: str | Path, count: int = 5) -> list[Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for clip in candidates[: max(0, count)]:
        files.append(write_social_copy(clip, out / f"clip_{clip.rank:02d}_opis_hashtagi.txt"))
    return files


def package_clips(
    paths: list[str | Path],
    zip_path: str | Path,
    extra_files: list[str | Path] | None = None,
) -> Path:
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [*paths, *(extra_files or [])]:
            item = Path(path)
            archive.write(item, arcname=item.name)
    return zip_path
