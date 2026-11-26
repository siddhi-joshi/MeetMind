import json
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import get_settings
from app.database import connection, decode_meeting, init_database, utc_now
from app.services.gemini import analyze_transcript
from app.services.transcription import transcribe_audio
from app.services.tts import synthesize


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings().ensure_directories()
    init_database()
    yield


app = FastAPI(title="MeetMind API", version="0.1.0", lifespan=lifespan)
settings = get_settings()


class TaskUpdate(BaseModel):
    status: str


def get_meeting_or_404(meeting_id: str) -> dict[str, Any]:
    with connection() as db:
        meeting = decode_meeting(db.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone())
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "gemini_configured": bool(settings.gemini_api_key),
        "mode": "connected" if settings.gemini_api_key else "demo",
    }


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    with connection() as db:
        meetings = [decode_meeting(row) for row in db.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 6")]
        tasks = [dict(row) for row in db.execute("SELECT * FROM tasks ORDER BY status DESC, created_at DESC")]
        counts = dict(db.execute(
            "SELECT COUNT(*) AS meetings, COALESCE(SUM(duration_seconds), 0) AS seconds FROM meetings WHERE status = 'ready'"
        ).fetchone())
    return {
        "meetings": meetings,
        "tasks": tasks,
        "stats": {
            "meetings": counts["meetings"],
            "hours_saved": round(counts["seconds"] / 3600 * 0.45, 1),
            "open_tasks": sum(1 for task in tasks if task["status"] != "done"),
        },
        "gemini_configured": bool(settings.gemini_api_key),
    }


@app.get("/api/meetings")
def list_meetings(q: str = "") -> list[dict[str, Any]]:
    with connection() as db:
        if q.strip():
            pattern = f"%{q.strip()}%"
            rows = db.execute(
                "SELECT * FROM meetings WHERE title LIKE ? OR transcript LIKE ? OR summary LIKE ? ORDER BY created_at DESC",
                (pattern, pattern, pattern),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM meetings ORDER BY created_at DESC").fetchall()
    return [decode_meeting(row) for row in rows]


@app.get("/api/meetings/{meeting_id}")
def get_meeting(meeting_id: str) -> dict[str, Any]:
    meeting = get_meeting_or_404(meeting_id)
    with connection() as db:
        meeting["tasks"] = [dict(row) for row in db.execute("SELECT * FROM tasks WHERE meeting_id = ?", (meeting_id,))]
    return meeting


@app.post("/api/meetings", status_code=202)
def create_meeting(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    participants: str = Form(""),
    language: str = Form("auto"),
    consent_confirmed: bool = Form(False),
    audio: UploadFile = File(...),
) -> dict[str, Any]:
    if not consent_confirmed:
        raise HTTPException(status_code=400, detail="Recording consent must be confirmed before upload.")
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Choose an audio file.")

    meeting_id = uuid.uuid4().hex
    suffix = Path(audio.filename).suffix.lower() or ".webm"
    audio_path = settings.meetmind_upload_dir / f"{meeting_id}{suffix}"
    with audio_path.open("wb") as destination:
        shutil.copyfileobj(audio.file, destination)

    names = [name.strip() for name in participants.split(",") if name.strip()]
    now = utc_now()
    consent_log = [
        {"participant": name, "status": "granted", "method": "host attestation", "at": now}
        for name in names
    ]
    with connection() as db:
        db.execute(
            """
            INSERT INTO meetings (id, title, participants, language, status, audio_path, consent_log, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'processing', ?, ?, ?, ?)
            """,
            (meeting_id, title.strip(), json.dumps(names), language, str(audio_path), json.dumps(consent_log), now, now),
        )
    background_tasks.add_task(process_meeting, meeting_id)
    return {"id": meeting_id, "status": "processing"}


def process_meeting(meeting_id: str) -> None:
    meeting = get_meeting_or_404(meeting_id)
    try:
        transcription = transcribe_audio(Path(meeting["audio_path"]), meeting["language"])
        analysis, provider = analyze_transcript(meeting["title"], meeting["participants"], transcription["text"])
        now = utc_now()
        with connection() as db:
            db.execute(
                """
                UPDATE meetings SET status = 'ready', transcript = ?, segments = ?, language = ?,
                    duration_seconds = ?, summary = ?, key_points = ?, decisions = ?, action_items = ?,
                    ai_provider = ?, error = NULL, updated_at = ? WHERE id = ?
                """,
                (
                    transcription["text"],
                    json.dumps(transcription["segments"]),
                    transcription["language"],
                    transcription["duration"],
                    analysis["summary"],
                    json.dumps(analysis["key_points"]),
                    json.dumps(analysis["decisions"]),
                    json.dumps(analysis["action_items"]),
                    provider,
                    now,
                    meeting_id,
                ),
            )
            for item in analysis["action_items"]:
                db.execute(
                    """
                    INSERT INTO tasks (id, meeting_id, title, owner, due_date, priority, status, source_quote, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)
                    """,
                    (
                        uuid.uuid4().hex,
                        meeting_id,
                        item["title"],
                        item.get("owner") or "Unassigned",
                        item.get("due_date") or None,
                        item.get("priority") or "medium",
                        item.get("source_quote") or "",
                        now,
                        now,
                    ),
                )
    except Exception as exc:
        with connection() as db:
            db.execute(
                "UPDATE meetings SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
                (str(exc), utc_now(), meeting_id),
            )


@app.post("/api/meetings/{meeting_id}/read-aloud")
def read_aloud(meeting_id: str, language: str = "en") -> dict[str, str]:
    meeting = get_meeting_or_404(meeting_id)
    if not meeting["summary"]:
        raise HTTPException(status_code=409, detail="The meeting summary is not ready.")
    safe_language = "hi" if language.startswith("hi") else "en"
    output = settings.meetmind_generated_dir / f"{meeting_id}-{safe_language}.wav"
    try:
        if not output.exists():
            synthesize(meeting["summary"], safe_language, output)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"audio_url": f"/generated/{output.name}"}


@app.get("/api/tasks")
def list_tasks() -> list[dict[str, Any]]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT tasks.*, meetings.title AS meeting_title FROM tasks
            JOIN meetings ON meetings.id = tasks.meeting_id
            ORDER BY CASE tasks.status WHEN 'open' THEN 0 ELSE 1 END, tasks.created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, update: TaskUpdate) -> dict[str, Any]:
    if update.status not in {"open", "in_progress", "done"}:
        raise HTTPException(status_code=400, detail="Invalid task status")
    with connection() as db:
        cursor = db.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (update.status, utc_now(), task_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(row)


@app.get("/generated/{filename}")
def generated_audio(filename: str):
    path = settings.meetmind_generated_dir / Path(filename).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path, media_type="audio/wav")


app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")


@app.get("/{path:path}")
def frontend(path: str):
    static_root = Path("static").resolve()
    requested = (static_root / path).resolve()
    if path and requested.is_relative_to(static_root) and requested.is_file():
        return FileResponse(requested)
    return FileResponse(static_root / "index.html")

