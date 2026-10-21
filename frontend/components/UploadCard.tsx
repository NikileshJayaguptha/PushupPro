"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { uploadSession } from "@/lib/api";

const ACCEPT = ".mp4,.mov,.m4v,.webm,.avi,.mkv,video/*";

export default function UploadCard() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [over, setOver] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  function pick(f: File | undefined | null) {
    if (!f) return;
    setError(null);
    setFile(f);
  }

  async function submit() {
    if (!file) return;
    setError(null);
    setProgress(0);
    try {
      const session = await uploadSession(file, title, setProgress);
      router.push(`/sessions/${session.id}`);
    } catch (e) {
      setError((e as Error).message);
      setProgress(null);
    }
  }

  const uploading = progress !== null;

  return (
    <section className="panel" aria-labelledby="upload-title">
      <h2 id="upload-title">Analyze a set</h2>
      <p className="muted" style={{ margin: "4px 0 14px", fontSize: 15 }}>
        Film from the side, with your whole body in frame, at about hip height.
      </p>

      <div
        className={`drop${over ? " over" : ""}`}
        role="button"
        tabIndex={0}
        onClick={() => input.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          pick(e.dataTransfer.files?.[0]);
        }}
      >
        {file ? (
          <>
            <strong>{file.name}</strong>
            <span className="muted">{(file.size / 1024 / 1024).toFixed(1)} MB · choose a different video</span>
          </>
        ) : (
          <>
            <strong>Drop a workout video here</strong>
            <span className="muted">or click to choose one (MP4, MOV, WebM)</span>
          </>
        )}
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          hidden
          onChange={(e) => pick(e.target.files?.[0])}
        />
      </div>

      <div className="field">
        <label htmlFor="set-title">Name (optional)</label>
        <input
          id="set-title"
          value={title}
          placeholder="e.g. Morning set"
          maxLength={200}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>

      {uploading && (
        <div style={{ marginTop: 14 }}>
          <div className="bar" role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100}>
            <div style={{ width: `${progress * 100}%` }} />
          </div>
          <div className="muted" style={{ fontSize: 14, marginTop: 4 }}>
            Uploading {Math.round(progress * 100)}%
          </div>
        </div>
      )}
      {error && <p className="error" role="alert">{error}</p>}

      <button className="btn btn-primary" style={{ marginTop: 16, width: "100%", justifyContent: "center" }}
        disabled={!file || uploading} onClick={submit}>
        {uploading ? "Uploading…" : "Upload and analyze"}
      </button>
    </section>
  );
}
