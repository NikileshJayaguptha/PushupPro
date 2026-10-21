"""Joint-angle geometry on 2D image keypoints (image y axis points down)."""

from __future__ import annotations

import math

import numpy as np


def joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Interior angle at ``b`` (degrees, 0-180) formed by segments b->a and b->c."""
    ba = np.asarray(a, dtype=float)[:2] - np.asarray(b, dtype=float)[:2]
    bc = np.asarray(c, dtype=float)[:2] - np.asarray(b, dtype=float)[:2]
    na, nc = np.linalg.norm(ba), np.linalg.norm(bc)
    if na < 1e-6 or nc < 1e-6:
        return float("nan")
    cos = float(np.clip(np.dot(ba, bc) / (na * nc), -1.0, 1.0))
    return math.degrees(math.acos(cos))


def body_line_deviation(shoulder: np.ndarray, hip: np.ndarray, ankle: np.ndarray) -> float:
    """Signed deviation of the hip from a straight shoulder-to-ankle line, in degrees.

    ``0``   -> perfectly straight plank.
    ``> 0`` -> hips dropped *below* the line (sag).
    ``< 0`` -> hips raised *above* the line (pike).

    The magnitude is ``180 - angle(shoulder, hip, ankle)``. The sign comes from
    which side of the shoulder-ankle line the hip sits on, using the image
    "down" direction (+y) as reference, so it works whichever way the athlete
    faces the camera.
    """
    s = np.asarray(shoulder, dtype=float)[:2]
    h = np.asarray(hip, dtype=float)[:2]
    a = np.asarray(ankle, dtype=float)[:2]
    angle = joint_angle(s, h, a)
    if math.isnan(angle):
        return float("nan")
    magnitude = 180.0 - angle

    line = a - s
    length = np.linalg.norm(line)
    if length < 1e-6:
        return float("nan")
    # Unit normal to the body line, oriented to point "down" in the image.
    normal = np.array([-line[1], line[0]]) / length
    if normal[1] < 0:
        normal = -normal
    offset = float(np.dot(h - s, normal))
    return magnitude if offset >= 0 else -magnitude
