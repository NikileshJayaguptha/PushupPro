"use client";

import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { IssueKey, Progress } from "@/lib/types";
import { ISSUE_ORDER, fmtScore } from "@/lib/format";

function weekLabel(iso: string) {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function Delta({ now, prev, unit = "" }: { now: number | null; prev: number | null; unit?: string }) {
  if (now == null || prev == null || prev === 0 && now === 0) return <div className="delta muted">No data last week</div>;
  const d = Math.round(now - prev);
  if (d === 0) return <div className="delta muted">Same as last week</div>;
  return (
    <div className={`delta ${d > 0 ? "up" : "down"}`}>
      {d > 0 ? "+" : ""}{d}{unit} vs last week
    </div>
  );
}

const tooltipStyle = {
  background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 6, fontSize: 14,
};

export default function WeeklyProgress({ data }: { data: Progress }) {
  const { totals, weeks } = data;
  const chart = weeks.map((w) => ({ ...w, label: weekLabel(w.week_start) }));
  const totalReps = weeks.reduce((n, w) => n + w.total_reps, 0);

  // Issue frequency across the whole window, most common first.
  const issueRates = ISSUE_ORDER.map((k) => {
    const hits = weeks.reduce((n, w) => n + (w.issue_rates[k] ?? 0) * w.total_reps, 0);
    return { key: k as IssueKey, rate: totalReps ? hits / totalReps : 0 };
  }).sort((a, b) => b.rate - a.rate);

  return (
    <>
      <div className="stat-row">
        <div className="stat">
          <div className="value">{totals.this_week_reps}</div>
          <div className="label">Reps this week</div>
          <Delta now={totals.this_week_reps} prev={totals.last_week_reps} />
        </div>
        <div className="stat">
          <div className="value">{fmtScore(totals.this_week_score)}</div>
          <div className="label">Form score this week</div>
          <Delta now={totals.this_week_score} prev={totals.last_week_score} />
        </div>
        <div className="stat">
          <div className="value">{totals.best_set}</div>
          <div className="label">Best set, last {weeks.length} weeks</div>
        </div>
        <div className="stat">
          <div className="value">{totals.week_streak}</div>
          <div className="label">Week streak</div>
        </div>
      </div>

      <div className="chart-grid">
        <div className="panel">
          <div className="chart-title">Reps per week</div>
          <div style={{ height: 200 }}>
            <ResponsiveContainer>
              <BarChart data={chart} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="var(--line)" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: "var(--muted)" }} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "var(--muted)" }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--surface-2)" }}
                  formatter={(v: number, name: string) => [v, name === "clean_reps" ? "Clean reps" : "Total reps"]} />
                <Bar dataKey="total_reps" fill="var(--accent)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <div className="chart-title">Average form score</div>
          <div style={{ height: 200 }}>
            <ResponsiveContainer>
              <LineChart data={chart} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="var(--line)" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: "var(--muted)" }} tickLine={false} axisLine={false} />
                <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={{ fontSize: 12, fill: "var(--muted)" }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [Math.round(v), "Form score"]} />
                <Line type="monotone" dataKey="avg_score" stroke="var(--accent)" strokeWidth={2.5}
                  dot={{ r: 3, fill: "var(--accent)" }} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {totalReps > 0 && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="chart-title">What to work on</div>
          <ul className="tips">
            {issueRates.map(({ key, rate }) => (
              <li key={key}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <strong>{data.issue_labels[key]}</strong>
                  <span className="rate num" style={{ color: rate > 0.25 ? "var(--poor)" : rate > 0.1 ? "var(--fair)" : "var(--good)" }}>
                    {Math.round(rate * 100)}% of reps
                  </span>
                </div>
                {rate > 0.1 && <span className="muted" style={{ fontSize: 15 }}>{data.issue_tips[key]}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
