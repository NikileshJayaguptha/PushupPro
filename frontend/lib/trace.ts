import type { Rep } from "./types";

/** Index of the trace sample closest to time ``t`` (times sorted ascending). */
export function frameIndexAt(times: number[], t: number): number {
  if (times.length === 0) return -1;
  let lo = 0;
  let hi = times.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (times[mid] < t) lo = mid + 1;
    else hi = mid;
  }
  if (lo > 0 && Math.abs(times[lo - 1] - t) < Math.abs(times[lo] - t)) lo -= 1;
  return lo;
}

/** The rep whose [start, end] window contains ``t``, if any. */
export function repAt(reps: Rep[], t: number): Rep | null {
  for (const r of reps) if (t >= r.start_time && t <= r.end_time) return r;
  return null;
}

/** Reps fully completed by time ``t``. */
export function repsCompleted(reps: Rep[], t: number): number {
  let n = 0;
  for (const r of reps) if (r.end_time <= t + 1e-3) n++;
  return n;
}

// Body-line deviation that counts as a fault (matches backend defaults).
export const BODY_FLAG_DEG = 15;
