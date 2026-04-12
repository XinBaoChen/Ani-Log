"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { BookOpen, Sparkles, Loader2, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { useCaptureStore } from "@/store/useCaptureStore";
import type { StoryArc } from "@/types";

interface StoryArcSummaryProps {
  sessionId?: string;
}

export default function StoryArcSummary({ sessionId: fixedSessionId }: StoryArcSummaryProps) {
  const [arcs, setArcs] = useState<StoryArc[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { sessionId: activeCaptureSessionId } = useCaptureStore();
  const sessionId = fixedSessionId ?? activeCaptureSessionId ?? undefined;

  useEffect(() => {
    fetchArcs();
  }, [sessionId]);

  const fetchArcs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStoryArcs(sessionId);
      setArcs(data);
    } catch (err) {
      console.error("Failed to fetch arcs:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch story arcs");
    } finally {
      setLoading(false);
    }
  };

  const generateSummary = async () => {
    if (!sessionId) return;

    setGenerating(true);
    setError(null);
    try {
      const arc = await api.generateSummary({
        session_id: sessionId,
        detail_level: "medium",
      });
      setArcs((prev) => [arc, ...prev]);
    } catch (err) {
      console.error("Failed to generate summary:", err);
      setError(err instanceof Error ? err.message : "Failed to generate summary");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="glass-panel p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-accent-amber" />
          Story Arcs
        </h2>

        <div className="flex items-center gap-2">
          <button onClick={fetchArcs} className="btn-ghost p-2">
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={generateSummary}
            disabled={generating || !sessionId}
            title={sessionId ? "Generate summary" : "Start capture or open a specific session first"}
            className="btn-primary flex items-center gap-2 text-xs"
          >
            {generating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            Generate Summary
          </button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-24 rounded-xl bg-surface-800 animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-8">
          <p className="text-sm text-red-400">{error}</p>
          <button onClick={fetchArcs} className="btn-ghost mt-3 text-xs">Retry</button>
        </div>
      ) : arcs.length > 0 ? (
        <div className="space-y-4">
          {arcs.map((arc, i) => (
            <motion.div
              key={arc.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-4 bg-surface-800/50 rounded-xl border border-surface-700/50"
            >
              <h3 className="font-semibold text-surface-200 mb-2">
                {arc.title}
              </h3>
              <p className="text-sm text-surface-400 leading-relaxed whitespace-pre-line">
                {arc.summary}
              </p>

              <div className="flex items-center gap-4 mt-3 text-xs text-surface-600">
                {arc.character_ids && (
                  <span>{arc.character_ids.length} characters</span>
                )}
                {arc.scene_ids && (
                  <span>{arc.scene_ids.length} scenes</span>
                )}
                <span>
                  {new Date(arc.generated_at).toLocaleDateString()}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8">
          <BookOpen className="w-8 h-8 text-surface-700 mx-auto mb-3" />
          <p className="text-sm text-surface-500">No story arcs yet</p>
          <p className="text-xs text-surface-600 mt-1">
            {sessionId
              ? "Generate a summary for this session"
              : "Start a capture session or open Session Detail, then generate a summary"}
          </p>
        </div>
      )}
    </div>
  );
}
