"""Rep segmentation.

A push-up rep is one top -> bottom -> top cycle of the body. We track
*press height* (how far the shoulders sit above the wrists, in arm lengths)
and find alternating peaks and troughs with a hysteresis "zig-zag" detector.

Why press height and not the elbow angle? Both move together, but the elbow
angle becomes unreliable when the arm is foreshortened — at the bottom of a
rep filmed from the front, a held bottom position can read like a half
press. Shoulder height doesn't have that problem. The elbow angle is still
what we *score* (depth and lockout) inside each detected rep.

The zig-zag needs no fixed "up"/"down" cut-offs, so a shallow rep is still
*counted* and can then be *flagged* as shallow.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import AnalysisConfig


@dataclass
class RepSegment:
    start: int      # frame where the descent begins (end of the top hold)
    bottom: int     # frame where the shoulders are lowest
    end: int        # frame where the press reaches the top
    end_peak: int   # frame of the top after the rep (used for the lockout check)


def _valid_segments(values: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous [start, end) runs of non-NaN values."""
    segs, start = [], None
    for i, v in enumerate(values):
        if np.isnan(v):
            if start is not None:
                segs.append((start, i))
                start = None
        elif start is None:
            start = i
    if start is not None:
        segs.append((start, len(values)))
    return segs


def zigzag_extrema(values: np.ndarray, lo: int, hi: int, threshold: float) -> list[tuple[int, str]]:
    """Alternating ('peak'|'trough') turning points in values[lo:hi]."""
    extrema: list[tuple[int, str]] = []
    direction: str | None = None
    max_i = min_i = ext = lo
    for i in range(lo, hi):
        v = values[i]
        if direction is None:
            if v > values[max_i]:
                max_i = i
            if v < values[min_i]:
                min_i = i
            if v <= values[max_i] - threshold:
                extrema.append((max_i, "peak"))
                direction = "down"
                ext = max_i + int(np.argmin(values[max_i: i + 1]))
            elif v >= values[min_i] + threshold:
                extrema.append((min_i, "trough"))
                direction = "up"
                ext = min_i + int(np.argmax(values[min_i: i + 1]))
        elif direction == "down":
            if v < values[ext]:
                ext = i
            elif v >= values[ext] + threshold:
                extrema.append((ext, "trough"))
                direction, ext = "up", i
        else:  # going up
            if v > values[ext]:
                ext = i
            elif v <= values[ext] - threshold:
                extrema.append((ext, "peak"))
                direction, ext = "down", i
    # A rise that is still in progress at the end of the clip closes the last rep.
    if direction == "up":
        extrema.append((ext, "peak"))
    return extrema


def _trim_to_motion(h: np.ndarray, start_peak: int, bottom: int, end_peak: int, tol: float) -> tuple[int, int]:
    """Shrink [start_peak, end_peak] so pauses at the top don't count as rep time.

    ``h`` is any signal that is high at the top of the rep.
    """
    start = start_peak
    for i in range(start_peak, bottom + 1):
        if h[i] >= h[start_peak] - tol:
            start = i
        else:
            break
    end = end_peak
    for i in range(bottom, end_peak + 1):
        if h[i] >= h[end_peak] - tol:
            end = i
            break
    return start, end


def detect_reps(height: np.ndarray, elbow: np.ndarray, times: np.ndarray,
                cfg: AnalysisConfig) -> list[RepSegment]:
    reps: list[RepSegment] = []
    for lo, hi in _valid_segments(height):
        if hi - lo < 3:
            continue
        ext = zigzag_extrema(height, lo, hi, cfg.height_reversal)
        for k, (idx, kind) in enumerate(ext):
            if kind != "trough":
                continue
            prev_peak = ext[k - 1][0] if k > 0 and ext[k - 1][1] == "peak" else None
            next_peak = ext[k + 1][0] if k + 1 < len(ext) and ext[k + 1][1] == "peak" else None
            if next_peak is None:
                continue  # clip ended at the bottom: not a completed rep
            start = prev_peak if prev_peak is not None else lo
            drop = max(height[start], height[next_peak]) - height[idx]
            if drop < cfg.min_rep_height_drop:
                continue
            window = elbow[start: next_peak + 1]
            window = window[~np.isnan(window)]
            if window.size and np.percentile(window, 5) > cfg.max_bottom_angle_deg:
                continue  # body moved but the arms barely bent (e.g. rocking on toes)
            # Trim top pauses on the elbow angle: near lockout it starts changing
            # well before shoulder height does. Fall back to height if untracked.
            seg_elbow = elbow[start: next_peak + 1]
            if not np.isnan(seg_elbow).any():
                t_start, t_end = _trim_to_motion(elbow, start, idx, next_peak, cfg.plateau_tolerance_deg)
            else:
                t_start, t_end = _trim_to_motion(height, start, idx, next_peak, cfg.plateau_tolerance)
            duration = times[t_end] - times[t_start]
            if not (cfg.min_rep_seconds <= duration <= cfg.max_rep_seconds):
                continue
            reps.append(RepSegment(start=t_start, bottom=idx, end=t_end, end_peak=next_peak))
    return reps
