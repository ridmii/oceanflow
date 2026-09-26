// src/store/filterStore.ts
// Zustand store for source visibility filtering.

import { create } from 'zustand';

export interface FilterState {
  /** Map from source id → visible. Default: all true. */
  visibility: Record<string, boolean>;
  showHeatmap: boolean;
  showTrails: boolean;
  blendingMode: 'additive' | 'normal';

  // Actions
  setSourceVisible: (id: string, visible: boolean) => void;
  setAllVisible: (ids: string[], visible: boolean) => void;
  toggleHeatmap: () => void;
  toggleTrails: () => void;
  setBlendingMode: (mode: 'additive' | 'normal') => void;
  initSources: (ids: string[]) => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  visibility: {},
  showHeatmap: false,
  showTrails: false,
  blendingMode: 'additive',

  setSourceVisible: (id, visible) =>
    set((s) => ({ visibility: { ...s.visibility, [id]: visible } })),

  setAllVisible: (ids, visible) =>
    set((s) => {
      const updated = { ...s.visibility };
      ids.forEach((id) => (updated[id] = visible));
      return { visibility: updated };
    }),

  toggleHeatmap: () => set((s) => ({ showHeatmap: !s.showHeatmap })),
  toggleTrails: () => set((s) => ({ showTrails: !s.showTrails })),
  setBlendingMode: (mode) => set({ blendingMode: mode }),

  initSources: (ids) =>
    set((s) => {
      const updated = { ...s.visibility };
      ids.forEach((id) => {
        if (!(id in updated)) updated[id] = true;
      });
      return { visibility: updated };
    }),
}));
