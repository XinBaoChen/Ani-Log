/* ─── TypeScript types for Ani-Log ─────────────────────────── */

// ─── Search ─────────────────────────────────────────────────
export interface SearchResult {
  id: string;
  type: "character" | "scene" | "item";
  label: string;
  description?: string;
  thumbnail_url?: string;
  score: number;
  metadata?: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchResult[];
}

// ─── Character ──────────────────────────────────────────────
export interface Character {
  id: string;
  name: string;
  description: string | null;
  appearance_count: number;
  first_seen_at: string;
  thumbnail_url: string | null;
  metadata?: Record<string, unknown>;
}

export interface Appearance {
  id: string;
  scene_id: string;
  timestamp: number;
  confidence: number;
  bbox: number[] | null;
}

export interface CharacterDetail extends Character {
  appearances: Appearance[];
  related_characters: Character[];
}

// ─── Scene ──────────────────────────────────────────────────
export interface Scene {
  id: string;
  session_id: string;
  scene_index: number;
  start_time: number;
  end_time: number | null;
  thumbnail_url: string | null;
  description: string | null;
  location: string | null;
  characters: Character[];
  items: Item[];
}

// ─── Item ───────────────────────────────────────────────────
export interface Item {
  id: string;
  label: string;
  category: string;
  confidence: number;
  timestamp: number;
  bbox: number[] | null;
}

// ─── Capture ────────────────────────────────────────────────
export interface CaptureStartRequest {
  title: string;
  fps: number;
  source: string;
}

export interface CaptureStartResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface CaptureStatus {
  session_id: string;
  status: string;
  total_frames: number;
  characters_found: number;
  scenes_detected: number;
  elapsed_seconds: number;
}

// ─── Story Arc ──────────────────────────────────────────────
export interface StoryArc {
  id: string;
  title: string;
  summary: string;
  character_ids: string[] | null;
  scene_ids: string[] | null;
  generated_at: string;
}

export interface SummaryGenerateRequest {
  session_id: string;
  detail_level: "brief" | "medium" | "detailed";
}

// ─── Session ────────────────────────────────────────────────
export interface Session {
  id: string;
  title: string;
  started_at: string;
  ended_at: string | null;
  total_frames: number;
  status: string;
  scene_count: number;
  first_thumbnail_url: string | null;
}
