from downloader.smartclip import (
    CandidateClip,
    FrameSignal,
    build_smart_clip_command,
    build_smart_crop_filter,
    clamp_crop_origin,
    select_non_overlapping,
    suggest_clips,
)


def test_crop_origin_stays_inside_frame():
    assert clamp_crop_origin(100, 1920, 608) == 0
    assert clamp_crop_origin(960, 1920, 608) == 656
    assert clamp_crop_origin(1850, 1920, 608) == 1312


def test_smart_crop_filter_uses_face_focus():
    filter_text = build_smart_crop_filter(1920, 1080, focus_x=0.75)
    assert "crop=608:1080:1136:0" in filter_text
    assert "scale=1080:1920" in filter_text


def test_select_non_overlapping_prefers_higher_scores():
    clips = [
        CandidateClip(0, 20, 0.90, 1.0, 0.7, 0.2, 0.5),
        CandidateClip(10, 30, 0.95, 1.0, 0.8, 0.3, 0.5),
        CandidateClip(35, 55, 0.70, 0.6, 0.8, 0.4, 0.5),
    ]
    selected = select_non_overlapping(clips, 2)
    assert [(clip.start, clip.end) for clip in selected] == [(10, 30), (35, 55)]


def test_suggest_clips_returns_ranked_non_overlapping_windows():
    signals = []
    for second in range(60):
        signals.append(
            FrameSignal(
                time=float(second),
                face_center_x=0.7 if 20 <= second < 40 else None,
                face_count=1 if 20 <= second < 40 else 0,
                motion=20.0 if 20 <= second < 40 else 2.0,
                scene_change=0.5 if second in {22, 28, 34} else 0.0,
            )
        )

    clips = suggest_clips(signals, duration=60, clip_length=20, max_clips=2)
    assert len(clips) == 2
    assert any(clip.start == 20.0 for clip in clips)
    focused = next(clip for clip in clips if clip.start == 20.0)
    assert focused.focus_x == 0.7
    assert focused.score > 0.7


def test_build_smart_clip_command_contains_trim_and_vertical_filter():
    candidate = CandidateClip(12.5, 32.5, 0.8, 0.9, 0.6, 0.3, 0.65)
    command = build_smart_clip_command(
        "ffmpeg",
        "input.mp4",
        "output.mp4",
        candidate,
        1920,
        1080,
    )
    joined = " ".join(command)
    assert "-ss 12.500" in joined
    assert "-t 20.000" in joined
    assert "scale=1080:1920" in joined
    assert command[-1] == "output.mp4"
