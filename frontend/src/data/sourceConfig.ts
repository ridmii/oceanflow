// src/data/sourceConfig.ts
// ── Swap flag ─────────────────────────────────────────────────────────────────
// Change ACTIVE_SOURCE to 'remote' to use RemoteParticleSource.
// The rest of the app is unaffected.

import type { ParticleDataSource } from './ParticleDataSource';
import type { PlasticSource } from '../types/particle';
import { MockParticleSource } from './MockParticleSource';
import { RemoteParticleSource } from './RemoteParticleSource';

export type SourceKey = 'mock' | 'remote';

export const ACTIVE_SOURCE: SourceKey = 'mock';

/** Factory — returns the configured data source. */
export function createDataSource(): ParticleDataSource {
  switch (ACTIVE_SOURCE) {
    case 'mock':   return new MockParticleSource();
    case 'remote': return new RemoteParticleSource();
  }
}

// ─── 20 largest river plastic sources (Meijer et al. 2021) ───────────────────
// Colors from Tableau10 + Set3 categorical palette
const CATEGORICAL_COLORS = [
  '#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f',
  '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac',
  '#8cd17d', '#b6992d', '#499894', '#86bcb6', '#f1ce63',
  '#f2f2f2', '#a0cbe8', '#ffbe7d', '#fabfd2', '#d37295',
];

export const RIVER_SOURCES: PlasticSource[] = [
  { id: 'yangtze',    name: 'Yangtze',       lon:  121.0, lat:  31.4, intensity: 1.00, color: CATEGORICAL_COLORS[0]  },
  { id: 'ganges',     name: 'Ganges',        lon:   90.0, lat:  22.0, intensity: 0.85, color: CATEGORICAL_COLORS[1]  },
  { id: 'mekong',     name: 'Mekong',        lon:  106.5, lat:  10.0, intensity: 0.75, color: CATEGORICAL_COLORS[2]  },
  { id: 'nile',       name: 'Nile',          lon:   31.0, lat:  30.0, intensity: 0.60, color: CATEGORICAL_COLORS[3]  },
  { id: 'amazon',     name: 'Amazon',        lon:  -50.0, lat:  -1.0, intensity: 0.55, color: CATEGORICAL_COLORS[4]  },
  { id: 'mississippi',name: 'Mississippi',   lon:  -90.0, lat:  29.0, intensity: 0.50, color: CATEGORICAL_COLORS[5]  },
  { id: 'danube',     name: 'Danube',        lon:   29.0, lat:  45.0, intensity: 0.45, color: CATEGORICAL_COLORS[6]  },
  { id: 'niger',      name: 'Niger',         lon:    5.0, lat:   8.0, intensity: 0.42, color: CATEGORICAL_COLORS[7]  },
  { id: 'indus',      name: 'Indus',         lon:   67.0, lat:  24.0, intensity: 0.40, color: CATEGORICAL_COLORS[8]  },
  { id: 'pearl',      name: 'Pearl',         lon:  113.5, lat:  22.5, intensity: 0.38, color: CATEGORICAL_COLORS[9]  },
  { id: 'volga',      name: 'Volga',         lon:   48.0, lat:  46.0, intensity: 0.35, color: CATEGORICAL_COLORS[10] },
  { id: 'brahma',     name: 'Brahmaputra',   lon:   90.5, lat:  24.0, intensity: 0.33, color: CATEGORICAL_COLORS[11] },
  { id: 'irrawaddy',  name: 'Irrawaddy',     lon:   95.0, lat:  17.0, intensity: 0.30, color: CATEGORICAL_COLORS[12] },
  { id: 'solo',       name: 'Solo',          lon:  112.0, lat:  -7.0, intensity: 0.28, color: CATEGORICAL_COLORS[13] },
  { id: 'pasig',      name: 'Pasig',         lon:  120.9, lat:  14.6, intensity: 0.25, color: CATEGORICAL_COLORS[14] },
  { id: 'chaophraya', name: 'Chao Phraya',   lon:  100.5, lat:  13.5, intensity: 0.23, color: CATEGORICAL_COLORS[15] },
  { id: 'hlaing',     name: 'Hlaing',        lon:   96.0, lat:  16.8, intensity: 0.20, color: CATEGORICAL_COLORS[16] },
  { id: 'cross',      name: 'Cross',         lon:    8.0, lat:   5.0, intensity: 0.18, color: CATEGORICAL_COLORS[17] },
  { id: 'imo',        name: 'Imo',           lon:    7.0, lat:   4.8, intensity: 0.16, color: CATEGORICAL_COLORS[18] },
  { id: 'magdalena',  name: 'Magdalena',     lon:  -74.0, lat:  10.5, intensity: 0.15, color: CATEGORICAL_COLORS[19] },
];
