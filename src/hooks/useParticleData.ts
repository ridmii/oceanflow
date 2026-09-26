// src/hooks/useParticleData.ts
// React hook that loads metadata from the data source and initializes stores.
// Components import this at the app root level.

import { useEffect, useState, useContext, createContext, useRef } from 'react';
import type { ParticleDataSource } from '../data/ParticleDataSource';
import type { ParticleDatasetMeta } from '../types/particle';
import { usePlaybackStore } from '../store/playbackStore';
import { useFilterStore } from '../store/filterStore';

interface ParticleDataContextValue {
  source: ParticleDataSource;
  meta: ParticleDatasetMeta | null;
  loading: boolean;
  error: string | null;
}

export const ParticleDataContext = createContext<ParticleDataContextValue | null>(null);

/** Consume the particle data context. Must be within <ParticleDataProvider>. */
export function useParticleData(): ParticleDataContextValue {
  const ctx = useContext(ParticleDataContext);
  if (!ctx) throw new Error('useParticleData must be used within ParticleDataProvider');
  return ctx;
}

interface UseParticleDataSourceResult {
  meta: ParticleDatasetMeta | null;
  loading: boolean;
  error: string | null;
}

/** Internal hook used by the provider to load meta and wire up stores. */
export function useParticleDataSource(
  source: ParticleDataSource,
): UseParticleDataSourceResult {
  const [meta, setMeta]       = useState<ParticleDatasetMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const setFrameCount         = usePlaybackStore((s) => s.setFrameCount);
  const setStoreError         = usePlaybackStore((s) => s.setError);
  const initSources           = useFilterStore((s) => s.initSources);
  const loadedSourceRef       = useRef<string>('');

  useEffect(() => {
    if (loadedSourceRef.current === source.name) return;
    loadedSourceRef.current = source.name;

    setLoading(true);
    setError(null);

    source
      .loadMeta()
      .then((m) => {
        setMeta(m);
        setFrameCount(m.frameCount);
        initSources(m.sources.map((s) => s.id));
        setLoading(false);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
        setStoreError(msg);
        setLoading(false);
      });
  }, [source, setFrameCount, initSources, setStoreError]);

  return { meta, loading, error };
}
