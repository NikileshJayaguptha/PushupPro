"use client";

import type { Rep } from "@/lib/types";
import { ISSUE_LABELS, fmtClock, fmtDeg, grade } from "@/lib/format";

interface Props {
  reps: Rep[];
  activeIndex: number | null;
  onSelect: (rep: Rep) => void;
}

export default function RepTable({ reps, activeIndex, onSelect }: Props) {
  if (!reps.length) {
    return (
      <div className="empty">
        No complete reps found. Make sure the camera sees you from the side with your arms, hips and feet in frame.
      </div>
    );
  }
  return (
    <div className="table-wrap">
      <table className="reps">
        <thead>
          <tr>
            <th scope="col">Rep</th>
            <th scope="col">Starts</th>
            <th scope="col" title="Smallest elbow angle; 90° or less is full depth">Bottom</th>
            <th scope="col" title="Elbow angle at the top; 155° or more is a full lockout">Top</th>
            <th scope="col">Hip sag</th>
            <th scope="col">Pike</th>
            <th scope="col" title="Seconds down / seconds up">Tempo</th>
            <th scope="col">Score</th>
            <th scope="col">Issues</th>
          </tr>
        </thead>
        <tbody>
          {reps.map((r) => (
            <tr key={r.index} className={activeIndex === r.index ? "active" : undefined}
              onClick={() => onSelect(r)} tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && onSelect(r)}>
              <td className="n">{r.index}</td>
              <td className="n">{fmtClock(r.start_time)}</td>
              <td className={`n${r.issues.includes("shallow_depth") ? " cell-bad" : ""}`}>{fmtDeg(r.min_elbow_angle)}</td>
              <td className={`n${r.issues.includes("incomplete_lockout") ? " cell-bad" : ""}`}>{fmtDeg(r.top_elbow_angle)}</td>
              <td className={`n${r.issues.includes("hip_sag") ? " cell-bad" : ""}`}>{fmtDeg(r.max_hip_sag)}</td>
              <td className={`n${r.issues.includes("piking") ? " cell-bad" : ""}`}>{fmtDeg(r.max_pike)}</td>
              <td className="n">{r.descent_time.toFixed(1)} / {r.ascent_time.toFixed(1)}s</td>
              <td><span className={`score-pill ${grade(r.score)}`}>{Math.round(r.score)}</span></td>
              <td>
                {r.issues.length
                  ? r.issues.map((i) => <span key={i} className="tag">{ISSUE_LABELS[i]}</span>)
                  : <span className="muted">Clean</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
