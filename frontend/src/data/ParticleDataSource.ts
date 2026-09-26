// src/data/ParticleDataSource.ts
// The abstraction boundary. Components depend ONLY on this interface.
// To swap in real data: implement this interface and update sourceConfig.ts.

import type {
  ParticleDatasetMeta,
  ParticleFrame,
  DensityFrame,
} from '../types/particle';

export interface ParticleDataSource {
  readonly name: string;
  loadMeta(): Promise<ParticleDatasetMeta>;
  getParticleFrame(frameIndex: number): Promise<ParticleFrame>;
  getDensityFrame(frameIndex: number): Promise<DensityFrame>;
  /** Optional: warm up frames ahead of current playhead */
  preload?(fromFrame: number, toFrame: number): Promise<void>;
}
