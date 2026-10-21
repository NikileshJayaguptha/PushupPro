"use client";

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef } from "react";
import type { Trace } from "@/lib/types";
import { BODY_FLAG_DEG, frameIndexAt } from "@/lib/trace";

export interface PlayerHandle {
  seek: (t: number, play?: boolean) => void;
}

interface Props {
  src: string;
  trace: Trace | null;
  side: string | null;
  showSkeleton: boolean;
  showAngles: boolean;
  onTime: (t: number) => void;
}

// COCO indices of the tracked side's joints.
const SIDE = {
  left: { shoulder: 5, elbow: 7, wrist: 9, hip: 11, knee: 13, ankle: 15 },
  right: { shoulder: 6, elbow: 8, wrist: 10, hip: 12, knee: 14, ankle: 16 },
} as const;

const MIN_CONF = 0.35;

function cssVar(el: Element, name: string, fallback: string) {
  return getComputedStyle(el).getPropertyValue(name).trim() || fallback;
}

const SkeletonPlayer = forwardRef<PlayerHandle, Props>(function SkeletonPlayer(
  { src, trace, side, showSkeleton, showAngles, onTime },
  ref,
) {
  const video = useRef<HTMLVideoElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const lastReported = useRef(-1);

  useImperativeHandle(ref, () => ({
    seek(t, play = false) {
      const v = video.current;
      if (!v) return;
      v.currentTime = Math.max(0, t);
      if (play) void v.play();
    },
  }));

  const draw = useCallback(() => {
    const v = video.current;
    const c = canvas.current;
    if (!v || !c) return;

    // Throttle React updates (~12 Hz); canvas redraws every frame.
    if (Math.abs(v.currentTime - lastReported.current) > 0.08 || v.paused) {
      lastReported.current = v.currentTime;
      onTime(v.currentTime);
    }

    const dpr = window.devicePixelRatio || 1;
    const rect = c.getBoundingClientRect();
    if (c.width !== Math.round(rect.width * dpr) || c.height !== Math.round(rect.height * dpr)) {
      c.width = Math.round(rect.width * dpr);
      c.height = Math.round(rect.height * dpr);
    }
    const ctx = c.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);
    if (!trace || !showSkeleton || !v.videoWidth) return;

    const i = frameIndexAt(trace.times, v.currentTime);
    const kps = trace.keypoints[i];
    if (!kps) return;

    // Map video pixels into the letterboxed content box of the <video>.
    const scale = Math.min(rect.width / v.videoWidth, rect.height / v.videoHeight);
    const ox = (rect.width - v.videoWidth * scale) / 2;
    const oy = (rect.height - v.videoHeight * scale) / 2;
    const P = (k: number): [number, number] => [ox + kps[k][0] * scale, oy + kps[k][1] * scale];
    const ok = (k: number) => kps[k] && kps[k][2] >= MIN_CONF;

    const near = SIDE[(side as "left" | "right") || "left"] ?? SIDE.left;
    const nearSet = new Set<number>(Object.values(near));
    const accent = cssVar(c, "--accent", "#0f7a72");
    const good = cssVar(c, "--good", "#2e8b57");
    const poor = cssVar(c, "--poor", "#c23b2e");
    const bodyDev = trace.body[i];
    const bodyBad = bodyDev != null && Math.abs(bodyDev) > BODY_FLAG_DEG;

    ctx.lineCap = "round";
    // Far-side limbs: faint, so the measured side reads first.
    for (const [a, b] of trace.skeleton) {
      if (!ok(a) || !ok(b)) continue;
      const isNear = nearSet.has(a) && nearSet.has(b);
      if (isNear) continue;
      ctx.strokeStyle = "rgba(255,255,255,0.45)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(...P(a));
      ctx.lineTo(...P(b));
      ctx.stroke();
    }
    // Arm on the measured side.
    const arm: [number, number][] = [[near.shoulder, near.elbow], [near.elbow, near.wrist]];
    for (const [a, b] of arm) {
      if (!ok(a) || !ok(b)) continue;
      ctx.strokeStyle = accent;
      ctx.lineWidth = 5;
      ctx.beginPath();
      ctx.moveTo(...P(a));
      ctx.lineTo(...P(b));
      ctx.stroke();
    }
    // Body line shoulder-hip-ankle, green when straight and red when sagging/piking.
    const foot = ok(near.ankle) ? near.ankle : near.knee;
    if (ok(near.shoulder) && ok(near.hip) && ok(foot)) {
      ctx.strokeStyle = bodyBad ? poor : good;
      ctx.lineWidth = 5;
      ctx.beginPath();
      ctx.moveTo(...P(near.shoulder));
      ctx.lineTo(...P(near.hip));
      ctx.lineTo(...P(foot));
      ctx.stroke();
      // Dashed reference: where a straight plank would be.
      ctx.setLineDash([6, 6]);
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "rgba(255,255,255,0.7)";
      ctx.beginPath();
      ctx.moveTo(...P(near.shoulder));
      ctx.lineTo(...P(foot));
      ctx.stroke();
      ctx.setLineDash([]);
    }
    // Joints.
    for (let k = 0; k < kps.length; k++) {
      if (!ok(k)) continue;
      const [x, y] = P(k);
      ctx.fillStyle = nearSet.has(k) ? "#fff" : "rgba(255,255,255,0.55)";
      ctx.beginPath();
      ctx.arc(x, y, nearSet.has(k) ? 4.5 : 3, 0, Math.PI * 2);
      ctx.fill();
    }
    // Angle labels.
    if (showAngles) {
      const label = (text: string, [x, y]: [number, number], color: string) => {
        ctx.font = "600 15px 'Barlow Condensed', sans-serif";
        const w = ctx.measureText(text).width + 10;
        ctx.fillStyle = "rgba(0,0,0,0.65)";
        ctx.fillRect(x + 8, y - 22, w, 20);
        ctx.fillStyle = color;
        ctx.fillText(text, x + 13, y - 7);
      };
      const elbow = trace.elbow[i];
      if (elbow != null && ok(near.elbow)) label(`${Math.round(elbow)}°`, P(near.elbow), "#fff");
      if (bodyDev != null && ok(near.hip)) {
        const txt = Math.abs(bodyDev) < 3 ? "straight" : `${Math.round(Math.abs(bodyDev))}° ${bodyDev > 0 ? "sag" : "pike"}`;
        label(txt, P(near.hip), bodyBad ? "#ffb4aa" : "#b8f0cc");
      }
    }
  }, [trace, side, showSkeleton, showAngles, onTime]);

  // Redraw loop: requestVideoFrameCallback where supported, rAF otherwise.
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    let stop = false;
    let handle = 0;
    const hasRVFC = "requestVideoFrameCallback" in HTMLVideoElement.prototype;
    const tick = () => {
      if (stop) return;
      draw();
      handle = hasRVFC
        ? (v as HTMLVideoElement & { requestVideoFrameCallback: (cb: () => void) => number }).requestVideoFrameCallback(tick)
        : requestAnimationFrame(tick);
    };
    tick();
    const redraw = () => draw();
    v.addEventListener("seeked", redraw);
    v.addEventListener("loadeddata", redraw);
    v.addEventListener("pause", redraw);
    window.addEventListener("resize", redraw);
    return () => {
      stop = true;
      if (hasRVFC) (v as HTMLVideoElement & { cancelVideoFrameCallback: (h: number) => void }).cancelVideoFrameCallback(handle);
      else cancelAnimationFrame(handle);
      v.removeEventListener("seeked", redraw);
      v.removeEventListener("loadeddata", redraw);
      v.removeEventListener("pause", redraw);
      window.removeEventListener("resize", redraw);
    };
  }, [draw]);

  return (
    <div className="player">
      <video ref={video} src={src} controls playsInline preload="auto" />
      <canvas ref={canvas} aria-hidden="true" />
    </div>
  );
});

export default SkeletonPlayer;
