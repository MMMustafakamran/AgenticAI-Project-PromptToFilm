from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
OUTPUTS_ROOT = DATA_ROOT / "outputs"
TEMP_ROOT = DATA_ROOT / "temp"
STATE_ROOT = DATA_ROOT / "state_versions"
DB_PATH = DATA_ROOT / "project_state.db"

load_dotenv(PROJECT_ROOT / ".env")


def ensure_directories() -> None:
    for path in (DATA_ROOT, OUTPUTS_ROOT, TEMP_ROOT, STATE_ROOT):
        path.mkdir(parents=True, exist_ok=True)


def env(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key, default)
    if value is None:
        return None
    value = value.strip()
    return value or default
