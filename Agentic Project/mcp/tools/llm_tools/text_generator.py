from __future__ import annotations

import json
import time
from textwrap import shorten

import requests

from mcp.tools.system_tools.logger_tool import get_logger
from shared.utils.paths import env


LOGGER = get_logger("story-generator")


class StoryGenerator:
    def __init__(self) -> None:
        self.gemini_key = env("GEMINI_API_KEY")
        self.gemini_model = env("GEMINI_MODEL", "gemini-2.0-flash")
        self.gemini_fallback_model = env("GEMINI_FALLBACK_MODEL", "gemini-2.0-flash")
        self.gemini_fallback_models = env(
            "GEMINI_FALLBACK_MODELS",
            "gemini-2.5-flash-lite,gemini-2.0-flash,gemini-2.0-flash-lite",
        )

    def generate_story_payload(self, prompt: str) -> dict:
        if self.gemini_key:
            for model_name in self._candidate_models():
                cloud_payload = self._generate_with_gemini(prompt, model_name)
                if cloud_payload:
                    return cloud_payload
        return self.fallback_story_payload(prompt)

    def fallback_story_payload(self, prompt: str) -> dict:
        return self._generate_fallback(prompt)

    def _candidate_models(self) -> list[str]:
        csv_models = []
        if self.gemini_fallback_models:
            csv_models = [model.strip() for model in self.gemini_fallback_models.split(",") if model.strip()]
        models = [self.gemini_model, self.gemini_fallback_model, *csv_models]
        ordered: list[str] = []
        for model in models:
            if model and model not in ordered:
                ordered.append(model)
        return ordered

    def _generate_with_gemini(self, prompt: str, model_name: str) -> dict | None:
        instruction = (
            "You are generating a 2-scene animated short film plan. "
            "Return only valid JSON with keys story, characters, scenes. "
            "Use exactly 2 scenes and between 1 and 3 characters. "
            "Each scene must include title, duration_sec, narration, visual_prompt, mood, subtitle_lines, dialogue. "
            "Each dialogue item must include character_name, text, emotion."
        )
        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"{instruction}\n\nUser prompt: {prompt}",
                        }
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.8, "response_mime_type": "application/json"},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"
        for attempt in range(3):
            try:
                response = requests.post(url, json=body, timeout=(8, 40))
                response.raise_for_status()
                data = response.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                LOGGER.info("Gemini story generation succeeded with model %s", model_name)
                return json.loads(content)
            except Exception as exc:  # pragma: no cover - network failure fallback
                LOGGER.warning(
                    "Gemini story generation failed with model %s on attempt %s: %s",
                    model_name,
                    attempt + 1,
                    exc,
                )
                time.sleep(1.5 * (attempt + 1))
        return None

    def _generate_fallback(self, prompt: str) -> dict:
        subject = shorten(prompt, width=80, placeholder="...")
        protagonist = "Aanya"
        companion = "Rafi"
        return {
            "story": {
                "title": f"Echoes of {subject.title()[:32]}",
                "logline": f"{protagonist} and {companion} chase a sudden discovery sparked by: {subject}",
                "tone": "hopeful cinematic",
                "summary": (
                    f"Using the user prompt as inspiration, {protagonist} uncovers an unusual turning point, "
                    f"and {companion} helps transform it into a brief emotional payoff."
                ),
            },
            "characters": [
                {
                    "name": protagonist,
                    "role": "curious lead",
                    "voice_style": "warm, reflective, youthful",
                    "visual_description": "short silver jacket, expressive eyes, determined posture",
                },
                {
                    "name": companion,
                    "role": "supportive partner",
                    "voice_style": "calm, grounded, reassuring",
                    "visual_description": "earth-toned coat, patient smile, practical explorer gear",
                },
            ],
            "scenes": [
                {
                    "title": "The Unexpected Signal",
                    "duration_sec": 12,
                    "narration": (
                        f"In a world shaped by {subject}, Aanya notices a clue that feels too alive to ignore."
                    ),
                    "visual_prompt": (
                        f"Animated cinematic concept art of a dramatic discovery inspired by {subject}, "
                        "glowing accents, expressive characters, painterly detail, storybook lighting"
                    ),
                    "mood": "curious",
                    "subtitle_lines": [
                        "Something in the air feels different.",
                        "That signal is coming from just ahead.",
                    ],
                    "dialogue": [
                        {"character_name": protagonist, "text": "Something in the air feels different.", "emotion": "curious"},
                        {"character_name": companion, "text": "That signal is coming from just ahead.", "emotion": "focused"},
                    ],
                },
                {
                    "title": "Turning the Discovery Into Hope",
                    "duration_sec": 12,
                    "narration": (
                        f"The clue opens into a moment of wonder, and the mystery behind {subject} becomes a promise."
                    ),
                    "visual_prompt": (
                        f"Animated short film frame inspired by {subject}, emotional reveal, soft dramatic light, "
                        "hopeful horizon, polished illustration"
                    ),
                    "mood": "uplifting",
                    "subtitle_lines": [
                        "We were meant to find this together.",
                        "Then let's make sure the story doesn't end here.",
                    ],
                    "dialogue": [
                        {"character_name": protagonist, "text": "We were meant to find this together.", "emotion": "wonder"},
                        {"character_name": companion, "text": "Then let's make sure the story doesn't end here.", "emotion": "hopeful"},
                    ],
                },
            ],
        }
