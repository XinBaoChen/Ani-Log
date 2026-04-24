"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Play, Square, Loader2, ExternalLink } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useCaptureStore } from "@/store/useCaptureStore";
import { api } from "@/lib/api";

interface CaptureControlProps {
  fullView?: boolean;
}

function formatCaptureError(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  const cleaned = raw.replace(/^API Error\s+\d+:\s*/i, "").trim();
  if (cleaned) return cleaned;
  return "Failed to start capture.";
}

export default function CaptureControl({ fullView }: CaptureControlProps) {
  const { status, setStatus, setStats, setSessionId } = useCaptureStore();
  const [title, setTitle] = useState("");
  const [titleError, setTitleError] = useState<string | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [fps, setFps] = useState(2);
  const [preset, setPreset] = useState<"balanced" | "performance">("balanced");
  const [lastSessionId, setLastSessionId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const router = useRouter();

  // On mount: reconcile store with real backend state so stale "capturing"
  // left over from a previous session / server restart doesn't lock the UI.
  useEffect(() => {
    const sync = async () => {
      try {
        const data = await api.getCaptureStatus();
        if (data.status !== "capturing") {
          setStatus("idle");
          setSessionId(null);
        } else {
          setStatus("capturing");
          pollStatus();
        }
      } catch {
        // Backend unreachable — reset to idle so the button is usable
        setStatus("idle");
      }
    };
    sync();

    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleStart = async () => {
    const normalizedTitle = title.trim().toLowerCase();
    const genericTitles = new Set([
      "",
      "my anime session",
      "character test",
      "character detection validation",
      "balanced stress smoke",
      "perf stress smoke",
    ]);
    if (genericTitles.has(normalizedTitle)) {
      setTitleError("Enter the anime title (example: Karakai Jouzu no Takagi-san) so character names can be assigned correctly.");
      setStatus("idle");
      return;
    }

    setTitleError(null);
    setCaptureError(null);
    try {
      setStatus("starting");
      const isPerformance = preset === "performance";
      const response = await api.startCapture({
        title: title.trim(),
        fps: isPerformance ? 6 : fps,
        source: "screen",
        performance_mode: isPerformance,
        adaptive_keyframes: isPerformance,
      });
      setSessionId(response.session_id);
      setStatus("capturing");
      pollStatus();
    } catch (err) {
      console.error("Failed to start capture:", err);
      setCaptureError(formatCaptureError(err));
      setStatus("idle");
    }
  };

  const handleStop = async () => {
    // Save session ID before clearing so we can navigate to it
    const capturedSessionId = useCaptureStore.getState().sessionId;

    // Optimistically reset UI immediately
    setStatus("idle");
    setSessionId(null);
    if (pollRef.current) clearTimeout(pollRef.current);

    try {
      await api.stopCapture();
    } catch (err: unknown) {
      // 400 "No active capture session" is fine — backend already stopped
      const msg = err instanceof Error ? err.message : String(err);
      if (!msg.includes("400")) {
        console.error("Failed to stop capture:", err);
      }
    }

    // Remember last session so user can navigate to view it
    if (capturedSessionId) {
      setLastSessionId(capturedSessionId);
    }
  };

  const pollStatus = () => {
    const tick = async () => {
      try {
        const data = await api.getCaptureStatus();
        setStats({
          totalFrames: data.total_frames,
          skippedFrames: data.skipped_frames ?? 0,
          errorFrames: data.error_frames ?? 0,
          charactersFound: data.characters_found,
          scenesDetected: data.scenes_detected,
          effectiveFps: data.effective_fps ?? 0,
          elapsed: data.elapsed_seconds,
        });
        if (data.status === "capturing" && data.total_frames === 0 && data.last_error) {
          setCaptureError(String(data.last_error));
        }
        if (data.status === "capturing") {
          pollRef.current = setTimeout(tick, 1000);
        } else {
          setStatus("idle");
        }
      } catch {
        setStatus("idle");
      }
    };
    tick();
  };

  if (!fullView) {
    // Compact floating control
    return (
      <AnimatePresence>
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="fixed bottom-6 right-6 z-40"
        >
          {status === "capturing" ? (
            <button
              onClick={handleStop}
              className="flex items-center gap-2 px-5 py-3 bg-red-600 hover:bg-red-500 text-white
                       rounded-full shadow-2xl shadow-red-600/30 transition-all group"
            >
              <Square className="w-4 h-4 group-hover:scale-110 transition-transform" />
              <span className="text-sm font-medium">Stop Capture</span>
              <span className="w-2 h-2 bg-red-300 rounded-full animate-pulse" />
            </button>
          ) : (
            <button
              onClick={handleStart}
              disabled={status === "starting"}
              className="flex items-center gap-2 px-5 py-3 bg-primary-600 hover:bg-primary-500 text-white
                       rounded-full shadow-2xl shadow-primary-600/30 transition-all
                       disabled:opacity-50 group"
            >
              {status === "starting" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4 group-hover:scale-110 transition-transform" />
              )}
              <span className="text-sm font-medium">Start Capture</span>
            </button>
          )}
        </motion.div>
      </AnimatePresence>
    );
  }

  // Full control panel
  return (
    <div className="space-y-4">
      {/* Settings */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="text-xs font-medium text-surface-400 mb-1.5 block">
            Session Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (titleError) setTitleError(null);
            }}
            className="search-input text-sm"
            placeholder="Anime title (example: Karakai Jouzu no Takagi-san)"
            disabled={status === "capturing"}
          />
          {titleError && (
            <p className="text-[11px] text-red-400 mt-1">
              {titleError}
            </p>
          )}
        </div>

        <div>
          <label className="text-xs font-medium text-surface-400 mb-1.5 block">
            Capture Preset
          </label>
          <select
            value={preset}
            onChange={(e) => setPreset(e.target.value as "balanced" | "performance")}
            className="w-full px-3 py-3 bg-surface-900 border border-surface-700 rounded-xl
                       text-sm text-surface-300 focus:outline-none focus:border-primary-500"
            disabled={status === "capturing"}
          >
            <option value="balanced">Balanced — normal capture</option>
            <option value="performance">Performance Mode — smoother long sessions (6 FPS + adaptive keyframes)</option>
          </select>
          <p className="text-[11px] text-surface-600 mt-1">
            Performance mode keeps scrolling smoother while reducing CPU by combining adaptive keyframes with lighter detection frequency.
          </p>
        </div>

        <div>
          <label className="text-xs font-medium text-surface-400 mb-1.5 block">
            Sample FPS
          </label>
          <select
            value={fps}
            onChange={(e) => setFps(Number(e.target.value))}
            className="w-full px-3 py-3 bg-surface-900 border border-surface-700 rounded-xl
                       text-sm text-surface-300 focus:outline-none focus:border-primary-500"
            disabled={status === "capturing" || preset === "performance"}
          >
            <option value={1}>1 FPS — Low (saves storage)</option>
            <option value={2}>2 FPS — Default</option>
            <option value={5}>5 FPS — Smooth</option>
            <option value={10}>10 FPS — High</option>
            <option value={15}>15 FPS — Very High</option>
            <option value={30}>30 FPS — Max (heavy CPU)</option>
          </select>
          <p className="text-[11px] text-surface-600 mt-1">
            {preset === "performance"
              ? "Locked by Performance Mode: 6 FPS sampling, adaptive keyframes, and lighter detection stride for smoother capture."
              : "Higher FPS = more keyframes captured per second. Above 30 FPS is not achievable — Python screen capture peaks at ~30–50 FPS on Windows."}
          </p>
        </div>
      </div>

      {captureError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2">
          <p className="text-xs text-red-300">{captureError}</p>
        </div>
      )}

      {/* Control Buttons */}
      <div className="flex items-center gap-3">
        {status === "capturing" ? (
          <button onClick={handleStop} className="btn-primary bg-red-600 hover:bg-red-500 flex items-center gap-2">
            <Square className="w-4 h-4" />
            Stop Capture
          </button>
        ) : (
          <button
            onClick={handleStart}
            disabled={status === "starting"}
            className="btn-primary flex items-center gap-2"
          >
            {status === "starting" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            Start Capture
          </button>
        )}

        {status === "capturing" && (
          <span className="flex items-center gap-2 text-sm text-green-400">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            Capturing...
          </span>
        )}

        {status === "idle" && lastSessionId && (
          <button
            onClick={() => router.push(`/sessions/${lastSessionId}`)}
            className="flex items-center gap-2 text-sm text-primary-400 hover:text-primary-300 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            View Last Session
          </button>
        )}
      </div>
    </div>
  );
}
