from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def create_bgm_track(mood: str, duration_sec: int, output_path: Path) -> str:
    sample_rate = 22050
    total_frames = int(sample_rate * duration_sec)

    # High-quality harmonic ambient pads per mood
    mood_chords = {
        "curious": [110.0, 138.59, 164.81, 207.65],   # A major7
        "uplifting": [146.83, 185.00, 220.0, 277.18],  # D major7
        "tense": [73.416, 87.307, 110.0, 130.81],      # D minor7
        "calm": [130.81, 164.81, 196.00, 246.94],      # C major7
    }
    
    # Fallback to calm chord if mood is unspecified
    freqs = mood_chords.get(mood.lower(), mood_chords["calm"])

    with wave.open(str(output_path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        # Plays a rich, full ambient chord where all notes resonate together
        for frame in range(total_frames):
            time_sec = frame / sample_rate
            sample = 0.0

            # Layer all notes in the chord simultaneously
            for i, frequency in enumerate(freqs):
                # Gentle volume/tremolo modulation (LFO) for that warm analog synth feel
                lfo = 0.6 + 0.4 * math.sin(2 * math.pi * (0.15 + i * 0.08) * time_sec)
                
                # Main tone
                wave_val = math.sin(2 * math.pi * frequency * time_sec)
                # Overtone for a soft, warm organ/synth texture
                overtone = 0.35 * math.sin(4 * math.pi * frequency * time_sec)
                
                sample += (wave_val + overtone) * lfo

            # Normalize across chord notes and apply clean soft clipping
            sample = max(-1.0, min(1.0, (sample / len(freqs)) * 0.45))
            
            # Smooth master volume fade-in and fade-out over 2 seconds
            if time_sec < 2.0:
                sample *= (time_sec / 2.0)
            elif time_sec > duration_sec - 2.0:
                sample *= (max(0.0, duration_sec - time_sec) / 2.0)

            wav_val = int(sample * 32767)
            wav_file.writeframes(struct.pack("<h", wav_val))

    return str(output_path)
