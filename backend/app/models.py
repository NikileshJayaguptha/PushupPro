from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkoutSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    original_filename: Mapped[str] = mapped_column(String(255))
    video_path: Mapped[str] = mapped_column(String(500))
    playback_path: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)  
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text)

    fps: Mapped[float | None] = mapped_column(Float)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration: Mapped[float | None] = mapped_column(Float)
    side: Mapped[str | None] = mapped_column(String(10))
    tracking_quality: Mapped[float | None] = mapped_column(Float)

    rep_count: Mapped[int] = mapped_column(Integer, default=0)
    clean_reps: Mapped[int] = mapped_column(Integer, default=0)
    avg_score: Mapped[float | None] = mapped_column(Float)
    avg_depth: Mapped[float | None] = mapped_column(Float)
    summary: Mapped[dict | None] = mapped_column(JSONType)

    reps: Mapped[list["Rep"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Rep.index"
    )
    trace: Mapped["SessionTrace | None"] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )


class Rep(Base):
    __tablename__ = "reps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    index: Mapped[int] = mapped_column(Integer)

    start_frame: Mapped[int] = mapped_column(Integer)
    bottom_frame: Mapped[int] = mapped_column(Integer)
    end_frame: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[float] = mapped_column(Float)
    bottom_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    duration: Mapped[float] = mapped_column(Float)
    descent_time: Mapped[float] = mapped_column(Float)
    ascent_time: Mapped[float] = mapped_column(Float)

    min_elbow_angle: Mapped[float] = mapped_column(Float)
    top_elbow_angle: Mapped[float] = mapped_column(Float)
    max_hip_sag: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_pike: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[float] = mapped_column(Float)
    issues: Mapped[list] = mapped_column(JSONType, default=list)
    penalties: Mapped[dict] = mapped_column(JSONType, default=dict)

    session: Mapped[WorkoutSession] = relationship(back_populates="reps")


class SessionTrace(Base):

    __tablename__ = "session_traces"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True
    )
    data: Mapped[dict] = mapped_column(JSONType)

    session: Mapped[WorkoutSession] = relationship(back_populates="trace")
