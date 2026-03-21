"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Film, Clock, Users, Sword } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Scene } from "@/types";
import { formatTimestamp } from "@/lib/utils";

export default function ScenesPage() {
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loading, setLoading] = useState(true);
  const [minConfidence, setMinConfidence] = useState(0.5);
  const [brokenImages, setBrokenImages] = useState<Record<string, boolean>>({});

  const maxSceneCharConfidence = (scene: Scene): number | undefined => {
    if (!scene.characters || scene.characters.length === 0) return undefined;
    const vals = scene.characters
      .map((c) => c.confidence)
      .filter((v): v is number => typeof v === "number");
    if (vals.length === 0) return undefined;
    return Math.max(...vals);
  };

  const filteredScenes = scenes.filter((scene) => {
    const conf = maxSceneCharConfidence(scene);
    if (typeof conf !== "number") return true;
    return conf >= minConfidence;
  });

  useEffect(() => {
    const fetchScenes = async () => {
      try {
        const data = await api.getScenes();
        setScenes(data);
      } catch (err) {
        console.error("Failed to fetch scenes:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchScenes();
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-8">
        <Film className="w-6 h-6 text-accent-blue" />
        <h1 className="text-2xl font-bold">Scenes</h1>
        <span className="badge-blue">{scenes.length}</span>
        <div className="ml-auto flex items-center gap-2 px-3 py-1.5 rounded-lg border border-surface-700 bg-surface-900">
          <label htmlFor="scene-confidence-filter" className="text-xs text-surface-400 whitespace-nowrap">
            Min char confidence
          </label>
          <input
            id="scene-confidence-filter"
            type="range"
            min={0.3}
            max={0.95}
            step={0.05}
            value={minConfidence}
            onChange={(e) => setMinConfidence(Number(e.target.value))}
            className="w-24 accent-primary-500"
          />
          <span className="text-xs font-mono text-surface-300 w-10 text-right">
            {(minConfidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="h-24 rounded-2xl bg-surface-800 animate-pulse"
            />
          ))}
        </div>
      ) : filteredScenes.length > 0 ? (
        <div className="space-y-3">
          {filteredScenes.map((scene, i) => (
            <motion.div
              key={scene.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              className="glass-panel p-4 hover:border-surface-700 transition-all cursor-pointer group"
            >
              <div className="flex items-start gap-4">
                {/* Thumbnail */}
                <div className="w-28 h-16 rounded-lg bg-surface-800 overflow-hidden flex-shrink-0">
                  {scene.thumbnail_url && !brokenImages[scene.id] ? (
                    <img
                      src={scene.thumbnail_url}
                      alt={`Scene ${scene.scene_index}`}
                      className="w-full h-full object-cover"
                      onError={() => setBrokenImages((prev) => ({ ...prev, [scene.id]: true }))}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Film className="w-6 h-6 text-surface-600" />
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-primary-400">
                      #{scene.scene_index}
                    </span>
                    <span className="text-xs text-surface-500">
                      {formatTimestamp(scene.start_time)}
                      {scene.end_time && ` — ${formatTimestamp(scene.end_time)}`}
                    </span>
                  </div>

                  {scene.description && (
                    <p className="text-sm text-surface-300 line-clamp-1 mb-2">
                      {scene.description}
                    </p>
                  )}

                  <div className="flex items-center gap-3">
                    {scene.location && (
                      <span className="badge-cyan">{scene.location}</span>
                    )}
                    {scene.characters && scene.characters.length > 0 && (
                      <span className="flex items-center gap-1 text-xs text-surface-500">
                        <Users className="w-3 h-3" />
                        {scene.characters.length}
                      </span>
                    )}
                    {typeof maxSceneCharConfidence(scene) === "number" && (
                      <span className="text-xs text-surface-500 font-mono">
                        conf {(maxSceneCharConfidence(scene)! * 100).toFixed(0)}%
                      </span>
                    )}
                    {scene.items && scene.items.length > 0 && (
                      <span className="flex items-center gap-1 text-xs text-surface-500">
                        <Sword className="w-3 h-3" />
                        {scene.items.length}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <Film className="w-12 h-12 text-surface-700 mx-auto mb-4" />
          <p className="text-surface-400">
            {scenes.length > 0 ? "No scenes match this confidence filter" : "No scenes detected yet"}
          </p>
          <p className="text-sm text-surface-600 mt-1">
            {scenes.length > 0
              ? "Lower the minimum character confidence threshold to include weaker detections."
              : "Start a capture session to begin detecting scenes"}
          </p>
        </div>
      )}
    </div>
  );
}
