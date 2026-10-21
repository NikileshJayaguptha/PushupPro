import type { Progress, SessionDetail, SessionSummary, Trace } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  } catch {
    throw new Error(`Can't reach the PushupPro API at ${API_URL}. Check that the backend is running.`);
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  listSessions: () => request<SessionSummary[]>("/api/sessions?limit=50"),
  getSession: (id: string) => request<SessionDetail>(`/api/sessions/${id}`),
  getTrace: (id: string) => request<Trace>(`/api/sessions/${id}/trace`),
  renameSession: (id: string, title: string) =>
    request<SessionSummary>(`/api/sessions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }),
  reanalyze: (id: string) => request<SessionSummary>(`/api/sessions/${id}/reanalyze`, { method: "POST" }),
  deleteSession: (id: string) => request<void>(`/api/sessions/${id}`, { method: "DELETE" }),
  weeklyProgress: (weeks = 8) => {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    return request<Progress>(`/api/progress/weekly?weeks=${weeks}&tz=${encodeURIComponent(tz)}`);
  },
  videoUrl: (id: string) => `${API_URL}/api/sessions/${id}/video`,
};

/** Upload with progress events (fetch can't report upload progress). */
export function uploadSession(
  file: File,
  title: string,
  onProgress: (fraction: number) => void,
): Promise<SessionSummary> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);
    if (title.trim()) form.append("title", title.trim());
    xhr.open("POST", `${API_URL}/api/sessions`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* ignore */
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as SessionSummary);
      else {
        const detail = (body as { detail?: string } | null)?.detail;
        reject(new Error(detail || `Upload failed (${xhr.status})`));
      }
    };
    xhr.onerror = () => reject(new Error(`Can't reach the PushupPro API at ${API_URL}.`));
    xhr.send(form);
  });
}
