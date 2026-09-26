// src/store/fpsStore.ts
// Simple store for FPS — allows FpsSampler (inside Canvas) to push values
// to StatsPanel (outside Canvas) without prop-drilling or context crossing.

import { create } from 'zustand';

interface FpsState {
  fps: number;
  setFps: (fps: number) => void;
}

export const useFpsStore = create<FpsState>((set) => ({
  fps: 0,
  setFps: (fps) => set({ fps }),
}));
