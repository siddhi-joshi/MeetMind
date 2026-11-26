import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from app.config import get_settings


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def database_path() -> Path:
    return get_settings().meetmind_data_dir / "meetmind.db"


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(database_path(), check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def init_database() -> None:
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                participants TEXT NOT NULL DEFAULT '[]',
                language TEXT NOT NULL DEFAULT 'auto',
                status TEXT NOT NULL,
                duration_seconds REAL NOT NULL DEFAULT 0,
                audio_path TEXT,
                transcript TEXT NOT NULL DEFAULT '',
                segments TEXT NOT NULL DEFAULT '[]',
                summary TEXT NOT NULL DEFAULT '',
                key_points TEXT NOT NULL DEFAULT '[]',
                decisions TEXT NOT NULL DEFAULT '[]',
                action_items TEXT NOT NULL DEFAULT '[]',
                consent_log TEXT NOT NULL DEFAULT '[]',
                ai_provider TEXT NOT NULL DEFAULT '',
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                title TEXT NOT NULL,
                owner TEXT NOT NULL DEFAULT 'Unassigned',
                due_date TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'open',
                source_quote TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_meetings_created ON meetings(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_tasks_meeting ON tasks(meeting_id);
            """
        )
        count = db.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
        if count == 0:
            seed_demo(db)


JSON_FIELDS = {
    "participants",
    "segments",
    "key_points",
    "decisions",
    "action_items",
    "consent_log",
}


def decode_meeting(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for field in JSON_FIELDS:
        result[field] = json.loads(result.get(field) or "[]")
    result["duration_minutes"] = round(result.pop("duration_seconds", 0) / 60, 1)
    return result


def seed_demo(db: sqlite3.Connection) -> None:
    meeting_id = "demo-product-sync"
    now = utc_now()
    transcript = (
        "Priya: We will launch the private beta next Friday with five design partners.\n"
        "Arjun: I will prepare the onboarding checklist by Wednesday.\n"
        "Meera: I will review the consent wording with legal by Thursday.\n"
        "Priya: We decided to keep audio for seven days during the beta."
    )
    action_items = [
        {
            "title": "Prepare the beta onboarding checklist",
            "owner": "Arjun",
            "due_date": "Wednesday",
            "priority": "high",
            "source_quote": "I will prepare the onboarding checklist by Wednesday.",
        },
        {
            "title": "Review consent wording with legal",
            "owner": "Meera",
            "due_date": "Thursday",
            "priority": "high",
            "source_quote": "I will review the consent wording with legal by Thursday.",
        },
    ]
    db.execute(
        """
        INSERT INTO meetings (
            id, title, participants, language, status, duration_seconds, transcript,
            summary, key_points, decisions, action_items, consent_log, ai_provider,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'ready', ?, ?, ?, ?, ?, ?, ?, 'demo', ?, ?)
        """,
        (
            meeting_id,
            "Product beta planning",
            json.dumps(["Priya", "Arjun", "Meera"]),
            "en",
            1860,
            transcript,
            "The team aligned on a private beta launch with five design partners and assigned onboarding and consent-review work.",
            json.dumps([
                "Private beta launches next Friday",
                "Five design partners will join the first cohort",
                "Onboarding and consent review must finish before launch",
            ]),
            json.dumps(["Retain beta meeting audio for seven days"]),
            json.dumps(action_items),
            json.dumps([
                {"participant": "Priya", "status": "granted", "method": "host attestation", "at": now},
                {"participant": "Arjun", "status": "granted", "method": "host attestation", "at": now},
                {"participant": "Meera", "status": "granted", "method": "host attestation", "at": now},
            ]),
            now,
            now,
        ),
    )
    for index, item in enumerate(action_items, start=1):
        db.execute(
            """
            INSERT INTO tasks (id, meeting_id, title, owner, due_date, priority, status, source_quote, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)
            """,
            (
                f"demo-task-{index}",
                meeting_id,
                item["title"],
                item["owner"],
                item["due_date"],
                item["priority"],
                item["source_quote"],
                now,
                now,
            ),
        )

