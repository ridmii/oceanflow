import { create } from 'zustand';

interface QueryState {
  point: { lon: number; lat: number } | null;
  radiusKm: number;
  setPoint: (point: { lon: number; lat: number } | null) => void;
  setRadius: (radius: number) => void;
  clearQuery: () => void;
}

export const useQueryStore = create<QueryState>((set) => ({
  point: null,
  radiusKm: 100,
  setPoint: (point) => set({ point }),
  setRadius: (radiusKm) => set({ radiusKm }),
  clearQuery: () => set({ point: null }),
}));
