from __future__ import annotations

import asyncio
import hashlib
import json
import math
import struct
import threading
import wave
from pathlib import Path

import requests
from requests import HTTPError

from mcp.tools.system_tools.logger_tool import get_logger
from shared.utils.paths import env


LOGGER = get_logger("tts-generator")

EDGE_SOFT_VOICES = [
    "en-US-JennyNeural",
    "en-GB-SoniaNeural",
    "en-AU-NatashaNeural",
]
EDGE_BOLD_VOICES = [
    "en-US-GuyNeural",
    "en-GB-RyanNeural",
    "en-AU-WilliamNeural",
]
EDGE_DEFAULT_VOICES = EDGE_SOFT_VOICES + EDGE_BOLD_VOICES


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


def _run_coro_in_thread(coro) -> None:
    error: list[BaseException] = []

    def runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro)
        except BaseException as exc:  # pragma: no cover - defensive
            error.append(exc)
        finally:
            loop.close()

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error[0]


def _audio_duration_ms(path: Path) -> int:
    from moviepy import AudioFileClip

    clip = AudioFileClip(str(path))
    try:
        return max(1, int(clip.duration * 1000))
    finally:
        clip.close()


class TTSGenerator:
    def __init__(self) -> None:
        self.elevenlabs_key = env("ELEVENLABS_API_KEY")
        self.voice_id = env("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
        self.default_voice = env("EDGE_TTS_DEFAULT_VOICE", "en-US-JennyNeural")
        self.voice_map = self._load_voice_map()

    def generate(
        self,
        text: str,
        voice_style: str,
        character_name: str,
        output_base: Path,
        voice_seed: int = 0,
        preferred_voice_name: str | None = None,
        visual_description: str = "",
    ) -> tuple[str, str, int, str]:
        print(f"\n[INFO] Generating voice for {character_name}...")
        elevenlabs_voice_id = self.resolve_elevenlabs_voice(character_name, voice_style, visual_description)
        elevenlabs_path = output_base.with_suffix(".mp3")
        elevenlabs_result = self._generate_with_elevenlabs(text, elevenlabs_path, elevenlabs_voice_id)
        if elevenlabs_result is not None:
            print(f"[SUCCESS] Voice generated successfully via ElevenLabs!")
            return "elevenlabs", str(elevenlabs_path), elevenlabs_result, elevenlabs_voice_id

        edge_voice_name = self.resolve_voice_name(character_name, voice_style, visual_description)
        edge_path = output_base.with_suffix(".mp3")
        edge_result = self._generate_with_edge_tts(text, edge_path, edge_voice_name)
        if edge_result is not None:
            print(f"[SUCCESS] Voice generated successfully via Edge TTS!")
            return "edge-tts", str(edge_path), edge_result, edge_voice_name

        print(f"[ERROR] Voice generation completely failed for {character_name}")
        raise RuntimeError(f"TTS generation failed for character '{character_name}' on both Edge TTS and ElevenLabs.")

    def resolve_voice_name(self, character_name: str, voice_style: str, visual_description: str = "") -> str:
        if character_name in self.voice_map:
            return self.voice_map[character_name]
        if voice_style in self.voice_map:
            return self.voice_map[voice_style]

        style_key = (voice_style + " " + visual_description + " " + character_name).lower()
        if "female" in style_key or "woman" in style_key or "girl" in style_key:
            pool = EDGE_SOFT_VOICES
        elif "male" in style_key or "man" in style_key or "boy" in style_key:
            pool = EDGE_BOLD_VOICES
        elif any(keyword in style_key for keyword in ("soft", "calm", "warm", "gentle", "reflective", "reassuring")):
            pool = EDGE_SOFT_VOICES
        elif any(keyword in style_key for keyword in ("bold", "strong", "grounded", "energetic", "confident", "deep")):
            pool = EDGE_BOLD_VOICES
        else:
            pool = EDGE_DEFAULT_VOICES

        seed_material = f"{character_name}:{voice_style}".encode("utf-8")
        index = int(hashlib.sha256(seed_material).hexdigest(), 16) % len(pool)
        return pool[index] if pool else self.default_voice

    def resolve_elevenlabs_voice(self, character_name: str, voice_style: str, visual_description: str = "") -> str | None:
        if not self.elevenlabs_key:
            return None
            
        if not hasattr(self, "_elevenlabs_default_voices"):
            try:
                url = "https://api.elevenlabs.io/v1/voices"
                headers = {"xi-api-key": self.elevenlabs_key}
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                self._elevenlabs_female_voices = []
                self._elevenlabs_male_voices = []
                self._elevenlabs_default_voices = []
                
                for v in data.get("voices", []):
                    if "voice_id" not in v:
                        continue
                    vid = v["voice_id"]
                    gender = v.get("labels", {}).get("gender", "").lower()
                    self._elevenlabs_default_voices.append(vid)
                    
                    if gender == "female":
                        self._elevenlabs_female_voices.append(vid)
                    elif gender == "male":
                        self._elevenlabs_male_voices.append(vid)
            except Exception as e:
                LOGGER.warning(f"Failed to fetch ElevenLabs voices: {e}")
                self._elevenlabs_female_voices = []
                self._elevenlabs_male_voices = []
                self._elevenlabs_default_voices = []

        style_key = (voice_style + " " + visual_description + " " + character_name).lower()
        if "female" in style_key or "woman" in style_key or "girl" in style_key:
            pool = self._elevenlabs_female_voices if self._elevenlabs_female_voices else self._elevenlabs_default_voices
        elif "male" in style_key or "man" in style_key or "boy" in style_key:
            pool = self._elevenlabs_male_voices if self._elevenlabs_male_voices else self._elevenlabs_default_voices
        elif any(keyword in style_key for keyword in ("soft", "calm", "warm", "gentle", "reflective", "reassuring")):
            pool = self._elevenlabs_female_voices if self._elevenlabs_female_voices else self._elevenlabs_default_voices
        elif any(keyword in style_key for keyword in ("bold", "strong", "grounded", "energetic", "confident", "deep")):
            pool = self._elevenlabs_male_voices if self._elevenlabs_male_voices else self._elevenlabs_default_voices
        else:
            pool = self._elevenlabs_default_voices
            
        if not pool:
            return self.voice_id
            
        seed_material = f"{character_name}:{voice_style}".encode("utf-8")
        index = int(hashlib.sha256(seed_material).hexdigest(), 16) % len(pool)
        return pool[index]

    def _load_voice_map(self) -> dict[str, str]:
        raw = env("EDGE_TTS_VOICE_MAP")
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            LOGGER.warning("EDGE_TTS_VOICE_MAP is not valid JSON; ignoring it.")
            return {}
        if not isinstance(payload, dict):
            LOGGER.warning("EDGE_TTS_VOICE_MAP must be a JSON object; ignoring it.")
            return {}
        return {str(key): str(value) for key, value in payload.items()}

    def _generate_with_edge_tts(self, text: str, output_path: Path, voice_name: str) -> int | None:
        try:
            import edge_tts
        except ImportError:
            LOGGER.warning("edge-tts is not installed; skipping Edge TTS provider.")
            return None

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            communicate = edge_tts.Communicate(text=text, voice=voice_name)
            _run_coro_in_thread(communicate.save(str(output_path)))
            duration_ms = _audio_duration_ms(output_path)
            LOGGER.info("Edge TTS succeeded with voice %s", voice_name)
            return duration_ms
        except Exception as exc:
            print(f"[WARNING] Edge TTS Error: {exc}")
            LOGGER.warning("Edge TTS failed for voice %s: %s", voice_name, exc)
            return None

    def _generate_with_elevenlabs(self, text: str, output_path: Path, voice_id: str | None) -> int | None:
        if not self.elevenlabs_key or not voice_id:
            return None

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
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
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            duration_ms = _audio_duration_ms(output_path)
            LOGGER.info("ElevenLabs TTS succeeded for %s words", len(text.split()))
            return duration_ms
        except HTTPError as exc:
            response = exc.response
            details = ""
            if response is not None:
                try:
                    details = response.text
                except Exception:  # pragma: no cover - defensive
                    details = "<unreadable response body>"
            print(f"[WARNING] ElevenLabs API Error (Status {response.status_code if response is not None else 'unknown'}): {details}")
            LOGGER.warning(
                "ElevenLabs TTS failed with status %s. Response body: %s",
                response.status_code if response is not None else "unknown",
                details,
            )
            return None
        except Exception as exc:
            print(f"[WARNING] ElevenLabs Error: {exc}")
            LOGGER.warning("ElevenLabs TTS failed: %s", exc)
            return None
