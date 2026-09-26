// src/hooks/usePlayback.ts
// Keyboard shortcut binding for playback. Wired at the app root.

import { useEffect } from 'react';
import { usePlaybackStore } from '../store/playbackStore';

export function usePlaybackKeyboard(): void {
  const setPlaying = usePlaybackStore((s) => s.setPlaying);
  const isPlaying  = usePlaybackStore((s) => s.isPlaying);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ignore when typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === ' ') {
        e.preventDefault();
        setPlaying(!isPlaying);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isPlaying, setPlaying]);
}

/** Returns whether prefers-reduced-motion is active. */
export function usePrefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}
