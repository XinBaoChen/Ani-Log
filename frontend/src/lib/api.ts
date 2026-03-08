/**
 * API client for the Ani-Log backend.
 */

import type {
  SearchResponse,
  Character,
  CharacterDetail,
  Scene,
  Session,
  CaptureStartRequest,
  CaptureStartResponse,
  CaptureStatus,
  StoryArc,
  SummaryGenerateRequest,
} from "@/types";

// Empty string = use relative paths routed through Next.js rewrite proxy (/api/* → localhost:8000)
// Set NEXT_PUBLIC_API_URL in .env.local only if your backend is on a different host
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error ${res.status}: ${error}`);
  }

  return res.json();
}

export const api = {
  // ─── Search ─────────────────────────────────────────────
  search: (query: string, category = "all", limit = 20) =>
    request<SearchResponse>(
      `/api/search?q=${encodeURIComponent(query)}&category=${category}&limit=${limit}`
    ),

  // ─── Characters ─────────────────────────────────────────
  getCharacters: (params?: { sort_by?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.sort_by) query.set("sort_by", params.sort_by);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    return request<Character[]>(`/api/characters?${query}`);
  },

  getCharacter: (id: string) =>
    request<CharacterDetail>(`/api/characters/${id}`),

  updateCharacter: (id: string, data: { name?: string; description?: string }) =>
    request<Character>(`/api/characters/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  // ─── Scenes ─────────────────────────────────────────────
  getScenes: (sessionId?: string) => {
    const query = sessionId ? `?session_id=${sessionId}` : "";
    return request<Scene[]>(`/api/scenes${query}`);
  },

  getScene: (id: string) => request<Scene>(`/api/scenes/${id}`),

  // ─── Sessions ───────────────────────────────────────────
  getSessions: () => request<Session[]>("/api/sessions/"),

  getSession: (id: string) => request<Session>(`/api/sessions/${id}`),

  getSessionScenes: (id: string) => request<Scene[]>(`/api/sessions/${id}/scenes`),

  deleteSession: (id: string) =>
    request<void>(`/api/sessions/${id}`, { method: "DELETE" }),

  // ─── Capture ────────────────────────────────────────────
  startCapture: (data: CaptureStartRequest) =>
    request<CaptureStartResponse>("/api/capture/start", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  stopCapture: () =>
    request<{ status: string; message: string }>("/api/capture/stop", {
      method: "POST",
    }),

  getCaptureStatus: () => request<CaptureStatus>("/api/capture/status"),

  // ─── Summary ────────────────────────────────────────────
  generateSummary: (data: SummaryGenerateRequest) =>
    request<StoryArc>("/api/summary/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getStoryArcs: (sessionId?: string) => {
    const query = sessionId ? `?session_id=${sessionId}` : "";
    return request<StoryArc[]>(`/api/summary${query}`);
  },

  getStoryArc: (id: string) => request<StoryArc>(`/api/summary/${id}`),
};
