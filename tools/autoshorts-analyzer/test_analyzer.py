import unittest

import pandas as pd

from analyzer import generate_prompt, score_videos, winning_pattern


class AutoShortsAnalyzerTests(unittest.TestCase):
    def test_score_videos_adds_viral_score(self):
        df = pd.DataFrame(
            [
                {
                    "platform": "YouTube Shorts",
                    "title": "Strong",
                    "topic": "Iceland road mistake",
                    "hook": "This road looks safe until it is not",
                    "views": 10000,
                    "likes": 600,
                    "comments": 100,
                    "shares": 150,
                    "avg_view_pct": 95,
                    "subscribers_gained": 40,
                    "duration_seconds": 30,
                },
                {
                    "platform": "YouTube Shorts",
                    "title": "Weak",
                    "topic": "General facts",
                    "hook": "Here are some facts",
                    "views": 1000,
                    "likes": 20,
                    "comments": 2,
                    "shares": 1,
                    "avg_view_pct": 45,
                    "subscribers_gained": 1,
                    "duration_seconds": 30,
                },
            ]
        )

        scored = score_videos(df)

        self.assertIn("viral_score", scored.columns)
        self.assertGreater(scored.iloc[0]["viral_score"], scored.iloc[1]["viral_score"])
        self.assertIn("Iceland road mistake", winning_pattern(scored))

    def test_generate_prompt_is_english_and_platform_specific(self):
        prompt = generate_prompt(
            topic="A common Iceland winter driving mistake",
            niche="Iceland travel",
            platform="TikTok",
            variation_index=1,
        )

        self.assertIn("Create ONE original vertical short-form video for TikTok", prompt)
        self.assertIn("HOOK STRATEGY", prompt)
        self.assertIn("TARGET DURATION", prompt)
        self.assertIn("Do not invent laws", prompt)


if __name__ == "__main__":
    unittest.main()
