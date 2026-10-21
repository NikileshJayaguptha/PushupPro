from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index: int
    start_frame: int
    bottom_frame: int
    end_frame: int
    start_time: float
    bottom_time: float
    end_time: float
    duration: float
    descent_time: float
    ascent_time: float
    min_elbow_angle: float
    top_elbow_angle: float
    max_hip_sag: float | None
    max_pike: float | None
    score: float
    issues: list[str]
    penalties: dict[str, float]


class SessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    title: str | None
    original_filename: str
    status: str
    progress: float
    error: str | None
    duration: float | None
    rep_count: int
    clean_reps: int
    avg_score: float | None
    avg_depth: float | None


class SessionDetail(SessionSummary):
    fps: float | None
    width: int | None
    height: int | None
    side: str | None
    tracking_quality: float | None
    summary: dict | None
    reps: list[RepOut]


class SessionUpdate(BaseModel):
    title: str | None = None


class TraceOut(BaseModel):
    times: list[float]
    elbow: list[float | None]
    body: list[float | None]
    elbow_raw: list[float | None]
    height: list[float | None] = []
    keypoints: list[list[list[float]] | None]
    skeleton: list[tuple[int, int]]


class WeekStats(BaseModel):
    week_start: str            
    sessions: int
    total_reps: int
    clean_reps: int
    avg_score: float | None
    best_set: int
    avg_depth: float | None
    issue_rates: dict[str, float]   


class ProgressOut(BaseModel):
    weeks: list[WeekStats]
    totals: dict
    issue_labels: dict[str, str]
    issue_tips: dict[str, str]
