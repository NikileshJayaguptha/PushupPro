FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics

# ffmpeg: web transcoding; libgl/libglib: required by the opencv build ultralytics pulls in.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only torch keeps the image ~1.5 GB instead of ~6 GB with CUDA.
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the pose model into the image so the first analysis doesn't download it.
ARG POSE_MODEL=yolo11n-pose.pt
RUN mkdir -p /app/models && cd /app/models \
 && python -c "from ultralytics import YOLO; YOLO('${POSE_MODEL}')"
ENV POSE_WEIGHTS=/app/models/${POSE_MODEL}

COPY app ./app
COPY scripts ./scripts

ENV STORAGE_DIR=/data/storage
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
