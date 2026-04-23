from __future__ import annotations

import contextlib
import shutil
import struct
import wave
from pathlib import Path


def _concat_wavs(dialogue_track_paths: list[str], bgm_track: str | None, output_path: Path) -> str:
    with contextlib.ExitStack() as stack:
        wavs = [stack.enter_context(wave.open(path, "rb")) for path in dialogue_track_paths]
        params = wavs[0].getparams()
        bgm_file = None
        if bgm_track and bgm_track.lower().endswith(".wav"):
            bgm_file = stack.enter_context(wave.open(bgm_track, "rb"))
        with wave.open(str(output_path), "wb") as target:
            target.setparams(params)
            silence = b"\x00\x00" * int(params.framerate * 0.35)
            mixed_frames = bytearray()
            for wav_file in wavs:
                mixed_frames.extend(wav_file.readframes(wav_file.getnframes()))
                mixed_frames.extend(silence)
            if bgm_file and bgm_file.getparams()[:3] == params[:3]:
                bgm_frames = bgm_file.readframes(bgm_file.getnframes())
                target.writeframes(_mix_pcm16(bytes(mixed_frames), bgm_frames))
            else:
                target.writeframes(bytes(mixed_frames))
    return str(output_path)


def _mix_pcm16(primary: bytes, secondary: bytes) -> bytes:
    mixed = bytearray()
    frame_count = max(len(primary), len(secondary)) // 2
    for index in range(frame_count):
        start = index * 2
        primary_sample = struct.unpack("<h", primary[start:start + 2])[0] if start + 2 <= len(primary) else 0
        secondary_sample = struct.unpack("<h", secondary[start:start + 2])[0] if start + 2 <= len(secondary) else 0
        value = max(-32768, min(32767, int(primary_sample * 0.85 + secondary_sample * 0.25)))
        mixed.extend(struct.pack("<h", value))
    return bytes(mixed)


def stitch_audio(dialogue_track_paths: list[str], bgm_track: str | None, output_path: Path) -> str:
    wav_tracks = [path for path in dialogue_track_paths if path.lower().endswith(".wav")]
    if wav_tracks:
        return _concat_wavs(wav_tracks, bgm_track, output_path)
    source = dialogue_track_paths[0] if dialogue_track_paths else bgm_track
    if not source:
        output_path.write_bytes(b"")
        return str(output_path)
    shutil.copyfile(source, output_path)
    return str(output_path)
