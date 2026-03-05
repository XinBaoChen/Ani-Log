import { create } from "zustand";
import { api } from "@/lib/api";
import type { SearchResult } from "@/types";

interface SearchState {
  query: string;
  results: SearchResult[];
  isSearching: boolean;
  error: string | null;
  search: (query: string, category?: string) => Promise<void>;
  clearResults: () => void;
}

export const useSearchStore = create<SearchState>((set) => ({
  query: "",
  results: [],
  isSearching: false,
  error: null,

  search: async (query: string, category = "all") => {
    set({ isSearching: true, query, error: null });

    try {
      const response = await api.search(query, category);
      set({ results: response.results, isSearching: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Search failed",
        isSearching: false,
      });
    }
  },

  clearResults: () => set({ results: [], query: "" }),
}));
