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
  readonly name = 'Remote (proxied)';
  
  private runId = 'minimal';
  private baseUrl = '/api';

  async loadMeta(): Promise<ParticleDatasetMeta> {
    const res = await fetch(`${this.baseUrl}/runs/${this.runId}/meta`);
    if (!res.ok) {
      throw new Error(`Failed to load meta: ${res.statusText}`);
    }
    return res.json();
  }

  async getParticleFrame(frameIndex: number): Promise<ParticleFrame> {
    const res = await fetch(`${this.baseUrl}/runs/${this.runId}/frames/${frameIndex}`);
    if (!res.ok) {
      throw new Error(`Failed to load frame ${frameIndex}: ${res.statusText}`);
    }
    
    const particleCount = parseInt(res.headers.get('x-particle-count') || '500', 10);
    const buffer = await res.arrayBuffer();
    const view = new DataView(buffer);
    
    const lon = new Float32Array(particleCount);
    const lat = new Float32Array(particleCount);
    const speed = new Float32Array(particleCount);
    const age = new Float32Array(particleCount);
    const sourceIndex = new Int16Array(particleCount);
    const alive = new Uint8Array(particleCount);
    
    let offset = 0;
    for (let i = 0; i < particleCount; i++) {
      lon[i] = view.getFloat32(offset, true); offset += 4;
      lat[i] = view.getFloat32(offset, true); offset += 4;
      speed[i] = view.getFloat32(offset, true) * 111000.0; offset += 4;
      age[i] = view.getFloat32(offset, true) * 24.0; offset += 4;
      sourceIndex[i] = view.getInt16(offset, true); offset += 2;
      alive[i] = view.getUint8(offset); offset += 1;
    }

    if (frameIndex === 0) {
      console.log('Frame 0 first particle parsed:', {
        lon: lon[0], lat: lat[0], speed: speed[0], age: age[0], sourceIndex: sourceIndex[0], alive: alive[0]
      });
    }

    return {
      frameIndex,
      lon, lat, speed, age, sourceIndex, alive
    };
  }

  async getDensityFrame(frameIndex: number): Promise<DensityFrame> {
    const res = await fetch(`${this.baseUrl}/runs/${this.runId}/density/${frameIndex}`);
    if (!res.ok) {
      // Return empty density frame if it's missing (since M5 adds density)
      if (res.status === 404) {
         return { frameIndex, density: new Float32Array(0) };
      }
      throw new Error(`Failed to load density ${frameIndex}: ${res.statusText}`);
    }
    const buffer = await res.arrayBuffer();
    return {
      frameIndex,
      density: new Float32Array(buffer)
    };
  }

  async preload(fromFrame: number, toFrame: number): Promise<void> {
    // Basic preloading: fire off fetches and ignore results (browser caches them)
    const promises = [];
    for (let i = fromFrame; i <= toFrame; i++) {
      promises.push(
        fetch(`${this.baseUrl}/runs/${this.runId}/frames/${i}`).catch(() => {})
      );
    }
    await Promise.all(promises);
  }
}
