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

    def generate_story_payload(self, prompt: str, num_scenes: int = 2) -> tuple[dict, str]:
        groq_key = env("GROQ_API")
        if groq_key:
            groq_payload = self._generate_with_groq(prompt, groq_key, num_scenes)
            if groq_payload:
                return groq_payload, "groq-llama-3.3"
                
        if self.gemini_key:
            for model_name in self._candidate_models():
                cloud_payload = self._generate_with_gemini(prompt, model_name, num_scenes)
                if cloud_payload:
                    return cloud_payload, model_name
        return self.fallback_story_payload(prompt), "fallback"

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

    def _generate_with_groq(self, prompt: str, api_key: str, num_scenes: int) -> dict | None:
        instruction = (
            f"You are an expert Hollywood screenwriter and cinematic director generating a {num_scenes}-scene animated short film. "
            "Your writing must be highly creative, atmospheric, and visually stunning. "
            "Return ONLY valid JSON with exactly the following schema: "
            "{ 'story': { 'title': str, 'logline': str, 'tone': str, 'summary': str }, "
            "  'characters': [ { 'name': str, 'role': str, 'voice_style': str, 'visual_description': str } ], "
            "  'scenes': [ { 'title': str, 'duration_sec': int, 'narration': str, 'visual_prompt': str, 'mood': str, 'subtitle_lines': [str], "
            "                'dialogue': [ { 'character_name': str, 'text': str, 'emotion': str } ] } ] } "
            "Constraints: "
            f"1. Use exactly {num_scenes} scenes and 1 to 3 characters. "
            "2. 'visual_prompt' must be highly detailed, cinematic image generation prompts (e.g., 'Cinematic wide shot, cyberpunk alleyway, neon lights reflecting on wet pavement, volumetric fog, 8k, masterpiece'). "
            "3. 'duration_sec' must be an integer between 10 and 14. "
            "4. Make the dialogue engaging and ensure the narrative flows naturally. "
            "Do NOT wrap the JSON in Markdown backticks or add any explanations."
        )
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        validation_feedback = ""
        
        for attempt in range(4):
            try:
                request_text = f"{instruction}\n\nUser prompt: {prompt}"
                if validation_feedback:
                    request_text += f"\n\nYour previous response was invalid. Validation issue: {validation_feedback}. Return purely raw JSON."
                    
                body = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "You output only raw, strictly valid JSON without markdown formatting."},
                        {"role": "user", "content": request_text}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.7
                }
                response = requests.post(url, json=body, headers=headers, timeout=(8, 40))
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                payload = json.loads(content)
                self._validate_payload_shape(payload, num_scenes)
                LOGGER.info("Groq story generation succeeded")
                return payload
            except Exception as exc:
                validation_feedback = str(exc)
                LOGGER.warning("Groq story generation failed on attempt %s: %s", attempt + 1, exc)
                time.sleep(1.5 * (attempt + 1))
        return None

    def _generate_with_gemini(self, prompt: str, model_name: str, num_scenes: int) -> dict | None:
        instruction = (
            f"You are an expert Hollywood screenwriter and cinematic director generating a {num_scenes}-scene animated short film. "
            "Your writing must be highly creative, atmospheric, and visually stunning. "
            "Return ONLY valid JSON with exactly the following schema: "
            "{ 'story': { 'title': str, 'logline': str, 'tone': str, 'summary': str }, "
            "  'characters': [ { 'name': str, 'role': str, 'voice_style': str, 'visual_description': str } ], "
            "  'scenes': [ { 'title': str, 'duration_sec': int, 'narration': str, 'visual_prompt': str, 'mood': str, 'subtitle_lines': [str], "
            "                'dialogue': [ { 'character_name': str, 'text': str, 'emotion': str } ] } ] } "
            "Constraints: "
            f"1. Use exactly {num_scenes} scenes and 1 to 3 characters. "
            "2. 'visual_prompt' must be highly detailed, cinematic image generation prompts (e.g., 'Cinematic wide shot, cyberpunk alleyway, neon lights reflecting on wet pavement, volumetric fog, 8k, masterpiece'). "
            "3. 'duration_sec' must be an integer between 10 and 14. "
            "4. Make the dialogue engaging and ensure the narrative flows naturally. "
            "Do NOT wrap the JSON in Markdown backticks or add any explanations."
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_key}"
        validation_feedback = ""
        for attempt in range(4):
            try:
                request_text = f"{instruction}\n\nUser prompt: {prompt}"
                if validation_feedback:
                    request_text += (
                        "\n\nYour previous response did not match the schema. "
                        f"Return corrected JSON only. Validation issue: {validation_feedback}"
                    )
                body = {
                    "contents": [{"parts": [{"text": request_text}]}],
                    "generationConfig": {"temperature": 0.8, "response_mime_type": "application/json"},
                }
                response = requests.post(url, json=body, timeout=(8, 40))
                response.raise_for_status()
                data = response.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                payload = json.loads(content)
                self._validate_payload_shape(payload, num_scenes)
                LOGGER.info("Gemini story generation succeeded with model %s", model_name)
                return payload
            except Exception as exc:  # pragma: no cover - network failure fallback
                validation_feedback = str(exc)
                LOGGER.warning(
                    "Gemini story generation failed with model %s on attempt %s: %s",
                    model_name,
                    attempt + 1,
                    exc,
                )
                time.sleep(1.5 * (attempt + 1))
        return None

    def _validate_payload_shape(self, payload: dict, num_scenes: int) -> None:
        if not isinstance(payload, dict):
            raise ValueError("Story payload must be a JSON object.")
        if not isinstance(payload.get("story"), dict):
            raise ValueError("Field 'story' must be an object.")
        if not isinstance(payload.get("characters"), list) or not payload["characters"]:
            raise ValueError("Field 'characters' must be a non-empty list.")
        if not isinstance(payload.get("scenes"), list) or len(payload["scenes"]) != num_scenes:
            raise ValueError(f"Field 'scenes' must contain exactly {num_scenes} scenes.")

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
