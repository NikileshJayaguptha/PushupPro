"""Tunable thresholds for rep detection and form scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisConfig:
    # --- keypoint quality -------------------------------------------------
    min_keypoint_conf: float = 0.35      # below this a joint is treated as missing
    max_gap_seconds: float = 0.5         # longer gaps are not interpolated

    # --- camera view ------------------------------------------------------
    # Median of shoulder-width / torso-length. Side-on shoulders overlap (ratio
    # near 0); facing the camera they spread wide (ratio > 1). Above this the
    # hips and ankles are hidden behind the torso and the body line can't be
    # measured, so sag / pike checks are skipped.
    side_view_max_ratio: float = 0.8
    # Body-line deviations beyond this are physically implausible tracking errors.
    max_plausible_body_dev_deg: float = 60.0

    # --- signal smoothing -------------------------------------------------
    smoothing_window_seconds: float = 0.2  # centered moving-median window

    # --- rep detection (press-height zig-zag) ------------------------------
    # Press height = shoulders above wrists in arm lengths (~1 at the top).
    height_reversal: float = 0.12          # swing needed to register a top/bottom
    min_rep_height_drop: float = 0.15      # top-to-bottom drop to count a rep
    plateau_tolerance_deg: float = 5.0     # still "at the top" within this many degrees of lockout
    plateau_tolerance: float = 0.015       # same, in press-height units (fallback)
    max_bottom_angle_deg: float = 135.0    # elbow must bend at least this far
    min_rep_seconds: float = 0.4
    max_rep_seconds: float = 10.0

    # --- form thresholds --------------------------------------------------
    # Depth: elbow angle at the bottom of the rep.
    depth_target_deg: float = 90.0         # ideal bottom
    depth_flag_deg: float = 100.0          # bottom above this => "shallow depth"
    depth_worst_deg: float = 135.0         # penalty saturates here
    # Lockout: elbow angle at the top that ends the rep.
    lockout_flag_deg: float = 155.0        # top below this => "incomplete lockout"
    lockout_worst_deg: float = 125.0
    # Body line: deviation of hip from shoulder-ankle line (degrees).
    sag_flag_deg: float = 15.0
    sag_worst_deg: float = 35.0
    pike_flag_deg: float = 15.0
    pike_worst_deg: float = 35.0
    # Body-line metrics use a robust high percentile within the rep, so one
    # noisy frame cannot flag a rep on its own.
    body_line_percentile: float = 90.0

    # --- score weights (max points deducted per fault) --------------------
    depth_weight: float = 35.0
    lockout_weight: float = 25.0
    sag_weight: float = 25.0
    pike_weight: float = 20.0
    # Fraction of a fault's weight deducted the moment it is flagged; the rest
    # ramps linearly up to the "worst" threshold.
    flag_base_fraction: float = 0.3


DEFAULT_CONFIG = AnalysisConfig()
