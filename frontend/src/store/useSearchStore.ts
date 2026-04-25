import { create } from "zustand";
import { api } from "@/lib/api";
import type { SearchResult, SearchOptions, SearchMode } from "@/types";

interface SearchState {
  query: string;
  results: SearchResult[];
  mode: SearchMode;
  category: "all" | "characters" | "scenes" | "items";
  minScore: number;
  isSearching: boolean;
  error: string | null;
  search: (query: string, options?: SearchOptions) => Promise<void>;
  clearResults: () => void;
}

export const useSearchStore = create<SearchState>((set) => ({
  query: "",
  results: [],
  mode: "hybrid",
  category: "all",
  minScore: 0,
  isSearching: false,
  error: null,

  search: async (query: string, options?: SearchOptions) => {
    const category = options?.category ?? "all";
    const mode = options?.mode ?? "hybrid";
    const minScore = options?.minScore ?? 0;
    set({ isSearching: true, query, error: null });

    try {
      const response = await api.search(query, {
        category,
        mode,
        minScore,
        limit: options?.limit ?? 40,
      });
      set({
        results: response.results,
        isSearching: false,
        mode,
        category,
        minScore,
      });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Search failed",
        isSearching: false,
      });
    }
  },

  clearResults: () => set({ results: [], query: "", minScore: 0 }),
}));
