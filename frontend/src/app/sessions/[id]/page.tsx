"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Film,
  Clock,
  Loader2,
  Trash2,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Session, Scene } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function thumb(url: string | null | undefined): string | null {
  if (!url) return null;
  return url.startsWith("http") ? url : `${API_BASE}${url}`;
}

function fmtTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

/** Real display duration (ms) for scene[i] at 1x speed */
function frameDurationMs(scenes: Scene[], i: number): number {
  if (scenes.length < 2) return 5000;
  if (i < scenes.length - 1) {
    const d = (scenes[i + 1].start_time - scenes[i].start_time) * 1000;
    if (d >= 16) return d;
  }
  const avg =
    ((scenes[scenes.length - 1].start_time - scenes[0].start_time) /
      (scenes.length - 1)) * 1000;
  return avg >= 16 ? avg : 1000;
}

const SPEEDS = [0.25, 0.5, 1, 2] as const;
type Speed = typeof SPEEDS[number];

export default function SessionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  const [session, setSession] = useState<Session | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [current, setCurrent] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<Speed>(1);
  const [loop, setLoop] = useState(true);
  const [preloaded, setPreloaded] = useState(0);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const scenesRef     = useRef<Scene[]>([]);
  const currentRef    = useRef(0);
  const playingRef    = useRef(false);
  const speedRef      = useRef<Speed>(1);
  const loopRef       = useRef(true);
  const rafRef        = useRef<number | null>(null);
  const frameStartRef = useRef<number>(0);
  const stripRef      = useRef<HTMLDivElement>(null);
  const canvasRef     = useRef<HTMLCanvasElement>(null);
  const bgImgRef      = useRef<HTMLImageElement>(null);
  const cacheRef      = useRef<Map<number, HTMLImageElement>>(new Map());
  // Cross-fade state — blends outgoing→incoming frame during playback
  const fadeRef = useRef<{
    active: boolean;
    from: HTMLImageElement | null;
    to:   HTMLImageElement | null;
    start: number;
    duration: number;
  }>({ active: false, from: null, to: null, start: 0, duration: 80 });

  scenesRef.current  = scenes;
  currentRef.current = current;
  playingRef.current = playing;
  speedRef.current   = speed;
  loopRef.current    = loop;

  useEffect(() => () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); }, []);

  useEffect(() => {
    if (!id) return;
    Promise.all([api.getSession(id), api.getSessionScenes(id)])
      .then(([sess, sc]) => { setSession(sess); setScenes(sc); })
      .catch((e) => setError(String(e?.message ?? e)))
      .finally(() => setLoading(false));
  }, [id]);

  // Preload every scene image into browser cache
  useEffect(() => {
    if (scenes.length === 0) return;
    cacheRef.current.clear();
    setPreloaded(0);
    let done = 0;
    scenes.forEach((sc, i) => {
      const src = thumb(sc.thumbnail_url);
      if (!src) { done++; setPreloaded(done); return; }
      const img = new Image();
      img.onload = img.onerror = () => { done++; setPreloaded(done); };
      img.src = src;
      cacheRef.current.set(i, img);
    });
  }, [scenes]);

  // Draw a frame onto the canvas — drawImage on a preloaded HTMLImageElement is instant
  const drawFrame = useCallback((idx: number) => {
    const cached = cacheRef.current.get(idx);
    const canvas = canvasRef.current;
    if (!canvas) return;

    if (cached && cached.complete && cached.naturalWidth > 0) {
      if (canvas.width !== cached.naturalWidth || canvas.height !== cached.naturalHeight) {
        canvas.width  = cached.naturalWidth;
        canvas.height = cached.naturalHeight;
      }
      canvas.getContext("2d")?.drawImage(cached, 0, 0);
      if (bgImgRef.current) bgImgRef.current.src = cached.src;
    } else {
      // Fallback while preloading
      const src = thumb(scenesRef.current[idx]?.thumbnail_url);
      if (!src) return;
      const img = new Image();
      img.onload = () => {
        if (canvas.width !== img.naturalWidth || canvas.height !== img.naturalHeight) {
          canvas.width  = img.naturalWidth  || 1280;
          canvas.height = img.naturalHeight || 720;
        }
        canvas.getContext("2d")?.drawImage(img, 0, 0);
        if (bgImgRef.current) bgImgRef.current.src = src;
      };
      img.src = src;
    }
  }, []);

  // rAF loop — frame-accurate with cross-fade blending
  const rafLoop = useCallback((now: number) => {
    if (!playingRef.current) return;

    const canvas = canvasRef.current;
    const ctx    = canvas?.getContext("2d");
    const fade   = fadeRef.current;

    // Render blend while a cross-fade is in progress
    if (fade.active && ctx && canvas && fade.from && fade.to) {
      const t = Math.min((now - fade.start) / fade.duration, 1);
      ctx.globalAlpha = 1;
      ctx.drawImage(fade.from, 0, 0, canvas.width, canvas.height);
      ctx.globalAlpha = t;
      ctx.drawImage(fade.to,   0, 0, canvas.width, canvas.height);
      ctx.globalAlpha = 1;
      if (t >= 1) {
        fade.active = false;
        // Sync background to the now-fully-visible incoming frame
        if (bgImgRef.current && fade.to.src) bgImgRef.current.src = fade.to.src;
      }
    }

    const sc      = scenesRef.current;
    const idx     = currentRef.current;
    const dur     = frameDurationMs(sc, idx) / speedRef.current;
    const elapsed = now - frameStartRef.current;

    if (elapsed >= dur) {
      let next = idx + 1;
      if (next >= sc.length) {
        if (loopRef.current) next = 0;
        else {
          playingRef.current = false;
          setPlaying(false);
          return;
        }
      }

      // Snapshot canvas as "from" frame, get cached "to" frame
      const fromImg = cacheRef.current.get(idx);
      const toImg   = cacheRef.current.get(next);

      if (fromImg?.complete && toImg?.complete && canvas) {
        // Resize canvas to incoming frame dimensions before cross-fade
        if (canvas.width !== toImg.naturalWidth || canvas.height !== toImg.naturalHeight) {
          canvas.width  = toImg.naturalWidth  || canvas.width;
          canvas.height = toImg.naturalHeight || canvas.height;
        }
        const fadeDur = Math.min(dur * 0.4, 100); // dur already speed-adjusted
        fadeRef.current = { active: true, from: fromImg, to: toImg, start: now, duration: fadeDur };
      } else {
        // Fallback: hard-cut
        drawFrame(next);
      }

      currentRef.current = next;
      setCurrent(next);
      frameStartRef.current = now;
    }

    rafRef.current = requestAnimationFrame(rafLoop);
  }, [drawFrame]);

  const startRaf = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    frameStartRef.current = performance.now();
    rafRef.current = requestAnimationFrame(rafLoop);
  }, [rafLoop]);

  const stopRaf = useCallback(() => {
    if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = null; }
  }, []);

  const play = useCallback(() => {
    if (scenesRef.current.length < 2) return;
    playingRef.current = true;
    setPlaying(true);
    startRaf();
  }, [startRaf]);

  const pause = useCallback(() => {
    playingRef.current = false;
    setPlaying(false);
    stopRaf();
  }, [stopRaf]);

  const togglePlay = useCallback(() => {
    if (playingRef.current) pause(); else play();
  }, [play, pause]);

  const go = useCallback((index: number) => {
    const clamped = Math.max(0, Math.min(index, scenesRef.current.length - 1));
    currentRef.current = clamped;
    setCurrent(clamped);
    drawFrame(clamped);
    // If already playing, reset frame timer so this frame gets its full duration
    if (playingRef.current) frameStartRef.current = performance.now();
  }, [drawFrame]);

  // prev/next intentionally do NOT pause — navigation keeps playback going
  const prev = useCallback(() => go(currentRef.current - 1), [go]);
  const next = useCallback(() => go(currentRef.current + 1), [go]);

  const handleDelete = useCallback(async () => {
    setDeleting(true);
    try {
      await api.deleteSession(id);
      router.push("/sessions");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`Delete failed: ${msg}`);
      setDeleting(false);
      setConfirmDelete(false);
    }
  }, [id, router]);

  useEffect(() => {
    if (playingRef.current) frameStartRef.current = performance.now();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speed]);

  // Initial / manual render when current changes outside rAF loop
  useEffect(() => { drawFrame(current); }, [current, drawFrame]);

  useEffect(() => {
    const strip = stripRef.current;
    if (!strip) return;
    const el = strip.children[current] as HTMLElement | undefined;
    el?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [current]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === "INPUT") return;
      if (e.key === "ArrowLeft")  prev();
      if (e.key === "ArrowRight") next();
      if (e.key === " ") { e.preventDefault(); togglePlay(); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [prev, next, togglePlay]);

  if (loading)
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
      </div>
    );

  if (error)
    return (
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <Film className="w-12 h-12 mx-auto mb-4 text-surface-700" />
        <p className="text-red-400 mb-2">
          {error.includes("404") ? "Session not found" : error}
        </p>
        <p className="text-sm text-surface-500 mb-6">
          {error.includes("404")
            ? "This session may have been deleted or the server was restarted."
            : "Something went wrong while loading this session."}
        </p>
        <button onClick={() => router.push("/sessions")} className="text-sm text-primary-400 hover:underline">
          Back to sessions
        </button>
      </div>
    );

  const scene     = scenes[current] ?? null;
  const canPlay   = scenes.length >= 2;
  const allLoaded = preloaded >= scenes.length;

  return (
    <div className="flex flex-col bg-black" style={{ height: "calc(100vh - 4rem)" }}>

      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-surface-800 bg-surface-950 shrink-0">
        <button
          onClick={() => { pause(); router.push("/sessions"); }}
          className="flex items-center gap-1.5 text-sm text-surface-400 hover:text-surface-100 transition-colors shrink-0"
        >
          <ArrowLeft className="w-4 h-4" />
          Sessions
        </button>
        <span className="h-4 w-px bg-surface-700" />
        <h1 className="font-semibold text-surface-100 truncate">{session?.title ?? id}</h1>
        <div className="ml-auto flex items-center gap-3 shrink-0">
          {!allLoaded && (
            <span className="flex items-center gap-1.5 text-xs text-surface-500">
              <Loader2 className="w-3 h-3 animate-spin" />
              Buffering {preloaded}/{scenes.length}
            </span>
          )}
          {playing && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-600/80 text-xs text-white font-medium animate-pulse">
              Playing
            </span>
          )}
          <span className="text-xs text-surface-500">
            {scenes.length} frame{scenes.length !== 1 ? "s" : ""}
          </span>

          {/* Delete button */}
          {!confirmDelete ? (
            <button
              onClick={() => setConfirmDelete(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-red-400 border border-red-500/20 hover:bg-red-500/10 hover:border-red-500/40 transition-all"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-xs text-red-400">Delete this session?</span>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-2.5 py-1 rounded text-xs font-medium bg-red-600 hover:bg-red-500 text-white disabled:opacity-50 transition-colors"
              >
                {deleting ? "Deleting…" : "Yes, delete"}
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-2.5 py-1 rounded text-xs text-surface-400 hover:text-surface-200 border border-surface-700 hover:bg-surface-800 transition-all"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>

      {scenes.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-surface-500">
          <Film className="w-12 h-12 mb-4 opacity-30" />
          <p>No scenes captured yet.</p>
          <p className="text-sm mt-1">Go to <strong>Capture</strong> and press Start while watching anime.</p>
        </div>
      ) : (
        <>
          {/* Main viewer */}
          <div className="relative flex-1 min-h-0 bg-black select-none overflow-hidden flex items-center justify-center">
            {/* Blurred background */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={bgImgRef}
              alt=""
              aria-hidden
              className="absolute inset-0 w-full h-full object-cover opacity-20 blur-2xl scale-110 pointer-events-none"
            />
            {/* Canvas frame — drawImage on preloaded HTMLImageElement is instant; no repaint flash */}
            <canvas
              ref={canvasRef}
              className="relative z-[1] max-w-full max-h-full"
              style={{ display: "block" }}
            />
            {/* Buffering overlay */}
            {!allLoaded && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/50 z-20 pointer-events-none">
                <Loader2 className="w-8 h-8 text-primary-400 animate-spin mb-2" />
                <span className="text-xs text-surface-400">Buffering… {preloaded}/{scenes.length}</span>
              </div>
            )}
            {/* Click zones — do NOT pause; navigation continues playback */}
            <button onClick={prev}
              className="absolute left-0 top-0 h-full w-1/5 flex items-center justify-start pl-3 group z-10">
              <span className="p-2 rounded-full bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <ChevronLeft className="w-7 h-7" />
              </span>
            </button>
            <button onClick={next}
              className="absolute right-0 top-0 h-full w-1/5 flex items-center justify-end pr-3 group z-10">
              <span className="p-2 rounded-full bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity">
                <ChevronRight className="w-7 h-7" />
              </span>
            </button>
            {/* HUD */}
            <span className="absolute top-3 right-3 px-2.5 py-1 rounded-full bg-black/70 text-xs text-white font-mono pointer-events-none z-10">
              {current + 1} / {scenes.length}
            </span>
            {scene && (
              <div className="absolute bottom-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/70 text-xs text-surface-300 pointer-events-none z-10">
                <Clock className="w-3 h-3" />
                {fmtTime(scene.start_time)}
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="shrink-0 bg-surface-950 border-t border-surface-800 px-3 pt-2 pb-2 space-y-1.5">
            <input
              type="range" min={0} max={Math.max(scenes.length - 1, 1)} value={current}
              onChange={(e) => go(Number(e.target.value))}
              className="w-full h-1.5 rounded-full accent-primary-500 cursor-pointer"
            />
            <div className="flex items-center gap-1">
              <button onClick={() => go(0)} disabled={current === 0}
                className="p-1.5 rounded text-surface-400 hover:text-white hover:bg-surface-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                <SkipBack className="w-4 h-4" />
              </button>
              <button onClick={prev}
                className="p-1.5 rounded text-surface-400 hover:text-white hover:bg-surface-800 transition-all">
                <ChevronLeft className="w-5 h-5" />
              </button>

              <button onClick={togglePlay} disabled={!canPlay || !allLoaded}
                title={!allLoaded ? "Buffering…" : canPlay ? "Play / Pause (Space)" : "Need at least 2 frames"}
                className="flex items-center justify-center w-9 h-9 rounded-full bg-primary-600 hover:bg-primary-500 disabled:opacity-30 disabled:cursor-not-allowed text-white shadow-lg transition-all mx-1">
                {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
              </button>

              <button onClick={next}
                className="p-1.5 rounded text-surface-400 hover:text-white hover:bg-surface-800 transition-all">
                <ChevronRight className="w-5 h-5" />
              </button>
              <button onClick={() => go(scenes.length - 1)} disabled={current === scenes.length - 1}
                className="p-1.5 rounded text-surface-400 hover:text-white hover:bg-surface-800 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                <SkipForward className="w-4 h-4" />
              </button>

              <span className="text-xs text-surface-600 font-mono ml-1 tabular-nums select-none">
                {fmtTime(scene?.start_time ?? 0)}
              </span>
              <div className="flex-1" />

              <div className="flex rounded overflow-hidden border border-surface-700">
                {SPEEDS.map((s) => (
                  <button key={s} onClick={() => setSpeed(s)}
                    className={`px-2 py-1 text-xs font-medium transition-colors ${
                      speed === s ? "bg-primary-600 text-white" : "bg-surface-800 text-surface-500 hover:text-white hover:bg-surface-700"
                    }`}>
                    {s}x
                  </button>
                ))}
              </div>

              <button onClick={() => setLoop((l) => !l)}
                className={`px-2 py-1 rounded text-xs font-medium border transition-all ml-1 ${
                  loop ? "bg-primary-600/20 border-primary-500/40 text-primary-300" : "bg-surface-800 border-surface-700 text-surface-500 hover:text-surface-300"
                }`}>
                {loop ? "↺ On" : "↺ Off"}
              </button>
              <span className="hidden lg:block text-xs text-surface-700 ml-2 select-none">← → Space</span>
            </div>

            {scenes.length > 1 && (
              <div ref={stripRef} className="flex gap-1.5 overflow-x-auto" style={{ scrollbarWidth: "thin" }}>
                {scenes.map((sc, i) => {
                  const src = thumb(sc.thumbnail_url);
                  return (
                    <button key={sc.id} onClick={() => go(i)}
                      title={`Frame ${sc.scene_index} — ${fmtTime(sc.start_time)}`}
                      className={`relative flex-shrink-0 w-20 h-12 rounded overflow-hidden border-2 transition-all duration-150 ${
                        i === current ? "border-primary-500" : "border-surface-700 hover:border-surface-500 opacity-50 hover:opacity-90"
                      }`}>
                      {src
                        // eslint-disable-next-line @next/next/no-img-element
                        ? <img src={src} alt="" className="w-full h-full object-cover" />
                        : <div className="w-full h-full bg-surface-800 flex items-center justify-center"><Film className="w-3 h-3 text-surface-600" /></div>
                      }
                      <span className="absolute bottom-0 left-0 right-0 text-center text-[9px] text-white bg-black/60 leading-4">{i + 1}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}