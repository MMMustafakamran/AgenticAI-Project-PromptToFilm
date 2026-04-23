from __future__ import annotations

from pathlib import Path

from mcp.tools.audio_tools.tts_tool import _write_wave


MOOD_FREQUENCIES = {
    "curious": 220,
    "uplifting": 330,
    "tense": 180,
    "calm": 200,
}


def create_bgm_track(mood: str, duration_sec: int, output_path: Path) -> str:
    frequency = MOOD_FREQUENCIES.get(mood, 220)
    _write_wave(output_path, duration_sec=duration_sec, frequency=frequency, volume=0.08)
    return str(output_path)
