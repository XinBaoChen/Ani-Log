"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, X, Loader2 } from "lucide-react";
import { useSearchStore } from "@/store/useSearchStore";

interface SearchBarProps {
  initialQuery?: string;
}

export default function SearchBar({ initialQuery = "" }: SearchBarProps) {
  const [query, setQuery] = useState(initialQuery);
  const router = useRouter();
  const { search, isSearching } = useSearchStore();

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!query.trim()) return;

      search(query.trim());
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    },
    [query, search, router]
  );

  return (
    <form onSubmit={handleSearch} className="relative">
      <div className="relative group">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500 group-focus-within:text-primary-400 transition-colors" />

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Search by description — "blue-haired girl with sword"'
          className="w-full pl-12 pr-12 py-4 bg-surface-900/80 border border-surface-700
                     rounded-2xl text-surface-100 placeholder-surface-500
                     focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20
                     transition-all text-base backdrop-blur-sm"
        />

        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="absolute right-14 top-1/2 -translate-y-1/2 p-1 rounded-md
                       text-surface-500 hover:text-surface-300 hover:bg-surface-800 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        <button
          type="submit"
          disabled={isSearching || !query.trim()}
          className="absolute right-3 top-1/2 -translate-y-1/2 px-3 py-1.5 rounded-xl
                     bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium
                     disabled:opacity-40 disabled:cursor-not-allowed
                     transition-all shadow-lg shadow-primary-600/20"
        >
          {isSearching ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            "Search"
          )}
        </button>
      </div>
    </form>
  );
}
