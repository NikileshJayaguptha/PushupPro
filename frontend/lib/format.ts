import type { IssueKey } from "./types";

export const ISSUE_LABELS: Record<IssueKey, string> = {
  shallow_depth: "Shallow depth",
  incomplete_lockout: "Incomplete lockout",
  hip_sag: "Hip sag",
  piking: "Piking",
};

export const ISSUE_TIPS: Record<IssueKey, string> = {
  shallow_depth: "Lower until your elbows reach about 90°, chest a fist's height from the floor.",
  incomplete_lockout: "Press all the way up and straighten your arms at the top of every rep.",
  hip_sag: "Squeeze your glutes and brace your core so hips stay in line with shoulders and ankles.",
  piking: "Drop your hips into a straight plank instead of shifting the load to your shoulders.",
};

export const ISSUE_ORDER: IssueKey[] = ["shallow_depth", "incomplete_lockout", "hip_sag", "piking"];

export type Grade = "good" | "fair" | "poor";

export function grade(score: number | null | undefined): Grade {
  if (score == null) return "fair";
  if (score >= 85) return "good";
  if (score >= 65) return "fair";
  return "poor";
}

export const GRADE_VAR: Record<Grade, string> = {
  good: "var(--good)",
  fair: "var(--fair)",
  poor: "var(--poor)",
};

export function fmtScore(score: number | null | undefined): string {
  return score == null ? "–" : Math.round(score).toString();
}

export function fmtDeg(v: number | null | undefined): string {
  return v == null ? "–" : `${Math.round(v)}°`;
}

export function fmtClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds - m * 60;
  return `${m}:${s.toFixed(1).padStart(4, "0")}`;
}

export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

export function sessionName(s: { title: string | null; created_at: string }): string {
  return s.title || `Set on ${fmtDate(s.created_at)}`;
}
