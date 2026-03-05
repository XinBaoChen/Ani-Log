"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Film, Clock, LayoutGrid, ChevronRight, Loader2, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Session } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function thumb(url: string | null) {
  if (!url) return null;
  return url.startsWith("http") ? url : `${API_BASE}${url}`;
}

function formatDuration(s: Session) {
  if (!s.ended_at) return s.status === "capturing" ? "Live" : "—";
  const ms =
    new Date(s.ended_at).getTime() - new Date(s.started_at).getTime();
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  return `${min}m ${sec % 60}s`;
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  useEffect(() => {
    api
      .getSessions()
      .then(setSessions)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await api.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`Delete failed: ${msg}`);
    } finally {
      setDeletingId(null);
      setConfirmId(null);
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="flex items-center gap-3 mb-8">
        <Film className="w-6 h-6 text-primary-400" />
        <h1 className="text-2xl font-bold text-surface-50">Capture Sessions</h1>
        {!loading && (
          <span className="ml-auto text-sm text-surface-500">
            {sessions.length} session{sessions.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
        </div>
      )}

      {error && (
        <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-6 text-red-400 text-sm">
          {error}
        </div>
      )}

      {!loading && !error && sessions.length === 0 && (
        <div className="text-center py-24 text-surface-500">
          <Film className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg">No sessions yet</p>
          <p className="text-sm mt-1">Start a capture from the home page to see it here.</p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sessions.map((s) => {
          const imgSrc = thumb(s.first_thumbnail_url);
          const date = new Date(s.started_at).toLocaleString();
          const isDeleting = deletingId === s.id;
          const isConfirming = confirmId === s.id;
          return (
            <div key={s.id} className="relative group">
              <Link
                href={`/sessions/${s.id}`}
                className="block rounded-xl overflow-hidden border border-surface-800 bg-surface-900 hover:border-primary-500/50 transition-all duration-200 hover:-translate-y-0.5"
              >
                {/* Thumbnail */}
                <div className="relative aspect-video bg-surface-800 overflow-hidden">
                  {imgSrc ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={imgSrc}
                      alt={s.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-surface-600">
                      <Film className="w-10 h-10" />
                    </div>
                  )}
                  {s.status === "capturing" && (
                    <span className="absolute top-2 right-2 px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/80 text-white animate-pulse">
                      ● LIVE
                    </span>
                  )}
                </div>

                {/* Info */}
                <div className="p-4">
                  <div className="flex items-start justify-between gap-2">
                    <h2 className="font-semibold text-surface-100 truncate">{s.title}</h2>
                    <ChevronRight className="w-4 h-4 text-surface-600 group-hover:text-primary-400 flex-shrink-0 mt-0.5 transition-colors" />
                  </div>
                  <p className="text-xs text-surface-500 mt-1">{date}</p>

                  <div className="flex items-center gap-4 mt-3 text-xs text-surface-500">
                    <span className="flex items-center gap-1">
                      <LayoutGrid className="w-3.5 h-3.5" />
                      {s.scene_count} scene{s.scene_count !== 1 ? "s" : ""}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {formatDuration(s)}
                    </span>
                    <span className="flex items-center gap-1">{s.total_frames} frames</span>
                  </div>
                </div>
              </Link>

              {/* Delete controls — floated above the card link */}
              <div className="absolute top-2 left-2 z-10">
                {!isConfirming ? (
                  <button
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); setConfirmId(s.id); }}
                    className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-red-400 bg-black/70 border border-red-500/20 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 hover:border-red-500/40 transition-all"
                  >
                    <Trash2 className="w-3 h-3" />
                    Delete
                  </button>
                ) : (
                  <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-black/90 border border-red-500/30 shadow-lg">
                    <span className="text-xs text-red-400 whitespace-nowrap">Delete?</span>
                    <button
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleDelete(s.id); }}
                      disabled={isDeleting}
                      className="px-2 py-0.5 rounded text-xs font-medium bg-red-600 hover:bg-red-500 text-white disabled:opacity-50 transition-colors"
                    >
                      {isDeleting ? "…" : "Yes"}
                    </button>
                    <button
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); setConfirmId(null); }}
                      className="px-2 py-0.5 rounded text-xs text-surface-400 hover:text-white hover:bg-surface-700 transition-colors"
                    >
                      No
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
