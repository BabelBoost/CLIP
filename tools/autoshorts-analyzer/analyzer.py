from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PLATFORMS_PATH = BASE_DIR / "platforms.json"

HOOK_FAMILIES = [
    "curiosity gap",
    "costly mistake",
    "myth versus reality",
    "unexpected consequence",
    "local insight",
    "warning with a practical payoff",
    "surprising contrast",
    "mini story with a reveal",
]

DEFAULT_COLUMNS = {
    "views": 0,
    "likes": 0,
    "comments": 0,
    "shares": 0,
    "avg_view_pct": 0,
    "subscribers_gained": 0,
    "duration_seconds": 0,
    "platform": "Unknown",
    "title": "",
    "topic": "",
    "hook": "",
}


def load_platform_profiles() -> dict:
    with PLATFORMS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _number(value) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _relative_score(value: float, median: float, ceiling_ratio: float = 2.0) -> float:
    if value <= 0:
        return 0.0
    if median <= 0:
        return 50.0
    ratio = min(value / median, ceiling_ratio)
    return min(100.0, 50.0 * ratio)


def score_videos(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with normalized metrics and a heuristic Viral Score 0-100."""
    df = frame.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    for column, default in DEFAULT_COLUMNS.items():
        if column not in df.columns:
            df[column] = default

    numeric = [
        "views",
        "likes",
        "comments",
        "shares",
        "avg_view_pct",
        "subscribers_gained",
        "duration_seconds",
    ]
    for column in numeric:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    safe_views = df["views"].clip(lower=1)
    df["engagement_rate"] = (
        (df["likes"] + df["comments"] + df["shares"]) / safe_views * 100
    )
    df["comments_per_1k"] = df["comments"] / safe_views * 1000
    df["shares_per_1k"] = df["shares"] / safe_views * 1000
    df["subs_per_1k"] = df["subscribers_gained"] / safe_views * 1000

    medians = {
        "views": max(float(df["views"].median()), 1.0),
        "engagement_rate": max(float(df["engagement_rate"].median()), 0.01),
        "comments_per_1k": max(float(df["comments_per_1k"].median()), 0.01),
        "shares_per_1k": max(float(df["shares_per_1k"].median()), 0.01),
        "subs_per_1k": max(float(df["subs_per_1k"].median()), 0.01),
    }

    scores = []
    for _, row in df.iterrows():
        view_score = _relative_score(_number(row["views"]), medians["views"], 2.5)
        watch_score = min(100.0, max(0.0, _number(row["avg_view_pct"]) / 1.05))
        engagement_score = _relative_score(
            _number(row["engagement_rate"]), medians["engagement_rate"], 2.2
        )
        comment_score = _relative_score(
            _number(row["comments_per_1k"]), medians["comments_per_1k"], 2.2
        )
        share_score = _relative_score(
            _number(row["shares_per_1k"]), medians["shares_per_1k"], 2.2
        )
        subscriber_score = _relative_score(
            _number(row["subs_per_1k"]), medians["subs_per_1k"], 2.2
        )

        score = (
            view_score * 0.15
            + watch_score * 0.30
            + engagement_score * 0.20
            + share_score * 0.15
            + comment_score * 0.10
            + subscriber_score * 0.10
        )
        scores.append(round(min(100.0, max(0.0, score)), 1))

    df["viral_score"] = scores
    return df.sort_values("viral_score", ascending=False).reset_index(drop=True)


def winning_pattern(scored: pd.DataFrame) -> str:
    if scored is None or scored.empty:
        return "No historical winner supplied. Build around a strong curiosity gap and one clear payoff."

    best = scored.iloc[0]
    parts = []

    topic = str(best.get("topic", "")).strip()
    hook = str(best.get("hook", "")).strip()
    platform = str(best.get("platform", "")).strip()

    if topic:
        parts.append(f"Winning topic family: {topic}.")
    if hook:
        parts.append(f'Winning hook reference: "{hook}".')
    if platform and platform.lower() != "unknown":
        parts.append(f"Best-performing source platform in the supplied sample: {platform}.")

    avg_view = _number(best.get("avg_view_pct", 0))
    share_rate = _number(best.get("shares_per_1k", 0))
    comment_rate = _number(best.get("comments_per_1k", 0))

    strengths = []
    if avg_view >= 90:
        strengths.append("strong completion/rewatch signal")
    if share_rate > 5:
        strengths.append("strong share signal")
    if comment_rate > 3:
        strengths.append("strong comment signal")
    if strengths:
        parts.append("Observed strengths: " + ", ".join(strengths) + ".")

    return " ".join(parts) or "Use the strongest historical topic and hook pattern without copying it."


def _duration_for(profile: dict, custom_duration: str | None) -> str:
    custom = (custom_duration or "").strip()
    return custom if custom else profile["target_seconds"]


def generate_prompt(
    *,
    topic: str,
    niche: str,
    platform: str,
    tone: str = "conversational, confident and concise",
    custom_duration: str | None = None,
    historical_pattern: str = "",
    variation_index: int = 0,
) -> str:
    profiles = load_platform_profiles()
    if platform not in profiles:
        raise ValueError(f"Unsupported platform: {platform}")

    profile = profiles[platform]
    duration = _duration_for(profile, custom_duration)
    hook_family = HOOK_FAMILIES[variation_index % len(HOOK_FAMILIES)]

    history = historical_pattern.strip()
    history_block = (
        f"PERFORMANCE PATTERN TO LEARN FROM:\n{history}\n"
        "Use the psychological mechanism, not the wording. Do not copy the previous video.\n\n"
        if history
        else ""
    )

    return f"""Create ONE original vertical short-form video for {platform} using AutoShorts.ai.

NICHE:
{niche.strip() or "general educational entertainment"}

TOPIC:
{topic.strip() or "Choose one specific, high-curiosity angle inside the niche."}

PRIMARY GOAL:
{profile["primary_goal"]}

TARGET DURATION:
{duration} seconds.

TONE:
{tone}

{history_block}HOOK STRATEGY:
Use a {hook_family}. {profile["hook"]}.
The first spoken sentence must create tension or curiosity immediately.
Do not start with greetings, introductions, "Did you know?", "Today we will...", or generic setup.
Do not reveal the full answer in the first sentence.

STORY STRUCTURE:
0-2 seconds: Immediate hook.
2-7 seconds: Open an information gap and make the consequence or benefit clear.
7-20 seconds: Deliver the core story, fact, mistake, comparison or useful insight.
Middle beat: Add a second reveal, escalation, contrast or "but here is the part people miss" moment.
Final section: Deliver a satisfying practical payoff.
Ending: {profile["ending"]}.

PACING:
{profile["pacing"]}.
Keep sentences short and spoken-English friendly.
Remove filler.
Keep one central idea per video.
Introduce a new visual, fact, question, reveal or tension beat regularly.

VISUAL DIRECTION:
Use 9:16 vertical framing.
Every visual must directly support the narration.
Prefer specific, realistic imagery over generic stock footage.
Change scenes often enough to maintain attention.
Use close details, movement, human context and location shots when relevant.
Do not use visuals that contradict the narration.

CAPTIONS:
Use large, readable burned-in subtitles.
Keep caption chunks short.
Highlight only the strongest words.
Keep important text away from interface-safe areas.

ACCURACY:
Do not invent laws, statistics, prices, quotes, locations, scientific claims or historical facts.
If a factual claim cannot be supported confidently, replace it with a safer angle.
Never exaggerate danger beyond the facts.

VIRAL MECHANICS:
Create curiosity without misleading clickbait.
Make the payoff worth the hook.
Include at least one moment that viewers may want to share, debate, save or rewatch.
Avoid generic listicle language unless the list itself has a strong story.
Do not repeat the same point using different words.

OUTPUT:
Generate the finished short with narration, matching visuals, captions and a concise platform-appropriate ending.
Do not add production notes to the final narration.
"""


def generate_prompt_pack(
    *,
    topic: str,
    niche: str,
    platforms: Iterable[str],
    count_per_platform: int = 1,
    tone: str = "conversational, confident and concise",
    custom_duration: str | None = None,
    historical_pattern: str = "",
) -> list[dict]:
    output = []
    for platform in platforms:
        for index in range(max(1, int(count_per_platform))):
            output.append(
                {
                    "platform": platform,
                    "variant": index + 1,
                    "prompt": generate_prompt(
                        topic=topic,
                        niche=niche,
                        platform=platform,
                        tone=tone,
                        custom_duration=custom_duration,
                        historical_pattern=historical_pattern,
                        variation_index=index,
                    ),
                }
            )
    return output
