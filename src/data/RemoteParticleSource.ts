// src/data/RemoteParticleSource.ts
// Stub for the real Lagrangian simulation backend.
// Swap in by setting ACTIVE_SOURCE = 'remote' in sourceConfig.ts.

import type { ParticleDataSource } from './ParticleDataSource';
import type {
  ParticleDatasetMeta,
  ParticleFrame,
  DensityFrame,
} from '../types/particle';

export class RemoteParticleSource implements ParticleDataSource {
  readonly name = 'Remote (Not Implemented)';

  loadMeta(): Promise<ParticleDatasetMeta> {
    return Promise.reject(new Error('RemoteParticleSource not implemented'));
  }

  getParticleFrame(_frameIndex: number): Promise<ParticleFrame> {
    return Promise.reject(new Error('RemoteParticleSource not implemented'));
  }

  getDensityFrame(_frameIndex: number): Promise<DensityFrame> {
    return Promise.reject(new Error('RemoteParticleSource not implemented'));
  }

  preload(_fromFrame: number, _toFrame: number): Promise<void> {
    return Promise.reject(new Error('RemoteParticleSource not implemented'));
  }
}
