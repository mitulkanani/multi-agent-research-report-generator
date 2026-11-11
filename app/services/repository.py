import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any


class ResearchRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self._lock = RLock()
        parent = Path(database_path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.database_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS research_runs (
                run_id TEXT PRIMARY KEY, topic TEXT NOT NULL, status TEXT NOT NULL,
                created_at TEXT NOT NULL, completed_at TEXT, payload_json TEXT NOT NULL)""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_created ON research_runs(created_at DESC)")

    def save(self, run_id: str, topic: str, status: str, created_at: str, completed_at: str | None, payload: dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO research_runs(run_id,topic,status,created_at,completed_at,payload_json) VALUES(?,?,?,?,?,?)",
                (run_id, topic, status, created_at, completed_at, json.dumps(payload, default=str)),
            )

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM research_runs WHERE run_id=?", (run_id,)).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT payload_json FROM research_runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]
