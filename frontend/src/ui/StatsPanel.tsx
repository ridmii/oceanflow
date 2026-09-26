// src/ui/StatsPanel.tsx
// Top-left collapsible stats panel.
// FPS is read from fpsStore (written by FpsSampler inside the R3F Canvas).
// StatsPanel itself is outside the Canvas, so it subscribes to the store.

import { memo, useEffect, useRef, useState, useCallback } from 'react';
import { useFrame } from '@react-three/fiber';
import { usePlaybackStore } from '../store/playbackStore';
import { useParticleData } from '../hooks/useParticleData';
import { useFilterStore } from '../store/filterStore';
import { useFpsStore } from '../store/fpsStore';

// ─── FPS Sampler (must live inside Canvas) ────────────────────────────────────
export function FpsSampler() {
  const samples = useRef<number[]>([]);
  const setFps  = useFpsStore((s) => s.setFps);

  useFrame((_state, dt) => {
    if (dt <= 0) return;
    samples.current.push(1 / dt);
    if (samples.current.length > 60) samples.current.shift();
  });

  useEffect(() => {
    const id = setInterval(() => {
      const arr = samples.current;
      if (arr.length === 0) return;
      const avg = arr.reduce((a, b) => a + b, 0) / arr.length;
      setFps(Math.round(avg));
    }, 250);
    return () => clearInterval(id);
  }, [setFps]);

  return null;
}

// ─── Stats Panel (outside Canvas) ────────────────────────────────────────────
const StatsPanel = memo(function StatsPanel() {
  const [collapsed, setCollapsed] = useState(false);
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;

  const fps          = useFpsStore((s) => s.fps);
  const error        = usePlaybackStore((s) => s.error);
  const currentFrame = usePlaybackStore((s) => s.currentFrame);
  const frameCount   = usePlaybackStore((s) => s.frameCount);
  const seekToFrame  = usePlaybackStore((s) => s.seekToFrame);
  const { meta, source, loading } = useParticleData();
  const toggleHeatmap = useFilterStore((s) => s.toggleHeatmap);
  const showHeatmap   = useFilterStore((s) => s.showHeatmap);
  const toggleTrails  = useFilterStore((s) => s.toggleTrails);
  const showTrails    = useFilterStore((s) => s.showTrails);
  const blendingMode  = useFilterStore((s) => s.blendingMode);
  const setBlending   = useFilterStore((s) => s.setBlendingMode);

  const resetView = useCallback(() => seekToFrame(0), [seekToFrame]);
  const fpsColor  = fps >= 50 ? 'text-emerald-400' : fps >= 30 ? 'text-yellow-400' : 'text-red-400';

  if (collapsed || (isMobile && collapsed)) {
    return (
      <button
        id="btn-stats-expand"
        onClick={() => setCollapsed(false)}
        aria-label="Expand stats panel"
        className="glass-panel p-2 text-white/60 hover:text-white text-xs"
      >
        ◉ Stats
      </button>
    );
  }

  return (
    <div
      id="stats-panel"
      className="glass-panel p-4 min-w-[200px] text-xs text-white/80 flex flex-col gap-2"
      role="region"
      aria-label="Statistics"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="font-semibold text-white/90 text-sm">Stats</span>
        <button
          id="btn-stats-collapse"
          onClick={() => setCollapsed(true)}
          aria-label="Collapse stats panel"
          className="text-white/40 hover:text-white/80 text-base leading-none"
        >
          ×
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div
          className="bg-red-900/50 border border-red-500/40 rounded px-2 py-1.5
                     text-red-300 text-[11px] break-all"
          role="alert"
        >
          ⚠ {error}
        </div>
      )}

      {/* Source */}
      <div className="flex justify-between gap-2">
        <span className="text-white/50">Source</span>
        <span className="tabular font-medium truncate max-w-[120px]" title={source.name}>
          {source.name}
        </span>
      </div>

      {/* Status */}
      {loading && (
        <div className="text-white/40 text-[11px] animate-pulse">Loading metadata…</div>
      )}

      {/* Particle count */}
      <div className="flex justify-between">
        <span className="text-white/50">Particles</span>
        <span className="tabular">{meta?.particleCount.toLocaleString() ?? '—'}</span>
      </div>

      {/* Frame */}
      <div className="flex justify-between">
        <span className="text-white/50">Frame</span>
        <span className="tabular">{currentFrame} / {frameCount - 1}</span>
      </div>

      {/* FPS */}
      <div className="flex justify-between">
        <span className="text-white/50">FPS</span>
        <span className={`tabular font-semibold ${fpsColor}`}>{fps}</span>
      </div>

      <hr className="border-white/10" />

      {/* Toggles */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showHeatmap}
          onChange={toggleHeatmap}
          id="toggle-heatmap"
        />
        <span>Density heatmap</span>
      </label>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showTrails}
          onChange={toggleTrails}
          id="toggle-trails"
        />
        <span>Motion trails*</span>
      </label>

      {/* Blending mode */}
      <div className="flex items-center gap-2">
        <span className="text-white/50">Blend</span>
        <select
          id="select-blending"
          value={blendingMode}
          onChange={(e) => setBlending(e.target.value as 'additive' | 'normal')}
          className="flex-1 bg-white/10 border border-white/10 rounded px-1 py-0.5 text-xs"
        >
          <option value="additive">Additive</option>
          <option value="normal">Normal</option>
        </select>
      </div>

      <hr className="border-white/10" />

      {/* Reset */}
      <button
        id="btn-reset-view"
        onClick={resetView}
        className="text-[#6ec6e8] hover:text-white transition-colors text-left text-[11px]"
      >
        ↺ Reset to frame 0
      </button>

      <p className="text-white/25 text-[10px] leading-tight">
        * Trails are screen-space; no occlusion.
      </p>
    </div>
  );
});

export default StatsPanel;
