"use client";

import type { Rep } from "@/lib/types";
import { GRADE_VAR, ISSUE_LABELS, grade } from "@/lib/format";

interface Props {
  reps: Rep[];
  activeIndex: number | null;
  onSelect: (rep: Rep) => void;
}

/** One block per rep, width proportional to its duration, colored by form score. */
export default function RepStrip({ reps, activeIndex, onSelect }: Props) {
  if (!reps.length) return null;
  return (
    <div className="rep-strip" role="group" aria-label="Reps by form score">
      {reps.map((r) => {
        const issues = r.issues.map((i) => ISSUE_LABELS[i]).join(", ") || "clean";
        return (
          <button
            key={r.index}
            style={{ flex: `${r.duration} 1 0`, background: GRADE_VAR[grade(r.score)] }}
            aria-pressed={activeIndex === r.index}
            aria-label={`Rep ${r.index}, score ${Math.round(r.score)}, ${issues}`}
            title={`Rep ${r.index}: ${Math.round(r.score)} (${issues})`}
            onClick={() => onSelect(r)}
          >
            {r.index}
          </button>
        );
      })}
    </div>
  );
}
