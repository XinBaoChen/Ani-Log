"use client";

import { Clock, MapPin } from "lucide-react";
import { formatTimestamp } from "@/lib/utils";
import type { Appearance } from "@/types";

interface SceneTimelineProps {
  appearances: Appearance[];
}

export default function SceneTimeline({ appearances }: SceneTimelineProps) {
  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-4 top-0 bottom-0 w-px bg-surface-700" />

      <div className="space-y-4">
        {appearances.map((appearance, i) => (
          <div key={appearance.id} className="relative pl-10">
            {/* Timeline dot */}
            <div className="absolute left-[11px] top-1.5 w-2.5 h-2.5 rounded-full bg-primary-500 ring-4 ring-surface-900" />

            <div className="glass-panel p-3">
              <div className="flex items-center gap-2 mb-1">
                <Clock className="w-3.5 h-3.5 text-surface-500" />
                <span className="text-xs font-mono text-primary-400">
                  {formatTimestamp(appearance.timestamp)}
                </span>
                <span className="text-xs text-surface-600">
                  Scene {appearance.scene_id.slice(0, 8)}...
                </span>
              </div>

              {appearance.confidence > 0 && (
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1 bg-surface-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary-500 rounded-full"
                      style={{ width: `${appearance.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-surface-500">
                    {(appearance.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
