// src/store/playbackStore.ts
// Zustand store for animation playback state.
// useFrame reads currentFrame from here, never from React state.

import { create } from 'zustand';

export interface PlaybackState {
  isPlaying: boolean;
  speed: number;           // 0.5 | 1 | 2 | 4
  currentFrame: number;
  frameCount: number;
  /** Accumulated sub-frame progress [0, 1) for inter-frame interpolation */
  frameProgress: number;
  error: string | null;

  // Actions
  setPlaying: (playing: boolean) => void;
  setSpeed: (speed: number) => void;
  seekToFrame: (frame: number) => void;
  setFrameCount: (count: number) => void;
  setError: (error: string | null) => void;
  /** Called by useFrame each tick with elapsed seconds */
  tick: (dt: number) => void;
}

export const usePlaybackStore = create<PlaybackState>((set) => ({
  isPlaying: false,
  speed: 1,
  currentFrame: 0,
  frameCount: 240,
  frameProgress: 0,
  error: null,

  setPlaying: (playing) => set({ isPlaying: playing }),
  setSpeed: (speed) => set({ speed }),
  seekToFrame: (frame) => set({ currentFrame: frame, frameProgress: 0 }),
  setFrameCount: (count) => set({ frameCount: count }),
  setError: (error) => set({ error }),

  tick: (dt) =>
    set((state) => {
      if (!state.isPlaying || state.frameCount === 0) return {};

      // How many simulated hours pass per real second at current speed?
      // Each frame = timeStepHours simulated hours.
      // At speed 1x, one frame per second is a sensible base rate.
      const framesPerSecond = state.speed;
      const newProgress = state.frameProgress + framesPerSecond * dt;
      const frameDelta = Math.floor(newProgress);
      const nextProgress = newProgress - frameDelta;
      const nextFrame = (state.currentFrame + frameDelta) % state.frameCount;

      return {
        currentFrame: nextFrame,
        frameProgress: nextProgress,
      };
    }),
}));
