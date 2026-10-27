# PushupPro

PushupPro counts push-ups and checks your form from a workout video. It tracks 17 body keypoints per frame with YOLO pose estimation, uses elbow and body-line angles to find each rep and flag form faults, and shows the results in a dashboard with a skeleton overlay, angle charts and weekly progress.

## Features

- Rep counting from any push-up video using YOLO11 pose estimation
- Form checks for shallow depth, incomplete lockout, hip sag and piking
- 0–100 form score for every rep
- Video playback with a live skeleton overlay
- Elbow and body-line angle charts with rep markers
- Weekly progress: reps, form score, best set, common issues and streak
- Camera side and view angle detected automatically

## Quick Start

1. Build and run everything

   ```bash
   docker compose up --build
   ```

2. Open:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000 (API docs at http://localhost:8000/docs)

The first build downloads PyTorch (CPU) and the `yolo11n-pose.pt` weights, so it takes a few minutes.

To fill the dashboard with six weeks of demo data:

```bash
docker compose exec backend python -m scripts.seed_demo
```

For full feedback, film from the side with your whole body in frame. Front-on videos still get rep counts, depth and lockout, but not hip sag or piking.

## Tech Stack

- Frontend: Next.js, React, TypeScript
- Backend: FastAPI, SQLAlchemy
- Analysis: Ultralytics YOLO11 pose, OpenCV, NumPy, ffmpeg
- Database: PostgreSQL

## API Endpoints

- `POST /api/sessions`: upload a video
- `GET /api/sessions`: list sessions
- `GET /api/sessions/{id}`: summary and per-rep metrics for one session
- `GET /api/sessions/{id}/trace`: per-frame keypoints and angle curves
- `GET /api/sessions/{id}/video`: stream the video
- `PATCH /api/sessions/{id}`: rename a session
- `POST /api/sessions/{id}/reanalyze`: run the analysis again
- `DELETE /api/sessions/{id}`: delete a session
- `GET /api/progress/weekly`: weekly progress stats
- `GET /api/health`: health check

## Form Checks

| Fault | Flagged when | Max deduction |
|---|---|---|
| Shallow depth | bottom elbow angle > 100° | 35 |
| Incomplete lockout | top elbow angle < 155° | 25 |
| Hip sag | hips > 15° below the shoulder–ankle line | 25 |
| Piking | hips > 15° above the shoulder–ankle line | 20 |

Thresholds are set in `backend/app/analysis/config.py`.

## Command Line

Analyze a video without running the app:

```bash
cd backend
python -m app.cli analyze my_set.mp4 --json results.json
```

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## Requirements

- Docker
- Python 3.11+ for local development
- A GPU is optional. The Docker image runs on CPU.
