from downloader.speech import (
    SilenceInterval,
    SpeechSegment,
    burn_subtitle_filter,
    clip_segments,
    parse_silencedetect_output,
    speech_ratio,
    srt_timestamp,
    transcript_for_window,
    write_clip_srt,
)


def test_parse_silencedetect_output():
    stderr = """
    [silencedetect] silence_start: 2.5
    [silencedetect] silence_end: 4.0 | silence_duration: 1.5
    [silencedetect] silence_start: 10.0
    [silencedetect] silence_end: 12.25 | silence_duration: 2.25
    """
    intervals = parse_silencedetect_output(stderr)
    assert [(item.start, item.end) for item in intervals] == [(2.5, 4.0), (10.0, 12.25)]


def test_speech_ratio_uses_silence_overlap():
    silences = [SilenceInterval(2.0, 4.0), SilenceInterval(8.0, 9.0)]
    assert speech_ratio(0.0, 10.0, silences) == 0.7
    assert speech_ratio(2.0, 4.0, silences) == 0.0


def test_srt_timestamp():
    assert srt_timestamp(65.432) == "00:01:05,432"


def test_clip_segments_shift_to_clip_start():
    segments = [
        SpeechSegment(8.0, 11.0, "pierwszy"),
        SpeechSegment(12.0, 15.0, "drugi"),
        SpeechSegment(20.0, 22.0, "poza"),
    ]
    clipped = clip_segments(segments, 10.0, 16.0)
    assert [(item.start, item.end, item.text) for item in clipped] == [
        (0.0, 1.0, "pierwszy"),
        (2.0, 5.0, "drugi"),
    ]


def test_transcript_for_window():
    segments = [
        SpeechSegment(0.0, 2.0, "Ala ma kota."),
        SpeechSegment(2.0, 4.0, "Kot ma Alę."),
    ]
    assert transcript_for_window(segments, 1.0, 3.0) == "Ala ma kota. Kot ma Alę."


def test_write_clip_srt(tmp_path):
    segments = [SpeechSegment(10.0, 12.5, "Test napisów")]
    target = tmp_path / "clip.srt"
    write_clip_srt(segments, 10.0, 20.0, target)
    text = target.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:02,500" in text
    assert "Test napisów" in text


def test_burn_subtitle_filter_contains_subtitles(tmp_path):
    target = tmp_path / "clip captions.srt"
    value = burn_subtitle_filter(target)
    assert "subtitles=" in value
    assert "force_style=" in value
