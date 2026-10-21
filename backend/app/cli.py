from __future__ import annotations

import argparse
import json
import sys

from .analysis import ISSUE_LABELS, analyze_video
from .analysis.pose import YoloPoseEstimator
from .config import get_settings


def _deg(v: float | None) -> str:
    return "-" if v is None else f"{v:.1f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pushuppro")
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="count reps and score form in a video")
    a.add_argument("video")
    a.add_argument("--weights", default=get_settings().pose_weights)
    a.add_argument("--device", default=None)
    a.add_argument("--json", dest="json_out", help="write full results (incl. trace) to this file")
    args = parser.parse_args(argv)

    estimator = YoloPoseEstimator(weights=args.weights, device=args.device)

    def progress(p: float) -> None:
        sys.stderr.write(f"\r  analysing… {p * 100:5.1f}%")
        sys.stderr.flush()

    result = analyze_video(args.video, estimator, progress=progress)
    sys.stderr.write("\r" + " " * 30 + "\r")

    s = result.summary
    print(f"Side tracked: {result.side}   view: {result.view}   tracking quality: {result.valid_fraction:.0%}")
    if result.view != "side":
        print("Camera is not side-on: hip sag and piking were not checked.")
    print(f"Reps: {s['rep_count']}   clean: {s['clean_reps']}   avg score: {s['avg_score']}")
    print()
    print(f"{'#':>3} {'time':>12} {'bottom°':>8} {'top°':>6} {'sag°':>5} {'pike°':>6} {'score':>6}  issues")
    for r in result.reps:
        issues = ", ".join(ISSUE_LABELS[i] for i in r.issues) or "-"
        print(f"{r.index:>3} {r.start_time:5.1f}-{r.end_time:5.1f}s {r.min_elbow_angle:8.1f} "
              f"{r.top_elbow_angle:6.1f} {_deg(r.max_hip_sag):>5} {_deg(r.max_pike):>6} {r.score:6.1f}  {issues}")

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump({"summary": s, "side": result.side, "fps": result.fps,
                       "reps": [r.to_dict() for r in result.reps], "trace": result.trace}, f)
        print(f"\nFull results written to {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
