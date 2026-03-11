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

export default function CaptureControl({ fullView }: CaptureControlProps) {
  const { status, setStatus, setStats, setSessionId } = useCaptureStore();
  const [title, setTitle] = useState("My Anime Session");
  const [fps, setFps] = useState(2);
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
    try {
      setStatus("starting");
      const response = await api.startCapture({ title, fps, source: "screen" });
      setSessionId(response.session_id);
      setStatus("capturing");
      pollStatus();
    } catch (err) {
      console.error("Failed to start capture:", err);
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
          charactersFound: data.characters_found,
          scenesDetected: data.scenes_detected,
          elapsed: data.elapsed_seconds,
        });
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
            onChange={(e) => setTitle(e.target.value)}
            className="search-input text-sm"
            placeholder="My Anime Session"
            disabled={status === "capturing"}
          />
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
            disabled={status === "capturing"}
          >
            <option value={1}>1 FPS — Low (saves storage)</option>
            <option value={2}>2 FPS — Default</option>
            <option value={5}>5 FPS — Smooth</option>
            <option value={10}>10 FPS — High</option>
            <option value={15}>15 FPS — Very High</option>
            <option value={30}>30 FPS — Max (heavy CPU)</option>
          </select>
          <p className="text-[11px] text-surface-600 mt-1">
            Higher FPS = more keyframes captured per second. Above 30 FPS is not achievable — Python screen capture peaks at ~30–50 FPS on Windows.
          </p>
        </div>
      </div>

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
