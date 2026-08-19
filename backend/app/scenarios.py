"""Scenario storage and deliberately conservative import/optimization helpers."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .models import Scenario, ScenarioEvent, ScenarioImport, ScenarioOptimization


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ScenarioStore:
    def __init__(self, database_path: str = "edgeplay.db") -> None:
        self.path = Path(database_path)
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                  id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  source TEXT NOT NULL,
                  events_json TEXT NOT NULL,
                  revision INTEGER NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Scenario:
        return Scenario(
            id=row["id"], name=row["name"], source=row["source"],
            events=[ScenarioEvent.model_validate(item) for item in json.loads(row["events_json"])],
            revision=row["revision"], created_at=row["created_at"], updated_at=row["updated_at"],
        )

    def list(self) -> list[Scenario]:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM scenarios ORDER BY updated_at DESC").fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, scenario_id: str) -> Scenario | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        return self._from_row(row) if row else None

    def import_scenario(self, payload: ScenarioImport) -> Scenario:
        events = parse_scenario(payload.content)
        timestamp = utc_now()
        scenario = Scenario(name=payload.name, source=payload.content, events=events, created_at=timestamp, updated_at=timestamp)
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO scenarios VALUES (?, ?, ?, ?, ?, ?, ?)",
                (scenario.id, scenario.name, scenario.source, json.dumps([event.model_dump() for event in events]), scenario.revision, timestamp, timestamp),
            )
        return scenario


def parse_scenario(content: str) -> list[ScenarioEvent]:
    """Accept structured JSON; plain text remains a safe narrative-only event."""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return [ScenarioEvent(type="narrative", payload={"text": content.strip()})]
    if isinstance(parsed, dict):
        parsed = parsed.get("events", [parsed])
    if not isinstance(parsed, list):
        raise ValueError("剧本 JSON 必须是事件数组，或包含 events 数组")
    return [ScenarioEvent.model_validate(item) for item in parsed]


def optimize_scenario(scenario: Scenario) -> ScenarioOptimization:
    """Offline deterministic optimizer. It never creates direct device commands."""
    event_types = {event.type for event in scenario.events}
    suggestions = ["将关键转折拆成短事件，便于在控制台中手动确认。"]
    if "audio" not in event_types:
        suggestions.append("可加入 audio 事件，为前端音频模块提供提示点。")
    if "narrative" in event_types:
        suggestions.append("叙事事件只提供文案与提示，不应直接转换为设备动作。")
    return ScenarioOptimization(
        summary=f"已分析《{scenario.name}》：{len(scenario.events)} 个事件；当前使用本地规则优化器。",
        suggestions=suggestions,
        safety_notes=["生理或视觉观察仅用于提示与人工复核，不能作为自动设备强度升级依据。", "设备动作仍受全局上限、持续时间和紧急停止开关限制。"],
        suggested_settings={"max_duration_ms": 5_000, "require_confirmation": True},
    )
