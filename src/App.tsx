// src/App.tsx
// Root component. Sets up data source context and composes UI layers.

import { useMemo } from 'react';
import Scene from './scene/Scene';
import ControlBar from './ui/ControlBar';
import StatsPanel from './ui/StatsPanel';
import SourceFilter from './ui/SourceFilter';
import Legend from './ui/Legend';
import { ParticleDataContext, useParticleDataSource } from './hooks/useParticleData';
import { createDataSource } from './data/sourceConfig';
import { usePlaybackKeyboard } from './hooks/usePlayback';

// ─── Provider wrapper ─────────────────────────────────────────────────────────
function AppDataProvider({ children }: { children: React.ReactNode }) {
  const source = useMemo(() => createDataSource(), []);
  const { meta, loading, error } = useParticleDataSource(source);

  return (
    <ParticleDataContext.Provider value={{ source, meta, loading, error }}>
      {children}
    </ParticleDataContext.Provider>
  );
}

// ─── App inner ────────────────────────────────────────────────────────────────
function AppInner() {
  usePlaybackKeyboard();

  return (
    <div className="relative w-full h-full" id="app-root">
      {/* 3D Canvas layer */}
      <Scene />

      {/* UI overlay layer – pointer-events-none on container, enabled on children */}
      <div
        className="absolute inset-0 pointer-events-none z-10
                   flex flex-col justify-between p-4"
      >
        {/* Top row */}
        <div className="flex justify-between items-start pointer-events-auto gap-3">
          <StatsPanel />
          <SourceFilter />
        </div>

        {/* Bottom row */}
        <div className="flex justify-between items-end pointer-events-auto gap-3">
          <Legend />
          <ControlBar />
          {/* Spacer to balance the layout */}
          <div className="w-32" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppDataProvider>
      <AppInner />
    </AppDataProvider>
  );
}
