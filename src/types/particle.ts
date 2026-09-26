// src/types/particle.ts
// Central data contract. All components depend on these interfaces.
// Real simulation can swap in without touching rendering code.

export interface PlasticSource {
  id: string;
  name: string;
  lon: number;
  lat: number;
  intensity: number; // 0–1 normalized emission strength
  color: string;     // CSS hex color for UI swatches
}

export interface ParticleDatasetMeta {
  schemaVersion: 1;
  generatedAt: string;   // ISO 8601
  startDate: string;     // ISO 8601
  timeStepHours: number;
  frameCount: number;
  particleCount: number;
  sources: PlasticSource[];
  bounds: { west: number; east: number; south: number; north: number };
  heatmapGrid: { cols: number; rows: number };
}

/** One snapshot in time. Frame-major layout: all particles for one timestep. */
export interface ParticleFrame {
  frameIndex: number;
  lon: Float32Array;        // degrees [-180, 180]
  lat: Float32Array;        // degrees [-85, 85]
  speed: Float32Array;      // m/s [0, 2]
  age: Float32Array;        // simulated hours since spawn
  sourceIndex: Int16Array;  // index into meta.sources; -1 = dead/unassigned
  alive: Uint8Array;        // 1 = visible, 0 = dead
}

export interface DensityFrame {
  frameIndex: number;
  density: Float32Array; // length = heatmapGrid.cols * heatmapGrid.rows, normalized [0,1]
}

/** Top-level dataset handle. Components only see this abstraction. */
export interface ParticleDataset {
  meta: ParticleDatasetMeta;
  getParticleFrame(frameIndex: number): Promise<ParticleFrame>;
  getDensityFrame(frameIndex: number): Promise<DensityFrame>;
  preload?(fromFrame: number, toFrame: number): Promise<void>;
}
