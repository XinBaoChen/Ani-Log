import { create } from "zustand";

type CaptureStatus = "idle" | "starting" | "capturing" | "stopping";

interface CaptureStats {
  totalFrames: number;
  charactersFound: number;
  scenesDetected: number;
  elapsed: number;
}

interface CaptureState {
  status: CaptureStatus;
  sessionId: string | null;
  stats: CaptureStats;
  setStatus: (status: CaptureStatus) => void;
  setSessionId: (id: string | null) => void;
  setStats: (stats: CaptureStats) => void;
}

export const useCaptureStore = create<CaptureState>((set) => ({
  status: "idle",
  sessionId: null,
  stats: {
    totalFrames: 0,
    charactersFound: 0,
    scenesDetected: 0,
    elapsed: 0,
  },

  setStatus: (status) => set({ status }),
  setSessionId: (sessionId) => set({ sessionId }),
  setStats: (stats) => set({ stats }),
}));
