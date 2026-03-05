"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Users, RefreshCw } from "lucide-react";
import CharacterCard from "@/components/CharacterCard";
import { api } from "@/lib/api";
import type { Character } from "@/types";

export default function CharactersPage() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState("appearance_count");

  const fetchCharacters = async () => {
    setLoading(true);
    try {
      const data = await api.getCharacters({ sort_by: sortBy });
      setCharacters(data);
    } catch (err) {
      console.error("Failed to fetch characters:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCharacters();
  }, [sortBy]);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Users className="w-6 h-6 text-primary-400" />
          <h1 className="text-2xl font-bold">Characters</h1>
          <span className="badge-purple">{characters.length}</span>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-1.5 bg-surface-800 border border-surface-700 rounded-lg
                       text-sm text-surface-300 focus:outline-none focus:border-primary-500"
          >
            <option value="appearance_count">Most Seen</option>
            <option value="first_seen_at">Recently Found</option>
            <option value="name">Name (A-Z)</option>
          </select>

          <button onClick={fetchCharacters} className="btn-ghost p-2">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {Array.from({ length: 10 }).map((_, i) => (
            <div
              key={i}
              className="aspect-[3/4] rounded-2xl bg-surface-800 animate-pulse"
            />
          ))}
        </div>
      ) : characters.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {characters.map((char, i) => (
            <motion.div
              key={char.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.02 }}
            >
              <CharacterCard
                data={{
                  id: char.id,
                  type: "character",
                  label: char.name,
                  description: char.description || undefined,
                  thumbnail_url: char.thumbnail_url || undefined,
                  score: 1,
                }}
              />
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <Users className="w-12 h-12 text-surface-700 mx-auto mb-4" />
          <p className="text-surface-400">No characters detected yet</p>
          <p className="text-sm text-surface-600 mt-1">
            Start a capture session to begin discovering characters
          </p>
        </div>
      )}
    </div>
  );
}
