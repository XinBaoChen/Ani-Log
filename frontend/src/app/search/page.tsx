"use client";

import { useEffect, useState, Suspense } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Search, SlidersHorizontal, Sparkles } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import CharacterCard from "@/components/CharacterCard";
import { useSearchStore } from "@/store/useSearchStore";
import type { SearchMode } from "@/types";

function SearchContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = (searchParams.get("q") || "").trim();
  const { results, isSearching, search, error } = useSearchStore();

  const [category, setCategory] = useState<"all" | "characters" | "scenes" | "items">(
    (searchParams.get("category") as "all" | "characters" | "scenes" | "items") || "all"
  );
  const [mode, setMode] = useState<SearchMode>((searchParams.get("mode") as SearchMode) || "hybrid");
  const [minScore, setMinScore] = useState<number>(Number(searchParams.get("min_score") || "0"));

  useEffect(() => {
    const pCategory = (searchParams.get("category") as "all" | "characters" | "scenes" | "items") || "all";
    const pMode = (searchParams.get("mode") as SearchMode) || "hybrid";
    const pMinScore = Number(searchParams.get("min_score") || "0");
    setCategory(pCategory);
    setMode(pMode);
    setMinScore(Number.isFinite(pMinScore) ? pMinScore : 0);
  }, [searchParams]);

  useEffect(() => {
    if (query) {
      search(query, {
        category,
        mode,
        minScore,
        limit: 50,
      });
    }
  }, [query, category, mode, minScore, search]);

  const updateFilterInUrl = (next: {
    category?: "all" | "characters" | "scenes" | "items";
    mode?: SearchMode;
    minScore?: number;
  }) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next.category) params.set("category", next.category);
    if (next.mode) params.set("mode", next.mode);
    if (typeof next.minScore === "number") params.set("min_score", String(next.minScore));
    router.replace(`${pathname}?${params.toString()}`);
  };

  const categories = [
    { key: "all", label: "All" },
    { key: "characters", label: "Characters" },
    { key: "scenes", label: "Scenes" },
    { key: "items", label: "Items" },
  ];

  const modes: Array<{ key: SearchMode; label: string; hint: string }> = [
    { key: "hybrid", label: "Hybrid", hint: "Best of keyword + semantic" },
    { key: "semantic", label: "Semantic", hint: "Concept meaning first" },
    { key: "keyword", label: "Keyword", hint: "Exact wording first" },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Search Header */}
      <div className="mb-8">
        <SearchBar initialQuery={query} />
      </div>

      {/* Filters */}
      <div className="space-y-3 mb-6">
        <div className="flex items-center gap-2 flex-wrap">
          <SlidersHorizontal className="w-4 h-4 text-surface-500" />
          {categories.map((cat) => (
            <button
              key={cat.key}
              onClick={() => {
                setCategory(cat.key as "all" | "characters" | "scenes" | "items");
                updateFilterInUrl({ category: cat.key as "all" | "characters" | "scenes" | "items" });
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                category === cat.key
                  ? "bg-primary-600 text-white"
                  : "bg-surface-800 text-surface-400 hover:bg-surface-700"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {modes.map((m) => (
            <button
              key={m.key}
              onClick={() => {
                setMode(m.key);
                updateFilterInUrl({ mode: m.key });
              }}
              className={`text-left p-2 rounded-lg border transition-all ${
                mode === m.key
                  ? "border-accent-cyan bg-accent-cyan/10"
                  : "border-surface-700 bg-surface-900/60 hover:bg-surface-800"
              }`}
            >
              <p className="text-xs font-semibold text-surface-200">{m.label}</p>
              <p className="text-[11px] text-surface-500">{m.hint}</p>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Sparkles className="w-4 h-4 text-accent-cyan" />
          <label htmlFor="min-score" className="text-xs text-surface-500 whitespace-nowrap">Min score</label>
          <input
            id="min-score"
            type="range"
            min={0}
            max={0.95}
            step={0.05}
            value={minScore}
            onChange={(e) => {
              const v = Number(e.target.value);
              setMinScore(v);
              updateFilterInUrl({ minScore: v });
            }}
            className="w-36 accent-primary-500"
          />
          <span className="text-xs font-mono text-surface-400 w-10">{Math.round(minScore * 100)}%</span>
        </div>
      </div>

      {/* Results */}
      {isSearching ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <div className="text-center py-20">
          <p className="text-red-400">{error}</p>
        </div>
      ) : results.length > 0 ? (
        <>
          <p className="text-sm text-surface-500 mb-4">
            {results.length} results for &quot;{query}&quot; using <span className="text-surface-300">{mode}</span>
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {results.map((result, i) => (
              <motion.div
                key={result.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <CharacterCard data={result} />
              </motion.div>
            ))}
          </div>
        </>
      ) : query ? (
        <div className="text-center py-20">
          <Search className="w-12 h-12 text-surface-700 mx-auto mb-4" />
          <p className="text-surface-400">No results found for &quot;{query}&quot;</p>
          <p className="text-sm text-surface-600 mt-1">
            Try a different description or broaden your search
          </p>
        </div>
      ) : null}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <SearchContent />
    </Suspense>
  );
}
