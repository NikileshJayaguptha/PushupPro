from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..analysis.keypoints import SKELETON
from ..config import get_settings
from ..database import get_db
from ..models import WorkoutSession
from ..schemas import SessionDetail, SessionSummary, SessionUpdate, TraceOut
from ..services import processing

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

ALLOWED_EXT = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
CHUNK = 1024 * 1024


def _get_or_404(db: Session, session_id: uuid.UUID, *options) -> WorkoutSession:
    stmt = select(WorkoutSession).where(WorkoutSession.id == session_id)
    if options:
        stmt = stmt.options(*options)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return obj


@router.post("", response_model=SessionSummary, status_code=status.HTTP_201_CREATED)
async def upload_session(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            f"Unsupported file type. Use one of: {', '.join(sorted(ALLOWED_EXT))}")

    session_id = uuid.uuid4()
    folder = settings.storage_dir / str(session_id)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"original{ext}"
    limit = settings.max_upload_mb * 1024 * 1024
    written = 0
    try:
        with dest.open("wb") as out:
            while chunk := await file.read(CHUNK):
                written += len(chunk)
                if written > limit:
                    raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                        f"Video exceeds {settings.max_upload_mb} MB")
                out.write(chunk)
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    if written == 0:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty")

    session = WorkoutSession(
        id=session_id,
        title=(title or "").strip() or None,
        original_filename=file.filename or dest.name,
        video_path=str(dest),
        status="queued",
    )
    db.add(session)
    db.commit()
    processing.submit(session_id)
    return session


@router.get("", response_model=list[SessionSummary])
def list_sessions(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    stmt = (select(WorkoutSession).order_by(WorkoutSession.created_at.desc())
            .limit(limit).offset(max(0, offset)))
    return db.execute(stmt).scalars().all()


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, session_id, selectinload(WorkoutSession.reps))


@router.patch("/{session_id}", response_model=SessionSummary)
def update_session(session_id: uuid.UUID, body: SessionUpdate, db: Session = Depends(get_db)):
    session = _get_or_404(db, session_id)
    if body.title is not None:
        session.title = body.title.strip() or None
    db.commit()
    return session


@router.get("/{session_id}/trace", response_model=TraceOut)
def get_trace(session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = _get_or_404(db, session_id, selectinload(WorkoutSession.trace))
    if session.trace is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Analysis not finished yet")
    return {**session.trace.data, "skeleton": SKELETON}


@router.post("/{session_id}/reanalyze", response_model=SessionSummary)
def reanalyze(session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = _get_or_404(db, session_id)
    if session.status == "processing":
        raise HTTPException(status.HTTP_409_CONFLICT, "Already processing")
    session.status, session.progress, session.error = "queued", 0.0, None
    db.commit()
    processing.submit(session_id)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = _get_or_404(db, session_id)
    folder = Path(session.video_path).parent
    db.delete(session)
    db.commit()
    storage = get_settings().storage_dir.resolve()
    if folder.resolve().is_relative_to(storage) and folder.resolve() != storage:
        shutil.rmtree(folder, ignore_errors=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")
_MEDIA_TYPES = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime",
                ".webm": "video/webm", ".avi": "video/x-msvideo", ".mkv": "video/x-matroska"}


@router.get("/{session_id}/video")
def stream_video(session_id: uuid.UUID, request: Request, db: Session = Depends(get_db)):
    """Serve the video with HTTP Range support so the player can seek."""
    session = _get_or_404(db, session_id)
    path = Path(session.playback_path or session.video_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video file missing")
    size = path.stat().st_size
    media_type = _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
    headers = {"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=3600"}

    start, end = 0, size - 1
    range_header = request.headers.get("range")
    status_code = 200
    if range_header and (m := _RANGE_RE.fullmatch(range_header.strip())):
        s, e = m.groups()
        if s:
            start = int(s)
            end = min(int(e), size - 1) if e else size - 1
        elif e:  # suffix range: last N bytes
            start = max(0, size - int(e))
        if start > end or start >= size:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
        status_code = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    headers["Content-Length"] = str(end - start + 1)

    def iterfile():
        with path.open("rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                data = f.read(min(CHUNK, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(iterfile(), status_code=status_code, media_type=media_type, headers=headers)

