export type SessionStatus = "queued" | "processing" | "done" | "failed";

export type IssueKey = "shallow_depth" | "incomplete_lockout" | "hip_sag" | "piking";

export interface Rep {
  index: number;
  start_frame: number;
  bottom_frame: number;
  end_frame: number;
  start_time: number;
  bottom_time: number;
  end_time: number;
  duration: number;
  descent_time: number;
  ascent_time: number;
  min_elbow_angle: number;
  top_elbow_angle: number;
  max_hip_sag: number | null; // null when the camera angle can't measure the body line
  max_pike: number | null;
  score: number;
  issues: IssueKey[];
  penalties: Partial<Record<IssueKey, number>>;
}

export interface SessionSummary {
  id: string;
  created_at: string;
  title: string | null;
  original_filename: string;
  status: SessionStatus;
  progress: number;
  error: string | null;
  duration: number | null;
  rep_count: number;
  clean_reps: number;
  avg_score: number | null;
  avg_depth: number | null;
}

export interface SessionDetail extends SessionSummary {
  fps: number | null;
  width: number | null;
  height: number | null;
  side: string | null;
  tracking_quality: number | null;
  summary: {
    rep_count: number;
    avg_score: number | null;
    best_score: number | null;
    worst_score: number | null;
    avg_depth: number | null;
    avg_rep_duration: number | null;
    reps_per_minute: number | null;
    clean_reps: number;
    issue_counts: Partial<Record<IssueKey, number>>;
    view?: "side" | "front";
    body_line_checked?: boolean;
  } | null;
  reps: Rep[];
}

export type Keypoint = [number, number, number];

export interface Trace {
  times: number[];
  elbow: (number | null)[];
  body: (number | null)[];
  elbow_raw: (number | null)[];
  height?: (number | null)[];
  keypoints: (Keypoint[] | null)[];
  skeleton: [number, number][];
}

export interface WeekStats {
  week_start: string;
  sessions: number;
  total_reps: number;
  clean_reps: number;
  avg_score: number | null;
  best_set: number;
  avg_depth: number | null;
  issue_rates: Record<IssueKey, number>;
}

export interface Progress {
  weeks: WeekStats[];
  totals: {
    sessions: number;
    reps: number;
    avg_score: number | null;
    best_set: number;
    week_streak: number;
    this_week_reps: number;
    last_week_reps: number;
    this_week_score: number | null;
    last_week_score: number | null;
  };
  issue_labels: Record<IssueKey, string>;
  issue_tips: Record<IssueKey, string>;
}
