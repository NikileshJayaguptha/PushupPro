import Link from "next/link";
import type { SessionSummary } from "@/lib/types";
import { fmtDateTime, fmtScore, grade, sessionName } from "@/lib/format";

function StatusText({ s }: { s: SessionSummary }) {
  if (s.status === "queued") return <>Waiting to analyze</>;
  if (s.status === "processing") return <>Analyzing {Math.round(s.progress * 100)}%</>;
  if (s.status === "failed") return <span style={{ color: "var(--poor)" }}>Analysis failed</span>;
  return (
    <>
      {s.clean_reps} of {s.rep_count} clean
      {s.duration ? ` · ${Math.round(s.duration)}s video` : ""}
    </>
  );
}

export default function SessionList({ sessions }: { sessions: SessionSummary[] }) {
  if (sessions.length === 0) {
    return <div className="empty">No sets yet. Upload a video to count your first set.</div>;
  }
  return (
    <ul className="session-list">
      {sessions.map((s) => (
        <li key={s.id}>
          <Link href={`/sessions/${s.id}`} className="session-link">
            <div>
              <div className="s-name">{sessionName(s)}</div>
              <div className="s-meta">
                {fmtDateTime(s.created_at)} · <StatusText s={s} />
              </div>
            </div>
            {s.status === "done" ? (
              <span className={`score-pill ${grade(s.avg_score)}`} title="Average form score">
                {fmtScore(s.avg_score)}
              </span>
            ) : (
              <span />
            )}
            <div className="s-reps">
              {s.status === "done" ? s.rep_count : "–"}
              <small>reps</small>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
