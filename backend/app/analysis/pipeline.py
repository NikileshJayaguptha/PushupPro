"""End-to-end analysis: video -> keypoints -> angle signals -> reps -> form scores."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .config import DEFAULT_CONFIG, AnalysisConfig
from .form import RepResult, evaluate_rep
from .pose import PoseEstimator
from .reps import detect_reps
from .signals import compute_signals

ProgressCallback = Callable[[float], None]


@dataclass
class AnalysisResult:
    fps: float
    width: int
    height: int
    duration: float
    side: str
    view: str
    valid_fraction: float
    reps: list[RepResult]
    summary: dict
    trace: dict = field(repr=False)


def _round_list(arr: np.ndarray, digits: int = 1) -> list:
    return [None if np.isnan(v) else round(float(v), digits) for v in arr]


def summarize(reps: list[RepResult], duration: float, view: str = "side") -> dict:
    n = len(reps)
    checks = {"view": view, "body_line_checked": view == "side"}
    issue_counts = Counter(issue for r in reps for issue in r.issues)
    if n == 0:
        return {
            "rep_count": 0, "avg_score": None, "best_score": None, "worst_score": None,
            "avg_depth": None, "avg_rep_duration": None, "reps_per_minute": None,
            "clean_reps": 0, "issue_counts": {}, **checks,
        }
    scores = [r.score for r in reps]
    active = reps[-1].end_time - reps[0].start_time
    return {
        "rep_count": n,
        "avg_score": round(float(np.mean(scores)), 1),
        "best_score": round(max(scores), 1),
        "worst_score": round(min(scores), 1),
        "avg_depth": round(float(np.mean([r.min_elbow_angle for r in reps])), 1),
        "avg_rep_duration": round(float(np.mean([r.duration for r in reps])), 2),
        "reps_per_minute": round(n / active * 60, 1) if active > 0 else None,
        "clean_reps": sum(1 for r in reps if not r.issues),
        "issue_counts": dict(issue_counts),
        **checks,
    }


def analyze_keypoints(
    keypoints: np.ndarray,
    times: np.ndarray,
    fps: float,
    width: int = 0,
    height: int = 0,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
) -> AnalysisResult:
    """Pure analysis on a (T, 17, 3) keypoint array - no video or model needed."""
    keypoints = np.asarray(keypoints, dtype=float)
    times = np.asarray(times, dtype=float)
    sig = compute_signals(keypoints, times, fps, cfg)
    segments = detect_reps(sig.height, sig.elbow, sig.times, cfg)
    reps = [evaluate_rep(i + 1, seg, sig, cfg) for i, seg in enumerate(segments)]
    duration = float(times[-1]) if len(times) else 0.0

    kp_rounded = [
        None if np.all(np.isnan(f[:, 2])) or np.nanmax(f[:, 2]) <= 0
        else [[round(float(x), 1), round(float(y), 1), round(float(c), 2)] for x, y, c in np.nan_to_num(f)]
        for f in keypoints
    ]
    trace = {
        "times": [round(float(t), 3) for t in times],
        "elbow": _round_list(sig.elbow),
        "body": _round_list(sig.body),
        "height": _round_list(sig.height, 3),
        "elbow_raw": _round_list(sig.elbow_raw),
        "keypoints": kp_rounded,
    }
    return AnalysisResult(
        fps=fps, width=width, height=height, duration=duration,
        side=sig.side, view=sig.view, valid_fraction=round(sig.valid_fraction, 3),
        reps=reps, summary=summarize(reps, duration, sig.view), trace=trace,
    )


def extract_keypoints(
    video_path: str,
    estimator: PoseEstimator,
    max_fps: float = 30.0,
    progress: ProgressCallback | None = None,
) -> tuple[np.ndarray, np.ndarray, float, int, int]:
    """Run pose estimation over a video, sub-sampling to at most ``max_fps``."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open video file")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if not np.isfinite(src_fps) or src_fps <= 0:
        src_fps = 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    stride = max(1, int(round(src_fps / max_fps)))
    fps = src_fps / stride

    estimator.reset()
    frames, times = [], []
    idx = 0
    empty = np.zeros((17, 3))
    try:
        while True:
            ok = cap.grab()
            if not ok:
                break
            if idx % stride == 0:
                ok, frame = cap.retrieve()
                if not ok:
                    break
                # Decoded frames are already rotated per container metadata,
                # so trust their shape over the stream's header dimensions.
                height, width = frame.shape[:2]
                kp = estimator(frame)
                frames.append(kp if kp is not None else empty)
                times.append(idx / src_fps)
                if progress and total:
                    progress(min(0.99, idx / total))
            idx += 1
    finally:
        cap.release()

    if not frames:
        raise ValueError("Video contains no readable frames")
    return np.stack(frames), np.asarray(times), fps, width, height


def analyze_video(
    video_path: str,
    estimator: PoseEstimator,
    cfg: AnalysisConfig = DEFAULT_CONFIG,
    max_fps: float = 30.0,
    progress: ProgressCallback | None = None,
) -> AnalysisResult:
    kps, times, fps, w, h = extract_keypoints(video_path, estimator, max_fps, progress)
    return analyze_keypoints(kps, times, fps, w, h, cfg)
