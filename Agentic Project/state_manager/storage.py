from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from shared.utils.paths import DB_PATH, ensure_directories


class SQLiteStorage:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        ensure_directories()
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init_db(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_phase TEXT NOT NULL,
                    current_version TEXT,
                    state_path TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS versions (
                    version_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    trigger_source TEXT NOT NULL,
                    changed_phase TEXT NOT NULL,
                    artifact_paths TEXT NOT NULL,
                    parent_version TEXT,
                    snapshot_path TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id)
                );
                """
            )
