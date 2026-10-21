import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="pushuppro-test-"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp / 'test.db'}")
os.environ.setdefault("STORAGE_DIR", str(_tmp / "storage"))

import cv2  
import numpy as np  
import pytest

from app.analysis.pose import set_estimator  
from app.analysis.synthetic import RepSpec, generate_pushups  


class ReplayEstimator:

    def __init__(self, keypoints: np.ndarray):
        self.kps = keypoints
        self.i = 0

    def reset(self):
        self.i = 0

    def __call__(self, frame):
        kp = self.kps[min(self.i, len(self.kps) - 1)]
        self.i += 1
        return kp


@pytest.fixture(scope="session")
def workout():
    specs = [RepSpec(), RepSpec(), RepSpec(bottom=118), RepSpec(sag=24)]
    kps, times = generate_pushups(specs, fps=30)
    path = _tmp / "workout.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30, (320, 240))
    for i in range(len(kps)):
        frame = np.full((240, 320, 3), 40, np.uint8)
        cv2.putText(frame, str(i), (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        writer.write(frame)
    writer.release()
    return {"path": path, "kps": kps, "frames": len(kps), "specs": specs}


@pytest.fixture()
def client(workout):
    from fastapi.testclient import TestClient

    from app.main import app

    set_estimator(ReplayEstimator(workout["kps"]))
    with TestClient(app) as c:
        yield c
    set_estimator(None)
