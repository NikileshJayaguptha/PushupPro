# PushupPro

An AI push-up form coach. Upload a workout video and PushupPro counts your reps and checks your form.

## What it does

- Tracks 17 body keypoints in every frame using YOLO pose estimation
- Counts each push-up rep from the video
- Flags common form mistakes: shallow depth, incomplete lockout, hip sag and piking
- Gives every rep a form score out of 100
- Plays your video back with a live skeleton overlay and charts of your joint angles
- Tracks your weekly progress

Built with FastAPI, PostgreSQL, Next.js and Docker.

## How to run

1. Install and open [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. In this folder, run:

   ```bash
   docker compose up --build
   ```

   The first build takes a few minutes. Later starts are quick.

3. Open http://localhost:3000 and upload a push-up video.

To stop it, press `Ctrl+C` or run `docker compose down`.

**Optional:** load sample workout history to see the progress charts filled in:

```bash
docker compose exec backend python -m scripts.seed_demo
```

## Filming tips

For the best results, film from the side at about hip height, with your whole body in frame. Videos filmed from the front still get rep counts, depth and lockout, but hip sag and piking can't be checked.
