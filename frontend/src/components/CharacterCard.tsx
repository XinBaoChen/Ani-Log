"use client";

import Link from "next/link";
import { useMemo, useState, useRef } from "react";
import { Users, Film, Sword, Pencil, Trash2, Check, X } from "lucide-react";
import type { SearchResult } from "@/types";

interface CharacterCardProps {
  data: SearchResult;
  onDelete?: () => void;
  onRename?: (newName: string) => void;
}

const typeConfig = {
  character: {
    icon: Users,
    badgeCls: "bg-primary-500/20 text-primary-300 border border-primary-500/25",
    href: (id: string) => `/characters/${id}`,
  },
  scene: {
    icon: Film,
    badgeCls: "bg-blue-500/20 text-blue-300 border border-blue-500/25",
    href: (id: string) => `/scenes`,
  },
  item: {
    icon: Sword,
    badgeCls: "bg-pink-500/20 text-pink-300 border border-pink-500/25",
    href: (id: string) => `/search`,
  },
};

function confColor(pct: number): string {
  if (pct >= 80) return "text-emerald-400";
  if (pct >= 60) return "text-amber-400";
  return "text-orange-400";
}

export default function CharacterCard({ data, onDelete, onRename }: CharacterCardProps) {
  const config = typeConfig[data.type as keyof typeof typeConfig] ?? typeConfig.character;
  const Icon = config.icon;
  const [imgFailed, setImgFailed] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(data.label);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const scorePct = useMemo(() => {
    if (typeof data.score !== "number") return null;
    if (data.score >= 1 || data.score <= 0) return null;
    return Math.round(data.score * 100);
  }, [data.score]);

  const introducedAt = useMemo(() => {
    const raw = data.metadata?.introduced_at;
    if (typeof raw !== "string") return null;
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }, [data.metadata]);

  const description = useMemo(() => {
    if (!data.description) return null;
    if (data.description.startsWith("Auto-detected")) return null;
    return data.description;
  }, [data.description]);

  const stop = (e: React.MouseEvent | React.FormEvent) => { e.preventDefault(); e.stopPropagation(); };

  const startEdit = (e: React.MouseEvent) => {
    stop(e);
    setEditName(data.label);
    setEditing(true);
    setTimeout(() => { inputRef.current?.focus(); inputRef.current?.select(); }, 30);
  };

  const submitRename = (e: React.FormEvent) => {
    stop(e);
    const trimmed = editName.trim();
    if (trimmed && trimmed !== data.label) onRename?.(trimmed);
    setEditing(false);
  };

  const hasControls = !!(onDelete || onRename);

  return (
    <div className="relative group">
      <Link href={config.href(data.id)}>
        <div className="overflow-hidden rounded-2xl aspect-[3/4] bg-surface-900 shadow-md hover:shadow-xl hover:ring-1 hover:ring-primary-500/30 transition-all duration-300 cursor-pointer">

          {/* Thumbnail */}
          <div className="absolute inset-0">
            {data.thumbnail_url && !imgFailed ? (
              <img
                src={data.thumbnail_url}
                alt={data.label}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                onError={() => setImgFailed(true)}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-surface-800 to-surface-900">
                <Icon className="w-12 h-12 text-surface-700" />
              </div>
            )}
          </div>

          {/* Gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/5 to-black/20" />

          {/* Type badge */}
          <div className="absolute top-2.5 right-2.5">
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-md backdrop-blur-sm ${config.badgeCls}`}>
              {data.type}
            </span>
          </div>

          {/* Bottom info strip */}
          <div className="absolute bottom-0 left-0 right-0 px-3 py-3">
            <div className="flex items-baseline justify-between gap-1.5">
              <p className="text-[13px] font-bold text-white truncate leading-tight flex-1">
                {data.label}
              </p>
              {scorePct !== null && (
                <span className={`text-[11px] font-mono font-semibold shrink-0 tabular-nums ${confColor(scorePct)}`}>
                  {scorePct}%
                </span>
              )}
            </div>
            {description && (
              <p className="text-[11px] text-white/55 line-clamp-2 mt-0.5 leading-snug">{description}</p>
            )}
            {introducedAt && (
              <p className="text-[10px] text-white/35 mt-1 font-medium">{introducedAt}</p>
            )}
          </div>
        </div>
      </Link>

      {/* Hover controls — outside <Link> so they don't navigate */}
      {hasControls && !editing && !confirmDelete && (
        <div className="absolute top-2 left-2 z-10 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
          {onRename && (
            <button
              onClick={startEdit}
              className="w-6 h-6 rounded-md bg-black/60 backdrop-blur-sm flex items-center justify-center text-white/70 hover:text-white hover:bg-black/80 transition-colors"
              title="Rename"
            >
              <Pencil className="w-3 h-3" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={(e) => { stop(e); setConfirmDelete(true); }}
              className="w-6 h-6 rounded-md bg-black/60 backdrop-blur-sm flex items-center justify-center text-white/70 hover:text-red-400 hover:bg-black/80 transition-colors"
              title="Delete"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
        </div>
      )}

      {/* Inline rename input — appears at the bottom of the card */}
      {editing && (
        <div
          className="absolute bottom-0 left-0 right-0 z-10 px-2 py-2 bg-black/85 backdrop-blur-sm rounded-b-2xl border-t border-white/10"
          onClick={stop}
        >
          <form onSubmit={submitRename} className="flex items-center gap-1.5">
            <input
              ref={inputRef}
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="flex-1 text-[12px] bg-white/10 text-white px-2 py-1 rounded-md outline-none focus:ring-1 focus:ring-primary-500 border border-white/20 min-w-0"
              onKeyDown={(e) => { if (e.key === "Escape") { e.stopPropagation(); setEditing(false); } }}
            />
            <button type="submit" className="w-6 h-6 rounded-md bg-primary-500/80 flex items-center justify-center text-white hover:bg-primary-500 transition-colors">
              <Check className="w-3 h-3" />
            </button>
            <button type="button" onClick={(e) => { stop(e); setEditing(false); }} className="w-6 h-6 rounded-md bg-white/10 flex items-center justify-center text-white/60 hover:text-white hover:bg-white/20 transition-colors">
              <X className="w-3 h-3" />
            </button>
          </form>
        </div>
      )}

      {/* Delete confirmation overlay */}
      {confirmDelete && (
        <div
          className="absolute inset-0 z-20 bg-black/85 backdrop-blur-sm rounded-2xl flex flex-col items-center justify-center gap-3 p-4"
          onClick={stop}
        >
          <Trash2 className="w-7 h-7 text-red-400" />
          <p className="text-xs text-white text-center font-medium leading-snug">
            Delete <span className="font-bold">{data.label}</span>?<br />
            <span className="text-white/40 text-[10px]">This cannot be undone.</span>
          </p>
          <div className="flex gap-2">
            <button
              onClick={(e) => { stop(e); onDelete?.(); }}
              className="px-3 py-1.5 text-[11px] font-semibold bg-red-500/80 hover:bg-red-500 text-white rounded-lg transition-colors"
            >
              Delete
            </button>
            <button
              onClick={(e) => { stop(e); setConfirmDelete(false); }}
              className="px-3 py-1.5 text-[11px] font-semibold bg-white/10 hover:bg-white/20 text-white/70 rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
