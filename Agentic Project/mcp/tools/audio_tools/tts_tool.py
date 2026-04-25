from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import requests
from requests import HTTPError

from mcp.tools.system_tools.logger_tool import get_logger
from shared.utils.paths import env


LOGGER = get_logger("tts-generator")


def _write_wave(path: Path, duration_sec: float, frequency: int = 440, volume: float = 0.22, sample_rate: int = 22050) -> int:
    total_frames = int(sample_rate * duration_sec)
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for frame in range(total_frames):
            sample = int(volume * 32767 * math.sin(2 * math.pi * frequency * frame / sample_rate))
            wav_file.writeframes(struct.pack("<h", sample))
    return int(duration_sec * 1000)


class TTSGenerator:
    def __init__(self) -> None:
        self.elevenlabs_key = env("ELEVENLABS_API_KEY")
        self.voice_id = env("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")

    def generate(self, text: str, voice_style: str, output_base: Path, voice_seed: int) -> tuple[str, str, int]:
        if self.elevenlabs_key:
            result = self._generate_with_elevenlabs(text, output_base.with_suffix(".mp3"))
            if result:
                return "elevenlabs", str(output_base.with_suffix(".mp3")), result
        duration = max(1.6, min(5.5, len(text.split()) * 0.42))
        output_path = output_base.with_suffix(".wav")
        ms = _write_wave(output_path, duration_sec=duration, frequency=260 + voice_seed * 40)
        return "synthetic", str(output_path), ms

    def _generate_with_elevenlabs(self, text: str, output_path: Path) -> int | None:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.elevenlabs_key,
            "accept": "audio/mpeg",
            "content-type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": env("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
            "voice_settings": {"stability": 0.55, "similarity_boost": 0.72},
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=(8, 60))
            response.raise_for_status()
            output_path.write_bytes(response.content)
            estimated_ms = max(1800, len(text.split()) * 450)
            LOGGER.info("ElevenLabs TTS succeeded for %s words", len(text.split()))
            return estimated_ms
        except HTTPError as exc:
            response = exc.response
            details = ""
            if response is not None:
                try:
                    details = response.text
                except Exception:
                    details = "<unreadable response body>"
            LOGGER.warning(
                "ElevenLabs TTS failed with status %s. Response body: %s",
                response.status_code if response is not None else "unknown",
                details,
            )
            return None
        except Exception as exc:
            LOGGER.warning("ElevenLabs TTS failed, falling back to synthetic audio: %s", exc)
            return None
