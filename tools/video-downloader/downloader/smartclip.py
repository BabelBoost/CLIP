import json
import math
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class FrameSignal:
    time: float
    face_center_x: float | None
    face_count: int
    motion: float
    scene_change: float


@dataclass
class CandidateClip:
    start: float
    end: float
    score: float
    face_ratio: float
    motion_score: float
    scene_score: float
    focus_x: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def even(value: float | int) -> int:
    number = max(2, int(round(value)))
    return number if number % 2 == 0 else number - 1


def clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def clamp_crop_origin(center: float, frame_size: int, crop_size: int) -> int:
    if crop_size >= frame_size:
        return 0
    origin = int(round(center - crop_size / 2))
    return int(clamp(origin, 0, frame_size - crop_size))


def build_smart_crop_filter(
    width: int,
    height: int,
    focus_x: float = 0.5,
    output_width: int = 1080,
    output_height: int = 1920,
) -> str:
    """Build a 9:16 crop centered on the detected face position when possible."""
    if width <= 0 or height <= 0:
        raise ValueError("Nieprawidłowe wymiary wideo.")

    target_ratio = output_width / output_height
    source_ratio = width / height
    focus_x = clamp(float(focus_x), 0.0, 1.0)

    if source_ratio > target_ratio:
        crop_width = even(height * target_ratio)
        crop_height = even(height)
        center_x = focus_x * width
        crop_x = clamp_crop_origin(center_x, width, crop_width)
        crop_y = max(0, (height - crop_height) // 2)
    elif source_ratio < target_ratio:
        crop_width = even(width)
        crop_height = even(width / target_ratio)
        crop_x = 0
        crop_y = max(0, (height - crop_height) // 2)
    else:
        crop_width = even(width)
        crop_height = even(height)
        crop_x = 0
        crop_y = 0

    return (
        f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y},"
        f"scale={output_width}:{output_height}:flags=lanczos,setsar=1"
    )


def _face_detector():
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        raise RuntimeError("Nie udało się załadować modelu wykrywania twarzy OpenCV.")
    return detector


def _resize_for_analysis(frame, target_width: int = 480):
    height, width = frame.shape[:2]
    if width <= target_width:
        return frame
    scale = target_width / width
    return cv2.resize(frame, (target_width, max(2, int(height * scale))))


def _scene_difference(gray, previous_gray) -> float:
    if previous_gray is None:
        return 0.0
    hist_a = cv2.calcHist([gray], [0], None, [32], [0, 256])
    hist_b = cv2.calcHist([previous_gray], [0], None, [32], [0, 256])
    cv2.normalize(hist_a, hist_a)
    cv2.normalize(hist_b, hist_b)
    correlation = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
    return float(clamp(1.0 - correlation, 0.0, 2.0))


def _motion_difference(gray, previous_gray) -> float:
    if previous_gray is None:
        return 0.0
    diff = cv2.absdiff(gray, previous_gray)
    return float(np.mean(diff))


def scan_video(
    input_path: str | Path,
    sample_interval: float = 0.8,
    progress_callback=None,
) -> tuple[list[FrameSignal], dict]:
    source = Path(input_path)
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError("OpenCV nie może otworzyć pobranego wideo.")

    detector = _face_detector()
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise RuntimeError("Nie udało się odczytać parametrów wideo.")

    duration = frame_count / fps
    sample_interval = max(0.25, float(sample_interval))
    sample_step = max(1, int(round(fps * sample_interval)))

    signals: list[FrameSignal] = []
    previous_gray = None
    sampled_index = 0
    expected_samples = max(1, math.ceil(frame_count / sample_step))

    for frame_index in range(0, frame_count, sample_step):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            continue

        reduced = _resize_for_analysis(frame)
        gray = cv2.cvtColor(reduced, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = detector.detectMultiScale(
            gray,
            scaleFactor=1.12,
            minNeighbors=5,
            minSize=(30, 30),
        )

        face_center_x = None
        if len(faces):
            largest = max(faces, key=lambda rect: rect[2] * rect[3])
            x, _, w, _ = largest
            face_center_x = float((x + w / 2) / reduced.shape[1])

        signals.append(
            FrameSignal(
                time=float(frame_index / fps),
                face_center_x=face_center_x,
                face_count=int(len(faces)),
                motion=_motion_difference(gray, previous_gray),
                scene_change=_scene_difference(gray, previous_gray),
            )
        )
        previous_gray = gray
        sampled_index += 1

        if progress_callback:
            progress_callback(min(sampled_index / expected_samples, 1.0))

    capture.release()

    metadata = {
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": frame_count,
        "duration": duration,
        "sample_interval": sample_interval,
    }
    return signals, metadata


def _window_score(signals: list[FrameSignal], start: float, end: float) -> CandidateClip:
    window = [signal for signal in signals if start <= signal.time < end]
    if not window:
        return CandidateClip(start, end, 0.0, 0.0, 0.0, 0.0, 0.5)

    face_signals = [signal for signal in window if signal.face_center_x is not None]
    face_ratio = len(face_signals) / len(window)

    motion_mean = float(np.mean([signal.motion for signal in window]))
    motion_score = clamp(motion_mean / 22.0, 0.0, 1.0)

    scene_peaks = sum(1 for signal in window if signal.scene_change >= 0.28)
    scene_score = clamp(scene_peaks / 3.0, 0.0, 1.0)

    if face_signals:
        centers = [signal.face_center_x for signal in face_signals if signal.face_center_x is not None]
        focus_x = float(np.median(centers))
    else:
        focus_x = 0.5

    score = (
        face_ratio * 0.50
        + motion_score * 0.32
        + scene_score * 0.18
    )

    return CandidateClip(
        start=float(start),
        end=float(end),
        score=float(score),
        face_ratio=float(face_ratio),
        motion_score=float(motion_score),
        scene_score=float(scene_score),
        focus_x=float(clamp(focus_x, 0.0, 1.0)),
    )


def clips_overlap(a: CandidateClip, b: CandidateClip, tolerance: float = 0.0) -> bool:
    return not (a.end <= b.start + tolerance or b.end <= a.start + tolerance)


def select_non_overlapping(
    candidates: list[CandidateClip],
    max_count: int,
) -> list[CandidateClip]:
    selected: list[CandidateClip] = []
    for candidate in sorted(candidates, key=lambda item: item.score, reverse=True):
        if all(not clips_overlap(candidate, chosen) for chosen in selected):
            selected.append(candidate)
        if len(selected) >= max(1, int(max_count)):
            break
    return sorted(selected, key=lambda item: item.start)


def suggest_clips(
    signals: list[FrameSignal],
    duration: float,
    clip_length: float = 20.0,
    max_clips: int = 3,
) -> list[CandidateClip]:
    if duration <= 0:
        return []

    clip_length = clamp(float(clip_length), 5.0, max(5.0, duration))
    if duration <= clip_length:
        return [_window_score(signals, 0.0, duration)]

    step = max(3.0, clip_length / 2.0)
    candidates: list[CandidateClip] = []
    start = 0.0

    while start < duration:
        end = min(start + clip_length, duration)
        if end - start >= min(5.0, clip_length):
            candidates.append(_window_score(signals, start, end))
        if end >= duration:
            break
        start += step

    return select_non_overlapping(candidates, max_clips)


def analyze_video_for_clips(
    input_path: str | Path,
    clip_length: float = 20.0,
    max_clips: int = 3,
    sample_interval: float = 0.8,
    progress_callback=None,
) -> tuple[list[CandidateClip], dict]:
    signals, metadata = scan_video(
        input_path,
        sample_interval=sample_interval,
        progress_callback=progress_callback,
    )
    clips = suggest_clips(
        signals,
        duration=float(metadata["duration"]),
        clip_length=clip_length,
        max_clips=max_clips,
    )
    metadata["samples"] = len(signals)
    metadata["face_samples"] = sum(1 for signal in signals if signal.face_center_x is not None)
    return clips, metadata


def smart_clip_output_path(input_path: str | Path, index: int) -> Path:
    source = Path(input_path)
    return source.with_name(f"{source.stem}_smartclip_{index:02d}_9x16.mp4")


def build_smart_clip_command(
    ffmpeg: str,
    input_path: str | Path,
    output_path: str | Path,
    candidate: CandidateClip,
    width: int,
    height: int,
) -> list[str]:
    video_filter = build_smart_crop_filter(width, height, candidate.focus_x)
    return [
        ffmpeg,
        "-y",
        "-ss", f"{candidate.start:.3f}",
        "-i", str(input_path),
        "-t", f"{candidate.duration:.3f}",
        "-vf", video_filter,
        "-map", "0:v:0",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]


def render_smart_clip(
    input_path: str | Path,
    candidate: CandidateClip,
    width: int,
    height: int,
    index: int,
    output_path: str | Path | None = None,
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg nie jest zainstalowany lub nie znajduje się w PATH.")

    target = Path(output_path) if output_path else smart_clip_output_path(input_path, index)
    command = build_smart_clip_command(
        ffmpeg,
        input_path,
        target,
        candidate,
        width,
        height,
    )
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        error_tail = process.stderr[-1800:] if process.stderr else "Nieznany błąd FFmpeg."
        raise RuntimeError(f"FFmpeg nie utworzył Smart Clip.\n{error_tail}")
    if not target.exists():
        raise RuntimeError("FFmpeg zakończył pracę, ale Smart Clip nie powstał.")
    return target


def write_analysis_report(
    output_dir: str | Path,
    source_name: str,
    candidates: list[CandidateClip],
    metadata: dict,
) -> Path:
    target = Path(output_dir) / "smartclip_analysis.json"
    payload = {
        "source": source_name,
        "engine": "Babel Boost Smart Clips 3.0",
        "note": (
            "Ranking jest heurystyczny. Ocenia obecność twarzy, ruch i zmiany scen, "
            "a nie znaczenie wypowiedzi."
        ),
        "metadata": metadata,
        "clips": [asdict(candidate) for candidate in candidates],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
