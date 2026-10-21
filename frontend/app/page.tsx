"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import SessionList from "@/components/SessionList";
import UploadCard from "@/components/UploadCard";
import WeeklyProgress from "@/components/WeeklyProgress";
import { api } from "@/lib/api";
import type { Progress, SessionSummary } from "@/lib/types";

export default function Dashboard() {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [p, s] = await Promise.all([api.weeklyProgress(8), api.listSessions()]);
      setProgress(p);
      setSessions(s);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Keep polling while anything is still being analyzed.
  const busy = sessions?.some((s) => s.status === "queued" || s.status === "processing");
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [busy, load]);

  return (
    <>
      <div style={{ marginTop: 28 }}>
        <h1>Your push-ups, rep by rep</h1>
        <p className="lede">
          Upload a video and get every rep counted, with depth, lockout and body line checked.
        </p>
      </div>

      {error && <p className="notice" role="alert" style={{ marginTop: 20 }}>{error}</p>}

      <div className="dash-grid">
        <div>
          <h2 style={{ marginBottom: 14 }}>Last 8 weeks</h2>
          {progress ? <WeeklyProgress data={progress} /> : !error && <div className="panel empty">Loading progress…</div>}
        </div>
        <UploadCard />
      </div>

      <section className="section">
        <div className="section-head">
          <h2>Recent sets</h2>
          {sessions && sessions.length > 6 && <Link href="/sessions">See all {sessions.length}</Link>}
        </div>
        <div className="panel" style={{ padding: "4px 16px" }}>
          {sessions ? <SessionList sessions={sessions.slice(0, 6)} /> : <div className="empty">Loading…</div>}
        </div>
      </section>
    </>
  );
}
