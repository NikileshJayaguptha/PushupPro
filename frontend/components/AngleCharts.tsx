"use client";

import { memo, useMemo } from "react";
import {
  CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { Rep, Trace } from "@/lib/types";
import { GRADE_VAR, grade } from "@/lib/format";
import { BODY_FLAG_DEG } from "@/lib/trace";

interface Props {
  trace: Trace;
  reps: Rep[];
  currentTime: number;
  onSeek: (t: number) => void;
  showBody?: boolean;
}

const MAX_POINTS = 1200;
const tooltipStyle = { background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 6, fontSize: 14 };
const axisTick = { fontSize: 12, fill: "var(--muted)" };

type ChartClick = { activeLabel?: string | number } | null;

function Charts({ trace, reps, currentTime, onSeek, showBody = true }: Props) {
  const data = useMemo(() => {
    const step = Math.max(1, Math.ceil(trace.times.length / MAX_POINTS));
    const out: { t: number; elbow: number | null; body: number | null }[] = [];
    for (let i = 0; i < trace.times.length; i += step) {
      out.push({ t: trace.times[i], elbow: trace.elbow[i], body: trace.body[i] });
    }
    return out;
  }, [trace]);

  const end = data.length ? data[data.length - 1].t : 0;
  const click = (e: ChartClick) => {
    if (e?.activeLabel != null) onSeek(Number(e.activeLabel));
  };
  const repAreas = (y1: number, y2: number) =>
    reps.map((r) => (
      <ReferenceArea key={r.index} x1={r.start_time} x2={r.end_time} y1={y1} y2={y2}
        fill={GRADE_VAR[grade(r.score)]} fillOpacity={0.12} stroke="none" ifOverflow="hidden" />
    ));
  const repLabels = reps.map((r) => (
    <ReferenceLine key={`b${r.index}`} x={r.bottom_time} stroke="none"
      label={{ value: String(r.index), position: "insideBottom", fill: "var(--muted)", fontSize: 12 }} />
  ));

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div className="chart-title">Elbow angle</div>
        <div className="legend">
          <span><i style={{ background: "var(--accent)" }} />Elbow</span>
          <span><i style={{ background: "var(--muted)", height: 1 }} />90° depth target</span>
          <span>Shaded bands are reps, colored by score. Click to jump.</span>
        </div>
      </div>
      <div style={{ height: 220 }}>
        <ResponsiveContainer>
          <LineChart data={data} syncId="angles" onClick={click} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            {repAreas(40, 185)}
            <XAxis dataKey="t" type="number" domain={[0, end]} tick={axisTick} tickLine={false}
              tickFormatter={(v: number) => `${Math.round(v)}s`} />
            <YAxis domain={[40, 185]} ticks={[60, 90, 120, 150, 180]} tick={axisTick} tickLine={false} axisLine={false}
              tickFormatter={(v: number) => `${v}°`} />
            <ReferenceLine y={90} stroke="var(--muted)" strokeDasharray="4 4" />
            <ReferenceLine y={155} stroke="var(--line)" strokeDasharray="2 4" />
            {repLabels}
            <ReferenceLine x={currentTime} stroke="var(--ink)" strokeWidth={1.5} />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(v: number) => `${Number(v).toFixed(2)}s`}
              formatter={(v: number) => [`${Math.round(v)}°`, "Elbow"]} />
            <Line type="monotone" dataKey="elbow" stroke="var(--accent)" strokeWidth={2} dot={false}
              isAnimationActive={false} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {showBody && (<>
      <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8, marginTop: 16 }}>
        <div className="chart-title">Body line</div>
        <div className="legend">
          <span><i style={{ background: "var(--body)" }} />Hip offset from a straight plank</span>
          <span>Above 0 is sag, below 0 is pike; ±{BODY_FLAG_DEG}° is flagged</span>
        </div>
      </div>
      <div style={{ height: 150 }}>
        <ResponsiveContainer>
          <LineChart data={data} syncId="angles" onClick={click} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            {repAreas(-40, 40)}
            <ReferenceArea y1={BODY_FLAG_DEG} y2={40} fill="var(--poor)" fillOpacity={0.06} stroke="none" />
            <ReferenceArea y1={-40} y2={-BODY_FLAG_DEG} fill="var(--poor)" fillOpacity={0.06} stroke="none" />
            <XAxis dataKey="t" type="number" domain={[0, end]} tick={axisTick} tickLine={false}
              tickFormatter={(v: number) => `${Math.round(v)}s`} />
            <YAxis domain={[-40, 40]} ticks={[-30, -15, 0, 15, 30]} tick={axisTick} tickLine={false} axisLine={false}
              tickFormatter={(v: number) => `${v}°`} allowDataOverflow />
            <ReferenceLine y={0} stroke="var(--muted)" />
            <ReferenceLine x={currentTime} stroke="var(--ink)" strokeWidth={1.5} />
            <Tooltip contentStyle={tooltipStyle} labelFormatter={(v: number) => `${Number(v).toFixed(2)}s`}
              formatter={(v: number) => {
                const d = Math.round(v);
                return [d === 0 ? "straight" : `${Math.abs(d)}° ${d > 0 ? "sag" : "pike"}`, "Body line"];
              }} />
            <Line type="monotone" dataKey="body" stroke="var(--body)" strokeWidth={2} dot={false}
              isAnimationActive={false} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      </>)}
    </div>
  );
}

export default memo(Charts);
