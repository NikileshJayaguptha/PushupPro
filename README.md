# PushupPro — AI push-up form coach

Upload a workout video and PushupPro counts every push-up rep and checks your form.
YOLO pose estimation tracks 17 body keypoints per frame; elbow and body-line angles
detect each rep and flag **shallow depth**, **incomplete lockout**, **hip sag** and
**piking**, with a 0–100 form score per rep. A FastAPI backend stores sessions and
per-rep metrics in PostgreSQL, and a Next.js dashboard plays the video with a live
skeleton overlay, charts joint angles with rep markers, and tracks weekly progress.

```
┌──────────────┐  upload   ┌─────────────────────────────┐   SQL   ┌────────────┐
│  Next.js     │ ────────▶ │ FastAPI                     │ ──────▶ │ PostgreSQL │
│  dashboard   │ ◀──────── │  ├─ background worker       │         │ sessions   │
│  :3000       │  JSON +   │  │   YOLO pose → angles →   │         │ reps       │
└──────────────┘  video    │  │   reps → form scores     │         │ traces     │
                  (Range)  │  └─ ffmpeg → H.264 playback │         └────────────┘
                           └─────────────────────────────┘
```

## Quick start (Docker)

```bash
docker compose up --build
```

- Dashboard: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs

The first build downloads the CPU build of PyTorch and bakes the `yolo11n-pose.pt`
weights into the backend image, so it takes a few minutes. Later starts are fast.

Optional: fill the dashboard with six weeks of demo history (stick-figure videos, so
the overlay and charts work like a real upload):

```bash
docker compose exec backend python -m scripts.seed_demo
docker compose exec backend python -m scripts.seed_demo --clear   # replace earlier demo sets
```

### Filming tips

Film from the **side** for full feedback: camera at roughly hip height, 2–3 m away,
whole body (hands to feet) in frame. The side of your body nearest the camera is picked
automatically. Front-on videos still get rep counts, depth and lockout, but the hips and
ankles are hidden behind the torso, so hip sag and piking are skipped (the session page
says so). If tracking drops below 60 % of frames, the page warns you too.

## How the analysis works

All code lives in `backend/app/analysis/`.

| Step | File | What happens |
|---|---|---|
| Pose | `pose.py` | Ultralytics YOLO pose returns 17 COCO keypoints per person. With several people in frame, the most prominent one is picked and then followed frame-to-frame by box centre. Video is sub-sampled to ≤30 fps. |
| Signals | `signals.py` | Picks the camera-facing side by mean keypoint confidence. Per frame: **press height** (shoulders above wrists, in arm lengths), **elbow angle** (shoulder–elbow–wrist) and **body-line deviation** (180° − shoulder–hip–ankle angle, signed + for sag / − for pike from which side of the shoulder→ankle line the hip sits). Falls back to the knee if ankles are out of frame. Gaps ≤0.5 s are interpolated, then a 0.2 s moving median removes jitter. |
| View | `signals.py` | Classifies the camera angle from shoulder width ÷ torso length (≈0 side-on, >1 facing the camera). In a front view the body line is discarded rather than guessed; deviations over 60° are always discarded as tracking errors. |
| Reps | `reps.py` | A hysteresis zig-zag detector finds alternating tops and bottoms of **press height**, so it needs no fixed "up"/"down" angles — a shallow rep is still *counted* and then *flagged*. Press height is used instead of the elbow angle because the elbow reading is unreliable when the arm is foreshortened (e.g. holding the bottom of a rep filmed from the front), which split one paused rep into two in real-footage testing. A rep needs a ≥0.15 arm-length drop, an elbow bend below 135°, and 0.4–10 s duration. Pauses at the top are trimmed so durations and tempo reflect actual movement. |
| Form | `form.py` | Per rep: 5th-percentile elbow angle (depth), 95th-percentile elbow angle within ±0.25 s of the top (lockout), and the 90th percentile of sag and pike over the rep — percentiles so one noisy frame can't decide a verdict. |
| Score | `form.py` | 100 minus penalties. Each fault deducts 30 % of its weight the moment it's flagged, ramping to its full weight at the "worst" threshold. Reps between 90° and 100° depth lose up to 5 points. |

Default thresholds (`config.py`, `AnalysisConfig`):

| Fault | Flagged when | Max deduction |
|---|---|---|
| Shallow depth | bottom elbow angle > 100° (ideal ≤ 90°) | 35 |
| Incomplete lockout | top elbow angle < 155° | 25 |
| Hip sag | hips > 15° below the shoulder–ankle line | 25 |
| Piking | hips > 15° above the line | 20 |

