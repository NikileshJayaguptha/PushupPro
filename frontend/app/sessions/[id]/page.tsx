"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AngleCharts from "@/components/AngleCharts";
import RepStrip from "@/components/RepStrip";
import RepTable from "@/components/RepTable";
import SkeletonPlayer, { type PlayerHandle } from "@/components/SkeletonPlayer";
import { api } from "@/lib/api";
import {
  ISSUE_LABELS, ISSUE_ORDER, ISSUE_TIPS, fmtDateTime, fmtDeg, fmtScore, grade, sessionName,
} from "@/lib/format";
import { frameIndexAt, repAt, repsCompleted } from "@/lib/trace";
import type { Rep, SessionDetail, Trace } from "@/lib/types";

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const player = useRef<PlayerHandle>(null);

  const [session, setSession] = useState<SessionDetail | null>(null);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [time, setTime] = useState(0);
  const [showSkeleton, setShowSkeleton] = useState(true);
  const [showAngles, setShowAngles] = useState(true);
  const [pinnedRep, setPinnedRep] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const s = await api.getSession(id);
      setSession(s);
      setError(null);
      if (s.status === "done") setTrace(await api.getTrace(id));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const pending = session?.status === "queued" || session?.status === "processing";
  useEffect(() => {
    if (!pending) return;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [pending, load]);

  const reps = useMemo(() => session?.reps ?? [], [session]);
  const current = repAt(reps, time);
  const activeIndex = current?.index ?? pinnedRep;
  const done = repsCompleted(reps, time);
  const fi = trace ? frameIndexAt(trace.times, time) : -1;
  const elbowNow = fi >= 0 ? trace!.elbow[fi] : null;
  const bodyNow = fi >= 0 ? trace!.body[fi] : null;

  const seek = useCallback((t: number) => player.current?.seek(t), []);
  const selectRep = useCallback((r: Rep) => {
    setPinnedRep(r.index);
    player.current?.seek(r.start_time, true);
  }, []);

  async function rename() {
    if (!session) return;
    const title = window.prompt("Name this set", session.title ?? "");
    if (title === null) return;
    await api.renameSession(id, title);
    load();
  }
  async function remove() {
    if (!window.confirm("Delete this set and its video? This can't be undone.")) return;
    await api.deleteSession(id);
    router.push("/");
  }
  async function reanalyze() {
    setTrace(null);
    await api.reanalyze(id);
    load();
  }

  if (error && !session) {
    return (
      <div style={{ marginTop: 28 }}>
        <p className="notice" role="alert">{error}</p>
        <p><Link href="/">Back to dashboard</Link></p>
      </div>
    );
  }
  if (!session) return <div className="empty">Loading…</div>;

  const header = (
    <div className="session-head">
      <div>
        <h1>{sessionName(session)}</h1>
        <p className="lede">{fmtDateTime(session.created_at)} · {session.original_filename}</p>
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button className="btn" onClick={rename}>Rename</button>
        {(session.status === "done" || session.status === "failed") && (
          <button className="btn" onClick={reanalyze}>Analyze again</button>
        )}
        <button className="btn btn-danger" onClick={remove}>Delete</button>
      </div>
    </div>
  );

  if (pending) {
    const pct = Math.round(session.progress * 100);
    return (
      <>
        {header}
        <div className="processing panel">
          <div className="num">{pct}%</div>
          <div className="bar" style={{ margin: "10px 0" }}><div style={{ width: `${pct}%` }} /></div>
          <p className="muted" style={{ margin: 0 }}>
            {session.status === "queued"
              ? "Waiting for the analyzer. Another video may be ahead of this one."
              : session.progress < 0.9
                ? "Tracking your joints frame by frame."
                : "Preparing the video for playback."}
          </p>
        </div>
      </>
    );
  }

  if (session.status === "failed") {
    return (
      <>
        {header}
        <div className="panel" style={{ marginTop: 24 }}>
          <h2>The analysis didn't finish</h2>
          <p className="notice" style={{ marginTop: 12 }}>{session.error || "Unknown error"}</p>
          <p className="muted">Check that the file plays in a video player, then select Analyze again.</p>
        </div>
      </>
    );
  }

  const s = session.summary;
  const issueCounts = s?.issue_counts ?? {};
  const topIssues = ISSUE_ORDER.filter((k) => (issueCounts[k] ?? 0) > 0)
    .sort((a, b) => (issueCounts[b] ?? 0) - (issueCounts[a] ?? 0));
  const lowTracking = (session.tracking_quality ?? 1) < 0.6;
  const bodyChecked = s?.body_line_checked !== false;

  return (
    <>
      {header}

      {lowTracking && (
        <p className="notice" style={{ marginTop: 16 }}>
          Your body was only tracked in {Math.round((session.tracking_quality ?? 0) * 100)}% of frames, so some reps
          may be missed. A side-on camera with your whole body in frame works best.
        </p>
      )}

      {!bodyChecked && (
        <p className="notice" style={{ marginTop: 16, background: "var(--fair-bg)", color: "var(--ink)" }}>
          This video was filmed from the front, so reps, depth and lockout were checked but hip sag and piking
          weren't. Film from the side to get body-line feedback too.
        </p>
      )}

      <div className="player-grid">
        <div>
          <SkeletonPlayer ref={player} src={api.videoUrl(id)} trace={trace} side={session.side}
            showSkeleton={showSkeleton} showAngles={showAngles} onTime={setTime} />
          <div className="player-controls">
            <label><input type="checkbox" checked={showSkeleton} onChange={(e) => setShowSkeleton(e.target.checked)} /> Skeleton</label>
            <label><input type="checkbox" checked={showAngles} onChange={(e) => setShowAngles(e.target.checked)} /> Angle labels</label>
            <span className="muted">Tracking the {session.side ?? "left"} side</span>
          </div>
          <RepStrip reps={reps} activeIndex={activeIndex} onSelect={selectRep} />
        </div>

        <aside className="scoreboard" aria-live="polite">
          <div className="count">
            {done}<small> / {session.rep_count}</small>
          </div>
          <div className="caption">reps completed at this point</div>
          <div className="live">
            <div><div className="v">{fmtDeg(elbowNow)}</div><div className="k">Elbow now</div></div>
            <div>
              <div className="v">
                {bodyNow == null ? "–" : Math.abs(bodyNow) < 3 ? "0°" : `${Math.round(Math.abs(bodyNow))}°`}
              </div>
              <div className="k">
                {!bodyChecked ? "Body line (side view only)" : bodyNow == null || Math.abs(bodyNow) < 3 ? "Body line" : bodyNow > 0 ? "Hip sag" : "Pike"}
              </div>
            </div>
            <div><div className="v">{fmtScore(session.avg_score)}</div><div className="k">Set form score</div></div>
            <div><div className="v">{session.clean_reps}</div><div className="k">Clean reps</div></div>
          </div>
          <div className="current">
            {current ? (
              <>
                <strong>Rep {current.index}</strong> · score{" "}
                <span className={`score-pill ${grade(current.score)}`} style={{ fontSize: 15 }}>{Math.round(current.score)}</span>
                <div style={{ marginTop: 6, opacity: 0.85 }}>
                  {current.issues.length ? current.issues.map((i) => ISSUE_LABELS[i]).join(", ") : "Clean rep"}
                </div>
              </>
            ) : (
              <span style={{ opacity: 0.7 }}>Play the video or pick a rep to follow along.</span>
            )}
          </div>
        </aside>
      </div>

      {trace && (
        <section className="section">
          <AngleCharts trace={trace} reps={reps} currentTime={time} onSeek={seek} showBody={bodyChecked} />
        </section>
      )}

      {topIssues.length > 0 && (
        <section className="section">
          <h2 style={{ marginBottom: 14 }}>Coaching notes</h2>
          <div className="panel">
            <ul className="tips">
              {topIssues.map((k) => (
                <li key={k}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                    <strong>{ISSUE_LABELS[k]}</strong>
                    <span className="num" style={{ fontSize: 18 }}>
                      {issueCounts[k]} of {session.rep_count} reps
                    </span>
                  </div>
                  <span className="muted">{ISSUE_TIPS[k]}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      <section className="section">
        <div className="section-head">
          <h2>Every rep</h2>
          {s && (
            <span className="muted">
              Average depth {fmtDeg(s.avg_depth)}
              {s.avg_rep_duration ? ` · ${s.avg_rep_duration.toFixed(1)}s per rep` : ""}
              {s.reps_per_minute ? ` · ${Math.round(s.reps_per_minute)} reps/min` : ""}
            </span>
          )}
        </div>
        <div className="panel" style={{ padding: 8 }}>
          <RepTable reps={reps} activeIndex={activeIndex} onSelect={selectRep} />
        </div>
      </section>
    </>
  );
}
