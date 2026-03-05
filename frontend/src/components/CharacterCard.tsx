"use client";

import Link from "next/link";
import { Users, Film, Sword, MapPin } from "lucide-react";
import type { SearchResult } from "@/types";

interface CharacterCardProps {
  data: SearchResult;
}

const typeConfig = {
  character: {
    icon: Users,
    badge: "badge-purple",
    href: (id: string) => `/characters/${id}`,
  },
  scene: {
    icon: Film,
    badge: "badge-blue",
    href: (id: string) => `/scenes`,
  },
  item: {
    icon: Sword,
    badge: "badge-pink",
    href: (id: string) => `/search`,
  },
};

export default function CharacterCard({ data }: CharacterCardProps) {
  const config = typeConfig[data.type as keyof typeof typeConfig] || typeConfig.character;
  const Icon = config.icon;

  return (
    <Link href={config.href(data.id)}>
      <div className="card group relative overflow-hidden aspect-[3/4]">
        {/* Thumbnail */}
        <div className="absolute inset-0">
          {data.thumbnail_url ? (
            <img
              src={data.thumbnail_url}
              alt={data.label}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-surface-800 to-surface-900">
              <Icon className="w-10 h-10 text-surface-700" />
            </div>
          )}
        </div>

        {/* Gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

        {/* Type badge */}
        <div className="absolute top-2 right-2">
          <span className={config.badge}>{data.type}</span>
        </div>

        {/* Score indicator */}
        {data.score < 1 && (
          <div className="absolute top-2 left-2">
            <span className="text-[10px] font-mono text-surface-400 bg-black/50 px-1.5 py-0.5 rounded">
              {(data.score * 100).toFixed(0)}%
            </span>
          </div>
        )}

        {/* Info */}
        <div className="absolute bottom-0 left-0 right-0 p-3">
          <p className="text-sm font-semibold text-white truncate">
            {data.label}
          </p>
          {data.description && (
            <p className="text-[11px] text-white/60 line-clamp-2 mt-0.5 leading-snug">
              {data.description}
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}
