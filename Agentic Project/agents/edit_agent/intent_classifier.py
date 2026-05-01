from __future__ import annotations

import re
from typing import Literal

from shared.schemas.project_state import ProjectState


EditTarget = Literal["script", "audio", "video_frame", "video"]


def classify_edit(command: str, state: ProjectState) -> tuple[str, EditTarget, dict[str, str | int | bool | None]]:
    import json
    import requests
    from shared.utils.paths import env

    groq_api_key = env("GROQ_API")
    if not groq_api_key:
        raise RuntimeError("GROQ_API key is not configured in .env")

    context = f"Characters: {[c.name for c in state.characters]}\nScenes: {[s.scene_id for s in state.scenes]}\n"
    
    system_prompt = f"""You are an intent classification agent for a video editing pipeline.
Available targets: "script", "audio", "video_frame", "video".
Analyze the user's command and determine what they want to change.
{context}

Output ONLY valid JSON matching this schema exactly:
{{
  "intent": "string (e.g. change_voice_tone, adjust_scene_visuals, toggle_subtitles, regenerate_script)",
  "target": "string (MUST BE one of: script, audio, video_frame, video)",
  "details": {{
    "scene_id": "string or null",
    "character_id": "string or null",
    "tone": "string or null",
    "visual_change": "string or null",
    "subtitles_enabled": "boolean or null",
    "duration_delta": "integer or null"
  }}
}}"""

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(result)
        
        target = parsed.get("target", "script")
        if target not in ["script", "audio", "video_frame", "video"]:
            target = "script"
            
        return parsed.get("intent", "regenerate_script"), target, parsed.get("details", {})
    except Exception as exc:
        print(f"Groq API Error: {exc}")
        # Fallback if API fails
        return "regenerate_script", "script", {}
