"""YOLO pose estimation wrapper: one frame in, one person's 17 keypoints out."""

from __future__ import annotations

import logging
import threading
from typing import Protocol

import numpy as np

log = logging.getLogger(__name__)


class PoseEstimator(Protocol):
    def reset(self) -> None: ...
    def __call__(self, frame_bgr: np.ndarray) -> np.ndarray | None:
        """Return a (17, 3) array of x, y, confidence for the tracked athlete, or None."""
        ...


class YoloPoseEstimator:
    """Ultralytics YOLO pose model (e.g. ``yolo11n-pose.pt``).

    When several people are in frame we keep following the same athlete: the
    first frame picks the most prominent person (box area x confidence) and
    later frames pick the detection closest to the previous one.
    """

    def __init__(self, weights: str = "yolo11n-pose.pt", device: str | None = None,
                 imgsz: int = 640, conf: float = 0.25):
        from ultralytics import YOLO  # heavy import, keep lazy

        self.model = YOLO(weights)
        self.device = device
        self.imgsz = imgsz
        self.conf = conf
        self._prev_center: np.ndarray | None = None

    def reset(self) -> None:
        self._prev_center = None

    def __call__(self, frame_bgr: np.ndarray) -> np.ndarray | None:
        results = self.model.predict(
            frame_bgr, imgsz=self.imgsz, conf=self.conf, device=self.device, verbose=False
        )
        if not results:
            return None
        r = results[0]
        if r.keypoints is None or r.boxes is None or len(r.boxes) == 0:
            return None
        kps = r.keypoints.data.cpu().numpy()          # (N, 17, 3)
        boxes = r.boxes.xyxy.cpu().numpy()            # (N, 4)
        scores = r.boxes.conf.cpu().numpy()           # (N,)
        if kps.ndim != 3 or kps.shape[1] != 17:
            return None
        if kps.shape[2] == 2:  # some exports drop confidences
            kps = np.concatenate([kps, np.ones((*kps.shape[:2], 1))], axis=2)

        centers = np.stack([(boxes[:, 0] + boxes[:, 2]) / 2, (boxes[:, 1] + boxes[:, 3]) / 2], axis=1)
        if self._prev_center is None:
            areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
            best = int(np.argmax(areas * scores))
        else:
            best = int(np.argmin(np.linalg.norm(centers - self._prev_center, axis=1)))
        self._prev_center = centers[best]
        return kps[best].astype(float)


_estimator: PoseEstimator | None = None
_lock = threading.Lock()


def get_estimator(weights: str, device: str | None = None) -> PoseEstimator:
    """Process-wide cached model (loading YOLO takes a second or two)."""
    global _estimator
    with _lock:
        if _estimator is None:
            log.info("Loading pose model %s", weights)
            _estimator = YoloPoseEstimator(weights=weights, device=device)
        return _estimator


def set_estimator(estimator: PoseEstimator | None) -> None:
    """Override the cached estimator (used by tests)."""
    global _estimator
    with _lock:
        _estimator = estimator
