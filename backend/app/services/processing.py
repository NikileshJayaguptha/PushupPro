"""Background video processing: pose analysis, persistence and web transcoding."""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.orm import Session

from ..analysis import AnalysisResult, analyze_video
from ..analysis.pose import get_estimator
from ..config import get_settings
from ..database import SessionLocal
from ..models import Rep, SessionTrace, WorkoutSession

log = logging.getLogger(__name__)

# One worker: pose inference is CPU/GPU bound and the model is shared.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="analysis")


def submit(session_id: uuid.UUID) -> None:
    _executor.submit(process_session, session_id)


def _set(session_id: uuid.UUID, **fields) -> None:
    with SessionLocal() as db:
        db.execute(update(WorkoutSession).where(WorkoutSession.id == session_id).values(**fields))
        db.commit()


def persist_result(db: Session, session: WorkoutSession, result: AnalysisResult) -> None:
    """Write an analysis result onto a session row (replacing any previous one)."""
    s = result.summary
    session.fps = result.fps
    session.width = result.width
    session.height = result.height
    session.duration = result.duration
    session.side = result.side
    session.tracking_quality = result.valid_fraction
    session.rep_count = s["rep_count"]
    session.clean_reps = s["clean_reps"]
    session.avg_score = s["avg_score"]
    session.avg_depth = s["avg_depth"]
    session.summary = s
    session.reps = [Rep(**{k: v for k, v in r.to_dict().items()}) for r in result.reps]
    if session.trace is None:
        session.trace = SessionTrace(data=result.trace)
    else:
        session.trace.data = result.trace
    session.status = "done"
    session.progress = 1.0
    session.error = None


def transcode_for_web(src: Path, dst: Path) -> bool:
    """Re-encode to H.264/AAC MP4 with faststart so every browser can seek it."""
    if not shutil.which("ffmpeg"):
        return False
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(dst),
    ]
    try:
        subprocess.run(cmd, check=True, timeout=900)
        return True
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("Transcode failed for %s: %s", src, exc)
        return False


def process_session(session_id: uuid.UUID) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        session = db.get(WorkoutSession, session_id)
        if session is None:
            return
        video_path = Path(session.video_path)

    _set(session_id, status="processing", progress=0.0, error=None)
    last_write = [0.0]

    def on_progress(p: float) -> None:
        now = time.monotonic()
        if now - last_write[0] > 0.5:  # throttle DB writes
            last_write[0] = now
            _set(session_id, progress=round(p * 0.9, 3))

    try:
        estimator = get_estimator(settings.pose_weights, settings.pose_device)
        result = analyze_video(str(video_path), estimator, max_fps=settings.max_analysis_fps,
                               progress=on_progress)

        playback = None
        if settings.transcode_for_web:
            _set(session_id, progress=0.92)
            dst = video_path.with_name("playback.mp4")
            if transcode_for_web(video_path, dst):
                playback = str(dst)

        with SessionLocal() as db:
            session = db.get(WorkoutSession, session_id)
            if session is None:
                return  # deleted while processing
            persist_result(db, session, result)
            session.playback_path = playback
            db.commit()
        log.info("Session %s analysed: %d reps", session_id, result.summary["rep_count"])
    except Exception as exc:  # noqa: BLE001 - surface any failure to the user
        log.exception("Analysis failed for %s", session_id)
        _set(session_id, status="failed", error=str(exc)[:1000])


def recover_interrupted_jobs() -> None:
    """Re-queue sessions left mid-processing by a restart."""
    with SessionLocal() as db:
        ids = [
            s.id for s in db.query(WorkoutSession)
            .filter(WorkoutSession.status.in_(["queued", "processing"]))
            .all()
        ]
    for sid in ids:
        submit(sid)