### Analyse a video without the API

```bash
cd backend
python -m app.cli analyze my_set.mp4 --json results.json
```

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/sessions` | Upload a video (`multipart/form-data`: `file`, optional `title`). Analysis starts in the background. |
| `GET` | `/api/sessions` | List sessions, newest first (`limit`, `offset`). |
| `GET` | `/api/sessions/{id}` | Session with status/progress, summary and per-rep metrics. |
| `GET` | `/api/sessions/{id}/trace` | Per-frame keypoints, elbow and body-line curves (for overlay + charts). |
| `GET` | `/api/sessions/{id}/video` | Video stream with HTTP Range support (seekable). |
| `PATCH` | `/api/sessions/{id}` | Rename. |
| `POST` | `/api/sessions/{id}/reanalyze` | Re-run analysis (e.g. after changing thresholds). |
| `DELETE` | `/api/sessions/{id}` | Delete the session and its files. |
| `GET` | `/api/progress/weekly?weeks=8&tz=America/New_York` | Weekly reps, form score, best set, issue rates, streak. |
| `GET` | `/api/health` | Liveness + DB check. |

### Data model

- **sessions** — upload metadata, processing status/progress, video properties, tracked side, tracking quality, rep count, clean reps, average score and depth, summary JSON.
- **reps** — one row per rep: frame/time boundaries, descent/ascent time, bottom and top elbow angle, max sag/pike, score, issues and penalty breakdown.
- **session_traces** — per-frame keypoints and angle curves as JSONB, loaded only by the session view.

Tables are created on startup. Sessions left mid-analysis by a restart are re-queued automatically.

## Local development (without Docker)

```bash
# Postgres
docker run -d --name pushup-db -e POSTGRES_USER=pushup -e POSTGRES_PASSWORD=pushup \
  -e POSTGRES_DB=pushuppro -p 5432:5432 postgres:16-alpine

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu   # or the CUDA build
pip install -r requirements-dev.txt
uvicorn app.main:app --reload            # http://localhost:8000

# Frontend
cd frontend
npm install
npm run dev                              # http://localhost:3000
```

Backend settings (environment variables or `backend/.env`):

| Variable | Default | |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://pushup:pushup@localhost:5432/pushuppro` | Any SQLAlchemy URL; SQLite works for quick tests. |
| `STORAGE_DIR` | `./storage` | Uploaded and transcoded videos. |
| `POSE_WEIGHTS` | `yolo11n-pose.pt` | Swap in `yolo11s-pose.pt` / `yolo11m-pose.pt` for better accuracy at more compute. |
| `POSE_DEVICE` | auto | `cpu`, `cuda:0` or `mps`. |
| `MAX_ANALYSIS_FPS` | `30` | Frames above this rate are skipped. |
| `MAX_UPLOAD_MB` | `500` | |
| `TRANSCODE_FOR_WEB` | `true` | Re-encode to H.264 MP4 so iPhone HEVC/MOV files play in every browser. Needs ffmpeg. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated. |

Frontend: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) — the URL the browser uses to reach the API. It is baked in at build time.

## Tests

```bash
cd backend && pytest
```

30 tests. The analysis tests generate synthetic side-view push-ups with known ground
truth (`app/analysis/synthetic.py`) — clean reps, noise, either facing direction,
variable tempo, low fps, occlusion gaps, front-view detection, and each form fault at
known severity. The API
tests run the full upload → background analysis → results → video streaming → weekly
progress flow against SQLite with a fake pose model replaying synthetic keypoints over
a real encoded video.

## Project layout

```
backend/
  app/
    analysis/       pose estimation, angles, rep detection, form scoring, synthetic data
    routers/        sessions + progress endpoints
    services/       background processing, ffmpeg transcoding
    models.py       SQLAlchemy models (PostgreSQL JSONB for traces)
    main.py         FastAPI app
    cli.py          command-line analysis
  scripts/seed_demo.py
  tests/
frontend/
  app/              dashboard, all sets, session view
  components/       skeleton player, angle charts, rep strip/table, weekly progress, upload
  lib/              API client, types, formatting
docker-compose.yml
```

## Limitations and next steps

- Hip sag and piking need a side view; front-facing videos get counting, depth and lockout only.
- Elbow angles from a front view are projected, so depth readings there are approximate.
- One athlete per video.
- Thresholds are general-purpose defaults; knee push-ups or very wide hand positions may need different depth targets.
- Single worker processes one video at a time; for many users, move processing to a queue (Celery/RQ/Arq) with GPU workers.
- No user accounts; every session is visible to anyone who can reach the API.
