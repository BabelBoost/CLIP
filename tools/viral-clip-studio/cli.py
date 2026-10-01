from __future__ import annotations

import argparse
from pathlib import Path

from viralclip import (
    analyze_segments,
    enrich_with_ollama,
    package_clips,
    render_top_clips,
    save_reports,
    transcribe_video,
    write_top5_copy,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Analyze a video and create TikTok-ready TOP clips.")
    p.add_argument("video", help="Path to a local video file")
    p.add_argument("--language", default="pl", help="pl, en or auto")
    p.add_argument("--model", default="small", help="Whisper model: tiny/base/small/medium")
    p.add_argument("--mode", choices=["auto", "general", "public_affairs"], default="auto")
    p.add_argument("--ollama", action="store_true", help="Improve copy fields using local Ollama")
    p.add_argument("--ollama-model", default="qwen3:8b")
    p.add_argument("--render", type=int, default=5, help="Render N best clips. Default: 5")
    p.add_argument("--no-hook", action="store_true", help="Do not burn the 0-3 second hook")
    p.add_argument("--static-subtitles", action="store_true", help="Use classic subtitles instead of dynamic captions")
    p.add_argument("--no-subtitles", action="store_true", help="Render without burned-in subtitles")
    p.add_argument("--no-word-highlight", action="store_true", help="Disable active-word highlighting")
    p.add_argument("--no-auto-zoom", action="store_true", help="Disable automatic face/speaker zoom")
    p.add_argument("--keep-silence", action="store_true", help="Do not remove longer pauses")
    p.add_argument("--silence-threshold", type=float, default=0.8, help="Remove pauses longer than this many seconds")
    p.add_argument("--output", default="output")
    args = p.parse_args()

    video = Path(args.video)
    out = Path(args.output)
    segments, detected = transcribe_video(
        video,
        model_size=args.model,
        language=None if args.language == "auto" else args.language,
    )
    print(f"Transcription: {len(segments)} segments, language={detected}")

    count = max(0, args.render)
    clips = analyze_segments(segments, top_n=max(10, count), content_mode=args.mode)
    if args.ollama:
        clips = enrich_with_ollama(clips, model=args.ollama_model, content_mode=args.mode)

    paths = save_reports(clips, out)
    print(f"Report: {paths['markdown']}")

    rendered = render_top_clips(
        video,
        clips,
        out / "clips",
        count=count,
        burn_subtitles=not args.no_subtitles,
        show_hook=not args.no_hook,
        dynamic_subtitles=not args.static_subtitles,
        segments=segments,
        highlight_words=not args.no_word_highlight,
        auto_zoom=not args.no_auto_zoom,
        trim_silence=not args.keep_silence,
        silence_threshold=max(0.3, args.silence_threshold),
    )
    for path in rendered:
        print(f"Rendered: {path}")

    copy_files = write_top5_copy(clips, out / "copy", count=count)
    for path in copy_files:
        print(f"Copy: {path}")

    if rendered:
        zip_path = package_clips(rendered, out / "viral_top5_tiktok_3_1.zip", extra_files=copy_files)
        print(f"ZIP: {zip_path}")


if __name__ == "__main__":
    main()
