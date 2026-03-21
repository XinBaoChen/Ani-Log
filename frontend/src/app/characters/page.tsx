"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Users, RefreshCw } from "lucide-react";
import CharacterCard from "@/components/CharacterCard";
import { api } from "@/lib/api";
import type { Character } from "@/types";

export default function CharactersPage() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState("appearance_count");
  const [minConfidence, setMinConfidence] = useState(0.5);

  const getConfidence = (char: Character): number | undefined => {
    if (typeof char.confidence === "number") return char.confidence;
    const meta = char.metadata as Record<string, unknown> | undefined;
    const metaConfidence = meta?.confidence;
    if (typeof metaConfidence === "number") return metaConfidence;
    return undefined;
  };

  const filteredCharacters = characters.filter((char) => {
    const conf = getConfidence(char);
    if (typeof conf !== "number") return true;
    return conf >= minConfidence;
  });

  const fetchCharacters = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getCharacters({ sort_by: sortBy });
      setCharacters(data);
    } catch (err) {
      console.error("Failed to fetch characters:", err);
    } finally {
      setLoading(false);
    }
  }, [sortBy]);

  const handleRename = async (id: string, newName: string) => {
    // Optimistic update so the card reflects the new name immediately
    setCharacters((prev) => prev.map((c) => c.id === id ? { ...c, name: newName } : c));
    try {
      await api.updateCharacter(id, { name: newName });
    } catch (err) {
      console.error("Failed to rename character:", err);
      fetchCharacters(); // revert on failure
    }
  };

  const handleDelete = async (id: string) => {
    setCharacters((prev) => prev.filter((c) => c.id !== id));
    try {
      await api.deleteCharacter(id);
    } catch (err) {
      console.error("Failed to delete character:", err);
      fetchCharacters(); // revert on failure
    }
  };

  useEffect(() => {
    fetchCharacters();
  }, [fetchCharacters]);

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
            <option value="confidence">Highest Confidence</option>
            <option value="name">Name (A-Z)</option>
          </select>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-surface-700 bg-surface-900">
            <label htmlFor="confidence-filter" className="text-xs text-surface-400 whitespace-nowrap">
              Min confidence
            </label>
            <input
              id="confidence-filter"
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
      ) : filteredCharacters.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {filteredCharacters.map((char, i) => (
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
                  score: getConfidence(char) ?? 1,
                  metadata: {
                    introduced_at: char.first_seen_at,
                  },
                }}
                onRename={(newName) => handleRename(char.id, newName)}
                onDelete={() => handleDelete(char.id)}
              />
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <Users className="w-12 h-12 text-surface-700 mx-auto mb-4" />
          <p className="text-surface-400">
            {characters.length > 0 ? "No characters match this confidence filter" : "No characters detected yet"}
          </p>
          <p className="text-sm text-surface-600 mt-1">
            {characters.length > 0
              ? "Lower the minimum confidence threshold to include weaker detections."
              : "Start a capture session to begin discovering characters."}
          </p>
        </div>
      )}
    </div>
  );
}
