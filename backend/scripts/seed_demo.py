

from __future__ import annotations

import argparse
import random
import shutil
import uuid
from datetime import datetime, timedelta, timezone

import cv2
import numpy as np

from app.analysis import analyze_keypoints
from app.analysis.keypoints import SKELETON
from app.analysis.synthetic import RepSpec, generate_pushups
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.models import WorkoutSession
from app.services.processing import persist_result, transcode_for_web

DEMO_PREFIX = "Demo · "
W, H, FPS = 1280, 720, 30


def render_video(kps: np.ndarray, path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    floor = np.full((H, W, 3), (214, 220, 222), np.uint8)
    floor[612:] = (92, 104, 110)
    for f in kps:
        img = floor.copy()
        pts = {i: (int(f[i, 0]), int(f[i, 1])) for i in range(17)}
        for a, b in SKELETON:
            cv2.line(img, pts[a], pts[b], (70, 72, 76), 26, cv2.LINE_AA)
        cv2.circle(img, pts[0], 30, (70, 72, 76), -1, cv2.LINE_AA)
        writer.write(img)
    writer.release()


def make_set(rng: random.Random, n_reps: int, skill: float) -> list[RepSpec]:
    reps = []
    for i in range(n_reps):
        fatigue = i / max(1, n_reps - 1)
        bottom = 82 + (1 - skill) * 30 + fatigue * 22 * (1 - skill) + rng.uniform(-4, 6)
        top = 170 - (fatigue * 30 * (1 - skill) if rng.random() < 0.4 else 0) + rng.uniform(-3, 2)
        sag = max(0.0, (1 - skill) * 22 * fatigue + rng.uniform(-4, 6))
        pike = 18.0 if rng.random() < 0.08 * (1 - skill) else 0.0
        reps.append(RepSpec(bottom=bottom, top=top, sag=sag, pike=pike,
                            seconds=rng.uniform(1.3, 2.0) + fatigue * 0.6))
    return reps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weeks", type=int, default=6)
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    init_db()
    settings = get_settings()
    rng = random.Random(args.seed)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        if args.clear:
            for s in db.query(WorkoutSession).filter(WorkoutSession.title.like(f"{DEMO_PREFIX}%")):
                shutil.rmtree(settings.storage_dir / str(s.id), ignore_errors=True)
                db.delete(s)
            db.commit()

        made = 0
        for week in range(args.weeks, -1, -1):
            for _ in range(rng.randint(2, 4)):
                days_ago = week * 7 + rng.randint(0, 6)
                if days_ago > args.weeks * 7:
                    continue
                created = now - timedelta(days=days_ago, hours=rng.randint(0, 10))
                progress = 1 - days_ago / (args.weeks * 7 + 1)      # improves over time
                skill = min(0.8, 0.25 + 0.6 * progress + rng.uniform(-0.1, 0.1))
                n_reps = int(8 + 12 * progress + rng.randint(-2, 3))

                kps, times = generate_pushups(make_set(rng, n_reps, skill), fps=FPS,
                                              noise_px=1.5, seed=rng.randint(0, 10_000))
                sid = uuid.uuid4()
                folder = settings.storage_dir / str(sid)
                folder.mkdir(parents=True, exist_ok=True)
                raw = folder / "original.mp4"
                render_video(kps, raw)
                playback = folder / "playback.mp4"
                has_playback = transcode_for_web(raw, playback)

                session = WorkoutSession(
                    id=sid, created_at=created,
                    title=f"{DEMO_PREFIX}{created.astimezone().strftime('%a %b %-d')}",
                    original_filename="demo.mp4", video_path=str(raw),
                    playback_path=str(playback) if has_playback else None,
                )
                db.add(session)
                persist_result(db, session, analyze_keypoints(kps, times, FPS, W, H))
                db.commit()
                made += 1
                print(f"  {session.title}: {session.rep_count} reps, score {session.avg_score}")
        print(f"Seeded {made} demo sets.")


if __name__ == "__main__":
    main()
