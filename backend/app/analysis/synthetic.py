"""Synthetic side-view push-up keypoints.

Used by the test-suite to check rep counting and every form fault against a
known ground truth, and by ``scripts/seed_demo.py`` to fill the dashboard with
sample history without needing real videos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .keypoints import KP


@dataclass
class RepSpec:
    bottom: float = 85.0     # elbow angle at the bottom (deg)
    top: float = 170.0       # elbow angle at the top that ends the rep
    sag: float = 0.0         # hip sag at the bottom (deg, body-line deviation)
    pike: float = 0.0        # hip pike throughout the rep (deg)
    seconds: float = 1.6


def _hip_offset_for_deviation(a: float, b: float, dev_deg: float) -> float:
    """Perpendicular hip offset that bends the body line by ``dev_deg`` at the hip."""
    target = math.radians(abs(dev_deg))
    lo, hi = 0.0, min(a, b)
    for _ in range(50):
        mid = (lo + hi) / 2
        if math.atan(mid / a) + math.atan(mid / b) < target:
            lo = mid
        else:
            hi = mid
    return lo if dev_deg >= 0 else -lo


def _pose(elbow_deg: float, body_dev: float, facing: str, scale: float = 1.0) -> np.ndarray:
    U, F = 95.0 * scale, 90.0 * scale          # upper arm / forearm lengths (px)
    floor = 600.0
    wrist = np.array([700.0, floor])
    ankle = np.array([700.0 - 430.0 * scale, floor - 10.0])

    # Forearm stays near vertical over the wrist; the upper arm rotates so the
    # shoulder travels down and slightly forward as the elbow bends.
    phi = math.pi - math.radians(elbow_deg)        # upper arm angle from vertical
    elbow = wrist + np.array([0.0, -F])
    shoulder = elbow + U * np.array([math.sin(phi), -math.cos(phi)])

    line = ankle - shoulder
    L = float(np.linalg.norm(line))
    t_hip = 0.55
    on_line = shoulder + t_hip * line
    normal = np.array([-line[1], line[0]]) / L
    if normal[1] < 0:
        normal = -normal  # point "down" in image space
    off = _hip_offset_for_deviation(t_hip * L, (1 - t_hip) * L, body_dev)
    hip = on_line + off * normal
    knee = (hip + ankle) / 2 + np.array([0.0, 3.0])
    nose = shoulder + np.array([45.0 * scale, -10.0 * scale])

    near = {
        "shoulder": shoulder, "elbow": elbow, "wrist": wrist,
        "hip": hip, "knee": knee, "ankle": ankle,
    }
    kps = np.zeros((17, 3))
    kps[KP["nose"]] = [*nose, 0.95]
    kps[KP["left_eye"]] = [*(nose + [-5, -6]), 0.9]
    kps[KP["right_eye"]] = [*(nose + [-5, -6]), 0.6]
    kps[KP["left_ear"]] = [*(nose + [-25, -2]), 0.85]
    kps[KP["right_ear"]] = [*(nose + [-25, -2]), 0.4]
    near_side, far_side = ("left", "right")
    for joint, p in near.items():
        kps[KP[f"{near_side}_{joint}"]] = [*p, 0.92]
        kps[KP[f"{far_side}_{joint}"]] = [*(p + [6.0, -4.0]), 0.55]

    if facing == "left":  # mirror horizontally inside a 1280 px frame
        kps[:, 0] = 1280.0 - kps[:, 0]
    return kps


def generate_pushups(
    reps: list[RepSpec],
    fps: float = 30.0,
    lead_in: float = 1.0,
    pause: float = 0.3,
    start_angle: float = 170.0,
    noise_px: float = 0.0,
    facing: str = "right",
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (keypoints[T, 17, 3], times[T]) for a sequence of reps."""
    rng = np.random.default_rng(seed)
    elbow, body = [], []

    def hold(angle: float, dev: float, seconds: float):
        for _ in range(int(round(seconds * fps))):
            elbow.append(angle)
            body.append(dev)

    hold(start_angle, -reps[0].pike if reps else 0.0, lead_in)
    prev_top = start_angle
    for spec in reps:
        n = max(2, int(round(spec.seconds * fps)))
        for i in range(n):
            phi = i / (n - 1)
            if phi <= 0.5:   # descent from the previous top
                w = (1 - math.cos(2 * math.pi * phi)) / 2
                angle = prev_top - (prev_top - spec.bottom) * w
            else:            # ascent to this rep's top
                w = (1 - math.cos(2 * math.pi * (1 - phi))) / 2
                angle = spec.top - (spec.top - spec.bottom) * w
            depth_phase = (1 - math.cos(2 * math.pi * phi)) / 2   # 0 top -> 1 bottom
            dev = spec.sag * depth_phase - spec.pike
            elbow.append(angle)
            body.append(dev)
        hold(spec.top, -spec.pike, pause)
        prev_top = spec.top

    kps = np.stack([_pose(a, d, facing) for a, d in zip(elbow, body)])
    if noise_px > 0:
        kps[:, :, :2] += rng.normal(0, noise_px, size=kps[:, :, :2].shape)
    times = np.arange(len(kps)) / fps
    return kps, times
