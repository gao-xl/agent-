"""SQLite store for non-secret application state and observation history."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Observation, ObservationRecord


class AppStateStore:
    def __init__(self, database_path: str) -> None:
        self.path = Path(database_path)
        with self._connection() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value_json TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, source TEXT NOT NULL, kind TEXT NOT NULL, value_json TEXT NOT NULL, confidence REAL)")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_setting(self, key: str, default: Any) -> Any:
        with self._connection() as connection:
            row = connection.execute("SELECT value_json FROM settings WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value_json"]) if row else default

    def set_setting(self, key: str, value: Any) -> None:
        with self._connection() as connection:
            connection.execute("INSERT INTO settings(key, value_json) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json", (key, json.dumps(value)))

    def add_observation(self, observation: Observation) -> ObservationRecord:
        timestamp = datetime.now(UTC).isoformat()
        with self._connection() as connection:
            cursor = connection.execute("INSERT INTO observations(timestamp, source, kind, value_json, confidence) VALUES (?, ?, ?, ?, ?)", (timestamp, observation.source, observation.kind, json.dumps(observation.value), observation.confidence))
        return ObservationRecord(id=cursor.lastrowid, timestamp=timestamp, **observation.model_dump())

    def list_observations(self, limit: int = 100) -> list[ObservationRecord]:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM observations ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [ObservationRecord(id=row["id"], timestamp=row["timestamp"], source=row["source"], kind=row["kind"], value=json.loads(row["value_json"]), confidence=row["confidence"]) for row in rows]
