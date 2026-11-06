from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from analyzer import generate_prompt_pack, load_platform_profiles, score_videos, winning_pattern

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="AutoShorts Analyzer",
    page_icon="🎬",
    layout="wide",
)

st.title("AutoShorts Analyzer")
st.caption("Generate English AutoShorts.ai prompts for TikTok, YouTube Shorts, X and Facebook Reels.")

profiles = load_platform_profiles()
platform_names = list(profiles.keys())

with st.sidebar:
    st.header("Generator settings")
    niche = st.text_input("Niche", value="Iceland travel, local life and practical travel advice")
    topic = st.text_area(
        "Topic or angle",
        value="A surprising Iceland travel mistake that tourists can avoid",
        height=100,
    )
    platforms = st.multiselect(
        "Platforms",
        platform_names,
        default=platform_names,
    )
    tone = st.selectbox(
        "Tone",
        [
            "conversational, confident and concise",
            "curious and cinematic",
            "practical and trustworthy",
            "fast, punchy and provocative without misleading clickbait",
            "warm, local and experience-based",
        ],
        index=0,
    )
    count_per_platform = st.slider("Prompt variants per platform", 1, 5, 2)
    custom_duration = st.text_input(
        "Custom duration in seconds",
        value="",
        placeholder="Leave blank to use each platform profile",
    )

st.subheader("1. Optional performance data")
st.write(
    "Upload a CSV with previous videos. The analyzer uses it to identify the strongest topic and hook pattern. "
    "If you skip this step, the prompt generator still works."
)

with (BASE_DIR / "sample_metrics.csv").open("rb") as sample_file:
    st.download_button(
        "Download sample CSV",
        data=sample_file.read(),
        file_name="sample_metrics.csv",
        mime="text/csv",
    )

uploaded = st.file_uploader("Upload metrics CSV", type=["csv"])

scored = None
pattern = ""

if uploaded is not None:
    try:
        source = pd.read_csv(uploaded)
        scored = score_videos(source)
        pattern = winning_pattern(scored)

        st.success("Performance data loaded.")
        st.write("Detected winning pattern:")
        st.info(pattern)

        visible_columns = [
            column
            for column in [
                "platform",
                "title",
                "topic",
                "views",
                "avg_view_pct",
                "engagement_rate",
                "shares_per_1k",
                "comments_per_1k",
                "subs_per_1k",
                "viral_score",
            ]
            if column in scored.columns
        ]
        st.dataframe(scored[visible_columns], use_container_width=True)
    except Exception as exc:
        st.error(f"Could not analyze the CSV: {exc}")

st.subheader("2. Generate AutoShorts.ai prompts")

if not platforms:
    st.warning("Select at least one platform.")

if st.button("Generate prompt pack", type="primary", disabled=not platforms):
    prompts = generate_prompt_pack(
        topic=topic,
        niche=niche,
        platforms=platforms,
        count_per_platform=count_per_platform,
        tone=tone,
        custom_duration=custom_duration or None,
        historical_pattern=pattern,
    )

    st.session_state["autoshorts_prompts"] = prompts

prompts = st.session_state.get("autoshorts_prompts", [])

if prompts:
    export_blocks = []

    for item in prompts:
        label = f'{item["platform"]} · Variant {item["variant"]}'
        with st.expander(label, expanded=True):
            st.text_area(
                "Copy this prompt into AutoShorts.ai",
                item["prompt"],
                height=560,
                key=f'prompt-{item["platform"]}-{item["variant"]}',
            )
        export_blocks.append(f"===== {label} =====\n\n{item['prompt']}")

    combined = "\n\n".join(export_blocks)
    st.download_button(
        "Download all prompts as TXT",
        data=combined,
        file_name="autoshorts_prompt_pack.txt",
        mime="text/plain",
    )

    st.download_button(
        "Download prompt pack as JSON",
        data=json.dumps(prompts, ensure_ascii=False, indent=2),
        file_name="autoshorts_prompt_pack.json",
        mime="application/json",
    )

st.subheader("3. Scoring model")
st.write(
    "Viral Score is a heuristic 0-100 score. It weights average viewed percentage most heavily, then "
    "engagement, views relative to your supplied sample, shares, comments and subscriber conversion. "
    "It is a comparison tool, not a guarantee of reach."
)

st.subheader("CSV columns")
st.code(
    "platform,title,topic,hook,views,likes,comments,shares,avg_view_pct,subscribers_gained,duration_seconds"
)
