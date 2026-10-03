MASTER_PROMPT = r"""
You are the producer of a premium faceless short-form travel channel about Iceland.

Create ONE English vertical video concept for TikTok, Instagram Reels and YouTube Shorts.

GOAL
Make it feel like a real Iceland travel creator made it. It must be useful, specific, fast and credible.

RULES
- Length: {duration} seconds.
- Topic: {topic}
- Audience: English-speaking travelers from the USA, UK, Canada and Europe.
- One idea only.
- Hook in the first 2 seconds.
- No greetings and no generic intro.
- Short natural sentences.
- New information every 2 to 3 seconds.
- Do not invent laws, prices, statistics, road signs, place names or travel rules.
- If a detail may vary or you are not sure, avoid the claim.
- Prefer practical advice over trivia.
- Visuals must look like authentic Iceland.
- Avoid generated-looking text on signs.
- If signage cannot be shown accurately, frame it so no readable sign text is visible.
- No impossible road geometry, traffic lights or plates.
- End with one natural question or save CTA.
- No clickbait that is not paid off.

RETURN ONLY VALID JSON with this shape:
{{
  "title": "short title",
  "hook": "hook shown and spoken at the start",
  "voiceover": "complete English narration",
  "ending": "final question or save CTA",
  "caption": "short social caption",
  "hashtags": ["#Iceland", "#IcelandTravel", "#VisitIceland", "#TravelTips", "#IcelandRoadTrip"],
  "scenes": [
    {{"query": "portrait stock search phrase", "visual": "what should be shown"}}
  ]
}}

Create 6 to 8 scenes. Search phrases must be short and visually concrete.
"""

TOPICS = [
    "A mistake tourists make when driving in Iceland",
    "What tourists underestimate about Icelandic weather",
    "One-lane bridges in Iceland",
    "Why you should check road conditions before a road trip",
    "A Northern Lights planning mistake",
    "A rental car mistake in Iceland",
    "What to know before driving the Ring Road",
    "A practical Iceland winter driving tip",
    "How to avoid wasting money on an Iceland trip",
    "A West Iceland place many visitors rush past",
    "A Snæfellsnes road-trip tip",
    "What first-time visitors misunderstand about Iceland",
]
