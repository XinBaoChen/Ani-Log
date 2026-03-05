"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  MonitorPlay,
  Play,
  Square,
  Settings,
  Activity,
  Users,
  Film,
  Sparkles,
} from "lucide-react";
import CaptureControl from "@/components/CaptureControl";
import StoryArcSummary from "@/components/StoryArcSummary";
import { useCaptureStore } from "@/store/useCaptureStore";

export default function CapturePage() {
  const { status, stats } = useCaptureStore();

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-8">
        <MonitorPlay className="w-6 h-6 text-accent-amber" />
        <h1 className="text-2xl font-bold">Capture</h1>
        {status === "capturing" && (
          <span className="badge bg-green-500/15 text-green-400 animate-pulse">
            ● Live
          </span>
        )}
      </div>

      {/* Capture Control Panel */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-6 mb-6"
      >
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Settings className="w-5 h-5 text-surface-400" />
          Capture Session
        </h2>

        <CaptureControl fullView />
      </motion.div>

      {/* Live Stats */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6"
      >
        {[
          {
            icon: Activity,
            label: "Frames",
            value: stats.totalFrames,
            color: "text-accent-amber",
          },
          {
            icon: Users,
            label: "Characters",
            value: stats.charactersFound,
            color: "text-primary-400",
          },
          {
            icon: Film,
            label: "Scenes",
            value: stats.scenesDetected,
            color: "text-accent-blue",
          },
          {
            icon: Sparkles,
            label: "Elapsed",
            value: `${Math.floor(stats.elapsed)}s`,
            color: "text-accent-cyan",
          },
        ].map((stat) => (
          <div key={stat.label} className="card text-center">
            <stat.icon className={`w-5 h-5 ${stat.color} mx-auto mb-2`} />
            <p className="text-xl font-bold text-surface-100">{stat.value}</p>
            <p className="text-xs text-surface-500">{stat.label}</p>
          </div>
        ))}
      </motion.div>

      {/* Story Arc Summaries */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <StoryArcSummary />
      </motion.div>
    </div>
  );
}
