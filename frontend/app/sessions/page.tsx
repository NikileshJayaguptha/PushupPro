"use client";

import { useEffect, useState } from "react";
import SessionList from "@/components/SessionList";
import { api } from "@/lib/api";
import type { SessionSummary } from "@/lib/types";

export default function AllSessions() {
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listSessions().then(setSessions).catch((e: Error) => setError(e.message));
  }, []);

  return (
    <>
      <div style={{ marginTop: 28 }}>
        <h1>All sets</h1>
        <p className="lede">Every video you've analyzed, newest first.</p>
      </div>
      {error && <p className="notice" role="alert" style={{ marginTop: 20 }}>{error}</p>}
      <div className="panel" style={{ padding: "4px 16px", marginTop: 24 }}>
        {sessions ? <SessionList sessions={sessions} /> : !error && <div className="empty">Loading…</div>}
      </div>
    </>
  );
}
