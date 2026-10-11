# AutoShorts Analyzer

AutoShorts Analyzer is a small Streamlit tool that turns a topic plus optional historical short-form performance data into ready-to-paste English prompts for AutoShorts.ai.

Supported output profiles:

- TikTok
- YouTube Shorts
- X
- Facebook Reels

## What it does

1. Accepts a niche and topic.
2. Optionally reads a CSV of previous short-form results.
3. Calculates a heuristic `Viral Score 0-100`.
4. Detects the strongest supplied topic and hook pattern.
5. Generates new English AutoShorts.ai prompts without copying the winning video.
6. Adapts pacing, hook style, ending and duration to each selected platform.
7. Exports the prompt pack as TXT or JSON.

## Run on Windows

Open Command Prompt or PowerShell in this folder:

```powershell
cd tools\autoshorts-analyzer
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Streamlit will open the app in your browser.

## Quick start

You do not need analytics data for the first run.

1. Enter your niche.
2. Enter one topic or angle.
3. Select TikTok, YouTube Shorts, X or Facebook Reels.
4. Choose how many variants you want.
5. Click **Generate prompt pack**.
6. Copy a generated English prompt into AutoShorts.ai.

## Using performance data

Use the sample file `sample_metrics.csv` as a template.

Expected columns:

```text
platform,title,topic,hook,views,likes,comments,shares,avg_view_pct,subscribers_gained,duration_seconds
```

Missing numeric columns are treated as zero.

The score uses:

- average viewed percentage
- engagement rate
- views relative to the supplied sample
- shares per 1,000 views
- comments per 1,000 views
- subscribers gained per 1,000 views

Average viewed percentage carries the largest weight.

The score is intentionally heuristic. It helps compare your own clips. It does not guarantee that a clip will go viral.

## Recommended workflow

```text
AutoShorts.ai
    ↓
Publish short
    ↓
Collect results after a consistent measurement window
    ↓
Add results to CSV
    ↓
AutoShorts Analyzer
    ↓
Find winning content pattern
    ↓
Generate new prompt variants
    ↓
AutoShorts.ai
```

Use a consistent measurement window when comparing videos, for example results collected after the same number of hours or days.

## Platform behavior

### TikTok

Prompts favor fast pattern changes, strong curiosity, comments and shares.

### YouTube Shorts

Prompts favor engaged views, completion, rewatch potential and subscriber conversion.

### X

Prompts favor immediate context, compact pacing and reply/repost potential.

### Facebook Reels

Prompts favor clarity, practical value, watch-through and sharing.

## Factual content

Generated prompts explicitly tell AutoShorts.ai not to invent statistics, laws, prices, quotes, locations or historical claims. For factual or high-stakes topics, verify the finished script before publishing.

## Files

```text
app.py              Streamlit interface
analyzer.py         scoring and prompt engine
platforms.json      platform profiles
sample_metrics.csv  example analytics input
requirements.txt    Python dependencies
```
