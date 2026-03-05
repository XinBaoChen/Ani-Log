"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Clock, Eye, Users, Sparkles } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import SceneTimeline from "@/components/SceneTimeline";
import type { CharacterDetail } from "@/types";

export default function CharacterDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [character, setCharacter] = useState<CharacterDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await api.getCharacter(id);
        setCharacter(data);
      } catch (err) {
        console.error("Failed to fetch character:", err);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="h-64 rounded-2xl bg-surface-800 animate-pulse" />
      </div>
    );
  }

  if (!character) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <p className="text-surface-400">Character not found</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Back */}
      <Link
        href="/characters"
        className="inline-flex items-center gap-1.5 text-sm text-surface-400 hover:text-surface-200 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        All Characters
      </Link>

      {/* Character Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-6 mb-6"
      >
        <div className="flex gap-6">
          {/* Thumbnail */}
          <div className="w-32 h-40 rounded-xl bg-surface-800 overflow-hidden flex-shrink-0">
            {character.thumbnail_url ? (
              <img
                src={character.thumbnail_url}
                alt={character.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <Users className="w-10 h-10 text-surface-600" />
              </div>
            )}
          </div>

          {/* Info */}
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-surface-100 mb-2">
              {character.name}
            </h1>

            {character.description && (
              <p className="text-sm text-surface-400 mb-4 leading-relaxed">
                {character.description}
              </p>
            )}

            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1.5 text-surface-400">
                <Eye className="w-4 h-4" />
                <span>
                  {character.appearance_count} appearance
                  {character.appearance_count !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-surface-400">
                <Clock className="w-4 h-4" />
                <span>
                  First seen{" "}
                  {new Date(character.first_seen_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Appearances Timeline */}
      {character.appearances && character.appearances.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-panel p-6 mb-6"
        >
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-primary-400" />
            Appearances
          </h2>
          <SceneTimeline appearances={character.appearances} />
        </motion.div>
      )}

      {/* Related Characters */}
      {character.related_characters && character.related_characters.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-panel p-6"
        >
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-accent-pink" />
            Often Seen With
          </h2>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
            {character.related_characters.map((related) => (
              <Link
                key={related.id}
                href={`/characters/${related.id}`}
                className="card text-center p-3"
              >
                <div className="w-12 h-12 rounded-full bg-surface-700 mx-auto mb-2 overflow-hidden">
                  {related.thumbnail_url ? (
                    <img
                      src={related.thumbnail_url}
                      alt={related.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Users className="w-5 h-5 text-surface-500" />
                    </div>
                  )}
                </div>
                <p className="text-xs font-medium text-surface-300 truncate">
                  {related.name}
                </p>
              </Link>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
