"""Turn raw per-frame keypoints into clean signals: press height, elbow angle, body line."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .config import AnalysisConfig
from .geometry import body_line_deviation, joint_angle
from .keypoints import SIDE_JOINTS


@dataclass
class AngleSignals:
    times: np.ndarray            # seconds, shape (T,)
    elbow_raw: np.ndarray        # degrees, NaN where not measurable
    body_raw: np.ndarray         # signed degrees (+ sag / - pike)
    elbow: np.ndarray            # interpolated + smoothed
    body: np.ndarray
    height: np.ndarray           # shoulders above wrists / arm length (1 = arms straight up, ~0.5 = chest down)
    side: str                    # "left" / "right" - the side facing the camera
    valid_fraction: float        # share of frames with a usable elbow angle
    view: str                    # "side" or "front" (camera angle)
    view_ratio: float | None     # median shoulder-width / torso-length

    @property
    def body_line_reliable(self) -> bool:
        return self.view == "side"


def estimate_view(keypoints: np.ndarray, cfg: AnalysisConfig) -> tuple[str, float | None]:
    """Classify the camera angle from how far apart the two shoulders appear."""
    ratios = []
    c = cfg.min_keypoint_conf
    for f in keypoints:
        if f[5, 2] < c or f[6, 2] < c:
            continue
        hips = [f[i, :2] for i in (11, 12) if f[i, 2] >= c]
        if not hips:
            continue
        shoulder_mid = (f[5, :2] + f[6, :2]) / 2
        torso = float(np.linalg.norm(shoulder_mid - np.mean(hips, axis=0)))
        if torso < 1:
            continue
        ratios.append(float(np.linalg.norm(f[5, :2] - f[6, :2])) / torso)
    if not ratios:
        return "side", None  # nothing to judge by; assume the documented setup
    median = float(np.median(ratios))
    return ("side" if median <= cfg.side_view_max_ratio else "front"), round(median, 2)


def _side_confidence(kps: np.ndarray, side: str) -> float:
    idx = list(SIDE_JOINTS[side].values())
    return float(np.nanmean(kps[:, idx, 2]))


def choose_side(keypoints: np.ndarray) -> str:
    """Pick the body side most visible to the camera across the whole clip."""
    if keypoints.size == 0:
        return "left"
    left = _side_confidence(keypoints, "left")
    right = _side_confidence(keypoints, "right")
    return "left" if (np.nan_to_num(left) >= np.nan_to_num(right)) else "right"


def _frame_angles(frame: np.ndarray, side: str, cfg: AnalysisConfig) -> tuple[float, float]:
    j = SIDE_JOINTS[side]

    def pt(name: str):
        p = frame[j[name]]
        return p if p[2] >= cfg.min_keypoint_conf else None

    shoulder, elbow, wrist, hip = pt("shoulder"), pt("elbow"), pt("wrist"), pt("hip")
    # Fall back to the knee when ankles are out of frame (e.g. cropped video);
    # shoulder-hip-knee still captures sag and pike well.
    foot = pt("ankle")
    if foot is None:
        foot = pt("knee")

    elbow_angle = (
        joint_angle(shoulder, elbow, wrist)
        if shoulder is not None and elbow is not None and wrist is not None
        else math.nan
    )
    body = (
        body_line_deviation(shoulder, hip, foot)
        if shoulder is not None and hip is not None and foot is not None
        else math.nan
    )
    return elbow_angle, body


def interpolate_gaps(values: np.ndarray, times: np.ndarray, max_gap: float) -> np.ndarray:
    """Linearly fill NaN runs no longer than ``max_gap`` seconds."""
    out = values.astype(float).copy()
    valid = ~np.isnan(out)
    if valid.sum() < 2:
        return out
    filled = np.interp(times, times[valid], out[valid])
    # Only accept fills inside short interior gaps.
    i = 0
    n = len(out)
    while i < n:
        if not valid[i]:
            j = i
            while j < n and not valid[j]:
                j += 1
            interior = i > 0 and j < n
            if interior and (times[j] - times[i - 1]) <= max_gap:
                out[i:j] = filled[i:j]
            i = j
        else:
            i += 1
    return out


def moving_median(values: np.ndarray, window: int) -> np.ndarray:
    """Centered moving median that ignores NaNs and keeps NaN where input is NaN."""
    if window <= 1:
        return values.copy()
    half = window // 2
    n = len(values)
    out = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(values[i]):
            continue
        seg = values[max(0, i - half): min(n, i + half + 1)]
        out[i] = np.nanmedian(seg)
    return out


def press_height(keypoints: np.ndarray, cfg: AnalysisConfig) -> np.ndarray:
    """How high the shoulders sit above the wrists, in arm lengths.

    This is what a rep physically *is* (the body going down and back up), and
    unlike the elbow angle it stays reliable when the arms are foreshortened,
    e.g. at the bottom of a rep filmed from the front. Both arms are averaged
    when visible.
    """
    c = cfg.min_keypoint_conf
    n = len(keypoints)
    drops = np.full(n, np.nan)
    arm_lengths = []
    for t, f in enumerate(keypoints):
        vals = []
        for side in ("left", "right"):
            j = SIDE_JOINTS[side]
            sh, el, wr = f[j["shoulder"]], f[j["elbow"]], f[j["wrist"]]
            if sh[2] < c or wr[2] < c:
                continue
            vals.append(wr[1] - sh[1])  # image y grows downward
            if el[2] >= c:
                arm_lengths.append(np.linalg.norm(sh[:2] - el[:2]) + np.linalg.norm(el[:2] - wr[:2]))
        if vals:
            drops[t] = float(np.mean(vals))
    if not arm_lengths:
        return drops
    # Arms are fully visible when extended, so a high percentile is the true length.
    arm = float(np.percentile(arm_lengths, 90))
    return drops / arm if arm > 1 else drops * np.nan


def compute_signals(
    keypoints: np.ndarray, times: np.ndarray, fps: float, cfg: AnalysisConfig
) -> AngleSignals:
    """``keypoints``: (T, 17, 3) array of x, y, confidence (NaN/0 where no person)."""
    times = np.asarray(times, dtype=float)
    side = choose_side(keypoints)
    n = len(times)
    elbow_raw = np.full(n, np.nan)
    body_raw = np.full(n, np.nan)
    for t in range(n):
        elbow_raw[t], body_raw[t] = _frame_angles(keypoints[t], side, cfg)

    view, view_ratio = estimate_view(keypoints, cfg)
    if view != "side":
        body_raw[:] = np.nan  # hips/ankles are occluded; don't report guesses
    body_raw[np.abs(body_raw) > cfg.max_plausible_body_dev_deg] = np.nan

    window = max(1, int(round(cfg.smoothing_window_seconds * fps)) | 1)  # odd
    height = moving_median(interpolate_gaps(press_height(keypoints, cfg), times, cfg.max_gap_seconds), window)
    elbow = moving_median(interpolate_gaps(elbow_raw, times, cfg.max_gap_seconds), window)
    body = moving_median(interpolate_gaps(body_raw, times, cfg.max_gap_seconds), window)
    valid_fraction = float(np.mean(~np.isnan(elbow_raw))) if n else 0.0

    return AngleSignals(
        times=times,
        elbow_raw=elbow_raw,
        body_raw=body_raw,
        elbow=elbow,
        body=body,
        height=height,
        side=side,
        valid_fraction=valid_fraction,
        view=view,
        view_ratio=view_ratio,
    )
