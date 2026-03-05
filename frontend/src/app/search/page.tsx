"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Search, SlidersHorizontal } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import CharacterCard from "@/components/CharacterCard";
import { useSearchStore } from "@/store/useSearchStore";

function SearchContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const { results, isSearching, search } = useSearchStore();
  const [category, setCategory] = useState("all");

  useEffect(() => {
    if (query) {
      search(query, category);
    }
  }, [query, category, search]);

  const categories = [
    { key: "all", label: "All" },
    { key: "characters", label: "Characters" },
    { key: "scenes", label: "Scenes" },
    { key: "items", label: "Items" },
  ];

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Search Header */}
      <div className="mb-8">
        <SearchBar initialQuery={query} />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-6">
        <SlidersHorizontal className="w-4 h-4 text-surface-500" />
        {categories.map((cat) => (
          <button
            key={cat.key}
            onClick={() => setCategory(cat.key)}
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

      {/* Results */}
      {isSearching ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : results.length > 0 ? (
        <>
          <p className="text-sm text-surface-500 mb-4">
            {results.length} results for &quot;{query}&quot;
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
