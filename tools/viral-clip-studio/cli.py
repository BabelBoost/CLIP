from __future__ import annotations

import argparse
from pathlib import Path

from viralclip import analyze_segments, enrich_with_ollama, render_clip, save_reports, transcribe_video


def main() -> None:
    p = argparse.ArgumentParser(description="Analyze a video and create ranked short-form clip candidates.")
    p.add_argument("video", help="Path to a local video file")
    p.add_argument("--language", default="pl", help="pl, en or auto")
    p.add_argument("--model", default="small", help="Whisper model: tiny/base/small/medium")
    p.add_argument("--mode", choices=["auto", "general", "public_affairs"], default="auto")
    p.add_argument("--ollama", action="store_true", help="Improve copy fields using local Ollama")
    p.add_argument("--ollama-model", default="qwen3:8b")
    p.add_argument("--render", type=int, default=0, help="Render N best clips (e.g. 5)")
    p.add_argument("--output", default="output")
    args = p.parse_args()

    video = Path(args.video)
    out = Path(args.output)
    segments, detected = transcribe_video(video, model_size=args.model, language=None if args.language == "auto" else args.language)
    print(f"Transcription: {len(segments)} segments, language={detected}")
    clips = analyze_segments(segments, top_n=max(10, args.render), content_mode=args.mode)
    if args.ollama:
        clips = enrich_with_ollama(clips, model=args.ollama_model, content_mode=args.mode)
    paths = save_reports(clips, out)
    print(f"Report: {paths['markdown']}")

    for clip in clips[: max(0, args.render)]:
        path = render_clip(video, clip, out / "clips", burn_subtitles=True)
        print(f"Rendered: {path}")


if __name__ == "__main__":
    main()
