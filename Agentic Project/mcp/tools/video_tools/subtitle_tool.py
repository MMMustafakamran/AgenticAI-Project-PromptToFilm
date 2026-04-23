from __future__ import annotations

from pathlib import Path

from shared.schemas.project_state import TimingManifestEntry


def _ms_to_timestamp(total_ms: int) -> str:
    seconds, milliseconds = divmod(total_ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def write_subtitles(entries: list[TimingManifestEntry], output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    for index, entry in enumerate(entries, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{_ms_to_timestamp(entry.start_ms)} --> {_ms_to_timestamp(entry.end_ms)}",
                    f"{entry.character_name}: {entry.text}",
                ]
            )
        )
    output_path.write_text("\n\n".join(blocks), encoding="utf-8")
    return str(output_path)
