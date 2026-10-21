from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..analysis import ISSUE_LABELS, ISSUE_TIPS
from ..database import get_db
from ..models import WorkoutSession
from ..schemas import ProgressOut, WeekStats

router = APIRouter(prefix="/api/progress", tags=["progress"])


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


@router.get("/weekly", response_model=ProgressOut)
def weekly_progress(
    weeks: int = Query(8, ge=1, le=52),
    tz: str = Query("UTC", description="IANA time zone used to bucket weeks"),
    db: Session = Depends(get_db),
):
    try:
        zone = ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")

    today = datetime.now(zone).date()
    current = _week_start(today)
    first = current - timedelta(weeks=weeks - 1)
    since = datetime.combine(first, datetime.min.time(), tzinfo=zone).astimezone(timezone.utc)

    sessions = db.execute(
        select(WorkoutSession)
        .where(WorkoutSession.status == "done", WorkoutSession.created_at >= since)
        .options(selectinload(WorkoutSession.reps))
    ).scalars().all()

    buckets: dict[date, list[WorkoutSession]] = defaultdict(list)
    for s in sessions:
        created = s.created_at if s.created_at.tzinfo else s.created_at.replace(tzinfo=timezone.utc)
        buckets[_week_start(created.astimezone(zone).date())].append(s)

    out: list[WeekStats] = []
    for i in range(weeks):
        wk = first + timedelta(weeks=i)
        group = buckets.get(wk, [])
        reps = [r for s in group for r in s.reps]
        issues = Counter(issue for r in reps for issue in r.issues)
        n = len(reps)
        out.append(WeekStats(
            week_start=wk.isoformat(),
            sessions=len(group),
            total_reps=n,
            clean_reps=sum(1 for r in reps if not r.issues),
            avg_score=round(sum(r.score for r in reps) / n, 1) if n else None,
            best_set=max((s.rep_count for s in group), default=0),
            avg_depth=round(sum(r.min_elbow_angle for r in reps) / n, 1) if n else None,
            issue_rates={k: round(issues.get(k, 0) / n, 3) if n else 0.0 for k in ISSUE_LABELS},
        ))

    this_week, last_week = out[-1], (out[-2] if len(out) > 1 else None)
    all_reps = sum(w.total_reps for w in out)
    scored = [(w.avg_score, w.total_reps) for w in out if w.avg_score is not None]
    # Consecutive weeks (ending this week or last) with at least one session.
    streak = 0
    for w in reversed(out[:-1] if this_week.sessions == 0 else out):
        if w.sessions == 0:
            break
        streak += 1

    totals = {
        "sessions": sum(w.sessions for w in out),
        "reps": all_reps,
        "avg_score": round(sum(s * n for s, n in scored) / sum(n for _, n in scored), 1) if scored else None,
        "best_set": max((w.best_set for w in out), default=0),
        "week_streak": streak,
        "this_week_reps": this_week.total_reps,
        "last_week_reps": last_week.total_reps if last_week else 0,
        "this_week_score": this_week.avg_score,
        "last_week_score": last_week.avg_score if last_week else None,
    }
    return ProgressOut(weeks=out, totals=totals, issue_labels=ISSUE_LABELS, issue_tips=ISSUE_TIPS)
