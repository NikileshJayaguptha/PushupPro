"""Per-rep form checks and the 0-100 form score."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from .config import AnalysisConfig
from .reps import RepSegment
from .signals import AngleSignals

ISSUE_LABELS = {
    "shallow_depth": "Shallow depth",
    "incomplete_lockout": "Incomplete lockout",
    "hip_sag": "Hip sag",
    "piking": "Piking (hips too high)",
}

ISSUE_TIPS = {
    "shallow_depth": "Lower until your elbows reach about 90° — chest a fist's height from the floor.",
    "incomplete_lockout": "Press all the way up and straighten your arms at the top of every rep.",
    "hip_sag": "Squeeze glutes and brace your core so hips stay in line with shoulders and ankles.",
    "piking": "Drop your hips into a straight plank; don't shift the load to your shoulders.",
}


@dataclass
class RepResult:
    index: int
    start_frame: int
    bottom_frame: int
    end_frame: int
    start_time: float
    bottom_time: float
    end_time: float
    duration: float
    descent_time: float
    ascent_time: float
    min_elbow_angle: float
    top_elbow_angle: float
    max_hip_sag: float | None   # None when the camera view can't measure the body line
    max_pike: float | None
    score: float
    issues: list[str] = field(default_factory=list)
    penalties: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _ramp_penalty(value: float, flag: float, worst: float, weight: float, base_frac: float) -> float:
    """0 before ``flag``; jumps to base_frac*weight at flag, ramps to weight at ``worst``.

    Works for both "higher is worse" (flag < worst) and "lower is worse"
    (flag > worst) metrics.
    """
    if np.isnan(value):
        return 0.0
    if flag < worst:
        if value <= flag:
            return 0.0
        frac = (value - flag) / (worst - flag)
    else:
        if value >= flag:
            return 0.0
        frac = (flag - value) / (flag - worst)
    frac = float(np.clip(frac, 0.0, 1.0))
    return weight * (base_frac + (1.0 - base_frac) * frac)


def evaluate_rep(index: int, seg: RepSegment, sig: AngleSignals, cfg: AnalysisConfig) -> RepResult:
    t = sig.times
    elbow, body = sig.elbow, sig.body
    window = body[seg.start: seg.end + 1]
    window = window[~np.isnan(window)]
    if window.size:
        sag = float(np.percentile(np.clip(window, 0, None), cfg.body_line_percentile))
        pike = float(np.percentile(np.clip(-window, 0, None), cfg.body_line_percentile))
    else:
        sag = pike = float("nan")

    # Robust percentiles instead of single frames: a momentary tracking glitch
    # shouldn't decide depth or lockout.
    rep_elbow = elbow[seg.start: seg.end + 1]
    rep_elbow = rep_elbow[~np.isnan(rep_elbow)]
    min_elbow = float(np.percentile(rep_elbow, 5)) if rep_elbow.size else float("nan")
    top_lo = int(np.searchsorted(t, t[seg.end_peak] - 0.25))
    top_hi = int(np.searchsorted(t, t[seg.end_peak] + 0.25, side="right"))
    top_window = elbow[top_lo:top_hi]
    top_window = top_window[~np.isnan(top_window)]
    top_elbow = float(np.percentile(top_window, 95)) if top_window.size else float("nan")

    penalties = {
        "shallow_depth": _ramp_penalty(min_elbow, cfg.depth_flag_deg, cfg.depth_worst_deg,
                                       cfg.depth_weight, cfg.flag_base_fraction),
        "incomplete_lockout": _ramp_penalty(top_elbow, cfg.lockout_flag_deg, cfg.lockout_worst_deg,
                                            cfg.lockout_weight, cfg.flag_base_fraction),
        "hip_sag": _ramp_penalty(sag, cfg.sag_flag_deg, cfg.sag_worst_deg,
                                 cfg.sag_weight, cfg.flag_base_fraction),
        "piking": _ramp_penalty(pike, cfg.pike_flag_deg, cfg.pike_worst_deg,
                                cfg.pike_weight, cfg.flag_base_fraction),
    }
    # Reps between the ideal depth and the flag threshold aren't flagged, but
    # lose up to 5 points so "barely deep enough" doesn't score a perfect 100.
    if cfg.depth_target_deg < min_elbow <= cfg.depth_flag_deg:
        penalties["shallow_depth"] = 5.0 * (min_elbow - cfg.depth_target_deg) / (
            cfg.depth_flag_deg - cfg.depth_target_deg
        )

    issues = [
        name for name, flagged in (
            ("shallow_depth", min_elbow > cfg.depth_flag_deg),
            ("incomplete_lockout", top_elbow < cfg.lockout_flag_deg),
            ("hip_sag", sag > cfg.sag_flag_deg),
            ("piking", pike > cfg.pike_flag_deg),
        ) if flagged
    ]
    score = max(0.0, 100.0 - sum(penalties.values()))

    return RepResult(
        index=index,
        start_frame=seg.start,
        bottom_frame=seg.bottom,
        end_frame=seg.end,
        start_time=float(t[seg.start]),
        bottom_time=float(t[seg.bottom]),
        end_time=float(t[seg.end]),
        duration=float(t[seg.end] - t[seg.start]),
        descent_time=float(t[seg.bottom] - t[seg.start]),
        ascent_time=float(t[seg.end] - t[seg.bottom]),
        min_elbow_angle=round(min_elbow, 1),
        top_elbow_angle=round(top_elbow, 1),
        max_hip_sag=None if np.isnan(sag) else round(sag, 1),
        max_pike=None if np.isnan(pike) else round(pike, 1),
        score=round(score, 1),
        issues=issues,
        penalties={k: round(v, 1) for k, v in penalties.items() if v > 0},
    )
