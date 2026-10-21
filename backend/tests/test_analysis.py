import math

import numpy as np
import pytest

from app.analysis import analyze_keypoints
from app.analysis.geometry import body_line_deviation, joint_angle
from app.analysis.synthetic import RepSpec, generate_pushups


def run(reps, **kw):
    kps, t = generate_pushups(reps, **kw)
    return analyze_keypoints(kps, t, fps=kw.get("fps", 30.0))


# ---------------------------------------------------------------- geometr
def test_joint_angle_right_angle():
    assert joint_angle([1, 0], [0, 0], [0, 1]) == pytest.approx(90)


def test_joint_angle_straight():
    assert joint_angle([0, 0], [1, 0], [2, 0]) == pytest.approx(180)


def test_joint_angle_degenerate_is_nan():
    assert math.isnan(joint_angle([0, 0], [0, 0], [1, 1]))


@pytest.mark.parametrize("flip", [False, True])
def test_body_line_sign(flip):
    sx = -1 if flip else 1
    shoulder, ankle = np.array([300 * sx, 400]), np.array([0, 500])
    mid = (shoulder + ankle) / 2
    assert body_line_deviation(shoulder, mid, ankle) == pytest.approx(0, abs=1e-6)
    assert body_line_deviation(shoulder, mid + [0, 30], ankle) > 5    
    assert body_line_deviation(shoulder, mid - [0, 30], ankle) < -5  


def test_counts_clean_reps():
    res = run([RepSpec() for _ in range(5)])
    assert res.summary["rep_count"] == 5
    assert all(not r.issues for r in res.reps)
    assert all(r.score >= 95 for r in res.reps)


@pytest.mark.parametrize("facing", ["left", "right"])
def test_counts_with_noise_either_direction(facing):
    res = run([RepSpec() for _ in range(8)], noise_px=2.5, facing=facing, seed=3)
    assert res.summary["rep_count"] == 8


def test_variable_tempo():
    specs = [RepSpec(seconds=s) for s in (1.0, 2.5, 1.4, 3.0, 0.9)]
    assert run(specs).summary["rep_count"] == 5


def test_lower_fps():
    assert run([RepSpec() for _ in range(4)], fps=12).summary["rep_count"] == 4


def test_ignores_small_wobble():
    # Elbow only bends to 150 deg: not a push-up.
    res = run([RepSpec(bottom=150) for _ in range(3)])
    assert res.summary["rep_count"] == 0


def test_rep_timing_is_sane():
    res = run([RepSpec(seconds=2.0) for _ in range(3)])
    for r in res.reps:
        assert 1.6 < r.duration < 2.6
        assert r.start_time < r.bottom_time < r.end_time


def test_occlusion_gap_is_bridged():
    kps, t = generate_pushups([RepSpec() for _ in range(4)])
    kps[60:66, :, 2] = 0.0  # 0.2 s of lost tracking mid-rep
    res = analyze_keypoints(kps, t, fps=30)
    assert res.summary["rep_count"] == 4


def test_shallow_depth_flagged():
    res = run([RepSpec(), RepSpec(bottom=118), RepSpec()])
    assert res.summary["rep_count"] == 3
    assert [("shallow_depth" in r.issues) for r in res.reps] == [False, True, False]
    assert res.reps[1].score < res.reps[0].score - 15


def test_incomplete_lockout_flagged():
    res = run([RepSpec(), RepSpec(top=138), RepSpec()])
    assert res.summary["rep_count"] == 3
    assert "incomplete_lockout" in res.reps[1].issues
    assert "incomplete_lockout" not in res.reps[0].issues


def test_hip_sag_flagged():
    res = run([RepSpec(sag=25) for _ in range(3)])
    assert all("hip_sag" in r.issues for r in res.reps)
    assert all("piking" not in r.issues for r in res.reps)
    assert all(20 < r.max_hip_sag < 30 for r in res.reps)


def test_piking_flagged():
    res = run([RepSpec(pike=22) for _ in range(3)])
    assert all("piking" in r.issues for r in res.reps)
    assert all("hip_sag" not in r.issues for r in res.reps)


def test_mild_sag_not_flagged():
    res = run([RepSpec(sag=8) for _ in range(3)])
    assert all("hip_sag" not in r.issues for r in res.reps)


def test_score_orders_by_severity():
    res = run([RepSpec(), RepSpec(sag=20), RepSpec(sag=20, bottom=115, top=145)])
    s = [r.score for r in res.reps]
    assert len(s) == 3
    assert s[0] > s[1] > s[2]
    assert 0 <= s[2] <= 100


def test_summary_and_trace_shape():
    res = run([RepSpec(), RepSpec(bottom=120)])
    s = res.summary
    assert s["rep_count"] == 2 and s["clean_reps"] == 1
    assert s["issue_counts"] == {"shallow_depth": 1}
    n = len(res.trace["times"])
    assert len(res.trace["elbow"]) == len(res.trace["keypoints"]) == n
    assert len(res.trace["keypoints"][0]) == 17


def test_empty_video_has_no_reps():
    kps = np.zeros((90, 17, 3))
    res = analyze_keypoints(kps, np.arange(90) / 30, fps=30)
    assert res.summary["rep_count"] == 0
    assert res.valid_fraction == 0


def test_front_view_skips_body_line_checks():
    kps, t = generate_pushups([RepSpec(sag=30) for _ in range(3)])
    kps[:, [6, 8, 10, 12, 14, 16], 0] += 260  
    kps[:, [12, 14, 16], 1] -= 40
    res = analyze_keypoints(kps, t, fps=30)
    assert res.view == "front"
    assert res.summary["body_line_checked"] is False
    assert res.summary["rep_count"] == 3  
    for r in res.reps:
        assert r.max_hip_sag is None and r.max_pike is None
        assert "hip_sag" not in r.issues and "piking" not in r.issues


def test_side_view_detected():
    res = run([RepSpec()])
    assert res.view == "side" and res.summary["body_line_checked"] is True
