// src/data/MockParticleSource.ts
// Procedurally generated ocean plastic transport simulation.
// Frame-major layout: each call to getParticleFrame() returns one complete
// snapshot of all particle positions at that timestep.
//
// The velocity field is intentionally simple (no real fluid dynamics).
// It is designed to LOOK like ocean plastic transport without claiming accuracy.

import type { ParticleDataSource } from './ParticleDataSource';
import type {
  ParticleDatasetMeta,
  ParticleFrame,
  DensityFrame,
} from '../types/particle';
import { RIVER_SOURCES } from './sourceConfig';

// ─── Simulation parameters ────────────────────────────────────────────────────
const FRAME_COUNT   = 240;
const TIME_STEP_H   = 6;       // hours per frame (6h → 60 simulated days total)
const PARTICLE_COUNT = 40_000;
const MAX_AGE_HOURS = 3 * 365 * 24; // 3 simulated years
const HEATMAP_COLS  = 720;
const HEATMAP_ROWS  = 360;

// ─── Ocean gyre vortices ──────────────────────────────────────────────────────
interface Vortex {
  cx: number; cy: number; radius: number; strength: number;
}
const VORTICES: Vortex[] = [
  { cx: -150, cy:  35, radius: 25, strength:  1.2 },  // North Pacific
  { cx: -120, cy: -30, radius: 22, strength: -1.0 },  // South Pacific
  { cx:  -40, cy:  35, radius: 18, strength:  1.1 },  // North Atlantic
  { cx:  -20, cy: -25, radius: 18, strength: -0.9 },  // South Atlantic
  { cx:   75, cy: -25, radius: 20, strength: -1.0 },  // Indian
  { cx:    0, cy:  75, radius: 15, strength:  0.3 },  // Arctic
];

// ─── Velocity field ───────────────────────────────────────────────────────────
function velocityAt(lon: number, lat: number, t: number): [number, number] {
  let u = 0, v = 0;

  // a) Gyres
  for (const vx of VORTICES) {
    const dx = lon - vx.cx;
    const dy = lat - vx.cy;
    const d2 = dx * dx + dy * dy;
    const falloff = Math.exp(-d2 / (vx.radius * vx.radius));
    u += (-dy * vx.strength * falloff) / 10;
    v += ( dx * vx.strength * falloff) / 10;
  }

  // b) Global westward zonal drift
  u += -0.6;

  // c) Time-varying perturbation
  u += 0.1 * Math.sin(t * 0.05 + lat * 0.1);
  v += 0.1 * Math.cos(t * 0.05 + lon * 0.1);

  return [u, v];
}

// ─── Gaussian noise (Box-Muller) ──────────────────────────────────────────────
function gaussianNoise(sigma: number): number {
  const u1 = Math.random();
  const u2 = Math.random();
  return sigma * Math.sqrt(-2 * Math.log(u1 + 1e-10)) * Math.cos(2 * Math.PI * u2);
}

// ─── Lon/lat clamping ─────────────────────────────────────────────────────────
function wrapLon(lon: number): number {
  while (lon > 180)  lon -= 360;
  while (lon < -180) lon += 360;
  return lon;
}
function clampLat(lat: number): number {
  return Math.max(-85, Math.min(85, lat));
}

// ─── Mock source class ────────────────────────────────────────────────────────
export class MockParticleSource implements ParticleDataSource {
  readonly name = 'Mock (Procedural)';

  private meta: ParticleDatasetMeta | null = null;
  // Initial per-particle state (lon, lat, sourceIndex, birthFrame)
  private initLon!: Float32Array;
  private initLat!: Float32Array;
  private initSrcIdx!: Int16Array;
  private birthFrame!: Int32Array;

  // LRU frame cache (last 4 frames to survive bi-directional scrubbing)
  private readonly CACHE_SIZE = 4;
  private frameCache = new Map<number, ParticleFrame>();

  async loadMeta(): Promise<ParticleDatasetMeta> {
    if (this.meta) return this.meta;
    this._initParticles();
    this.meta = {
      schemaVersion: 1,
      generatedAt: new Date().toISOString(),
      startDate: '2024-01-01T00:00:00Z',
      timeStepHours: TIME_STEP_H,
      frameCount: FRAME_COUNT,
      particleCount: PARTICLE_COUNT,
      sources: RIVER_SOURCES,
      bounds: { west: -180, east: 180, south: -85, north: 85 },
      heatmapGrid: { cols: HEATMAP_COLS, rows: HEATMAP_ROWS },
    };
    return this.meta;
  }

  /** Distribute particles proportional to source intensity, stagger birth times */
  private _initParticles(): void {
    const N = PARTICLE_COUNT;
    this.initLon   = new Float32Array(N);
    this.initLat   = new Float32Array(N);
    this.initSrcIdx = new Int16Array(N);
    this.birthFrame = new Int32Array(N);

    // Total intensity for normalization
    const total = RIVER_SOURCES.reduce((s, r) => s + r.intensity, 0);
    let pIdx = 0;
    const spawnWindow = Math.floor(FRAME_COUNT * 0.2); // first 20%

    for (let si = 0; si < RIVER_SOURCES.length; si++) {
      const src = RIVER_SOURCES[si];
      const count = si === RIVER_SOURCES.length - 1
        ? N - pIdx
        : Math.round((src.intensity / total) * N);

      for (let i = 0; i < count && pIdx < N; i++, pIdx++) {
        // Spawn near the river mouth with small Gaussian scatter (0.5°)
        this.initLon[pIdx]    = wrapLon(src.lon + gaussianNoise(0.5));
        this.initLat[pIdx]    = clampLat(src.lat + gaussianNoise(0.5));
        this.initSrcIdx[pIdx] = si;
        this.birthFrame[pIdx] = Math.floor(Math.random() * spawnWindow);
      }
    }
  }

  async getParticleFrame(frameIndex: number): Promise<ParticleFrame> {
    // Check cache first
    const cached = this.frameCache.get(frameIndex);
    if (cached) return cached;

    const frame = this._generateFrame(frameIndex);

    // LRU eviction
    if (this.frameCache.size >= this.CACHE_SIZE) {
      const oldest = this.frameCache.keys().next().value;
      if (oldest !== undefined) this.frameCache.delete(oldest);
    }
    this.frameCache.set(frameIndex, frame);
    return frame;
  }

  /** Generate frame by integrating each particle from birth to frameIndex */
  private _generateFrame(frameIndex: number): ParticleFrame {
    const N = PARTICLE_COUNT;
    const lon         = new Float32Array(N);
    const lat         = new Float32Array(N);
    const speed       = new Float32Array(N);
    const age         = new Float32Array(N);
    const sourceIndex = new Int16Array(N).fill(-1);
    const alive       = new Uint8Array(N);

    // Seeded-ish RNG per particle for reproducibility
    for (let i = 0; i < N; i++) {
      const birth = this.birthFrame[i];

      if (frameIndex < birth) {
        // Not born yet
        lon[i] = this.initLon[i];
        lat[i] = this.initLat[i];
        alive[i] = 0;
        continue;
      }

      const ageFrames = frameIndex - birth;
      const ageHours = ageFrames * TIME_STEP_H;

      if (ageHours > MAX_AGE_HOURS) {
        alive[i] = 0;
        continue;
      }

      // Integrate forward from birth position
      let lo = this.initLon[i];
      let la = this.initLat[i];

      // For performance, use a simplified multi-step integration
      // rather than re-integrating from frame 0 each time.
      // Use a fixed random seed per particle for noise reproducibility.
      const seed = BigInt(i) * 6364136223846793005n; // LCG constant
      let rngState = BigInt(i) ^ seed;

      const steps = ageFrames;
      for (let s = 0; s < steps; s++) {
        const t = (birth + s) * TIME_STEP_H;
        const [u, v] = velocityAt(lo, la, t);

        // Deterministic noise per step (cheap LCG)
        rngState = (rngState * 6364136223846793005n + 1442695040888963407n) & 0xFFFFFFFFFFFFFFFFn;
        const n1 = (Number(rngState & 0xFFFFn) / 0xFFFF - 0.5) * 0.04;
        rngState = (rngState * 6364136223846793005n + 1442695040888963407n) & 0xFFFFFFFFFFFFFFFFn;
        const n2 = (Number(rngState & 0xFFFFn) / 0xFFFF - 0.5) * 0.04;

        lo = wrapLon(lo + u * TIME_STEP_H + n1);
        la = clampLat(la + v * TIME_STEP_H + n2);
      }

      // Final velocity for speed attribute
      const [u, v] = velocityAt(lo, la, frameIndex * TIME_STEP_H);
      const spd = Math.sqrt(u * u + v * v) * 30; // scale to m/s range

      lon[i]         = lo;
      lat[i]         = la;
      speed[i]       = Math.min(2, Math.max(0, spd));
      age[i]         = ageHours;
      sourceIndex[i] = this.initSrcIdx[i];
      alive[i]       = 1;
    }

    return { frameIndex, lon, lat, speed, age, sourceIndex, alive };
  }

  async getDensityFrame(frameIndex: number): Promise<DensityFrame> {
    const frame = await this.getParticleFrame(frameIndex);
    const density = new Float32Array(HEATMAP_COLS * HEATMAP_ROWS);

    // Bin particles
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      if (!frame.alive[i]) continue;
      const col = Math.floor(((frame.lon[i] + 180) / 360) * HEATMAP_COLS);
      const row = Math.floor(((frame.lat[i] + 85) / 170) * HEATMAP_ROWS);
      if (col >= 0 && col < HEATMAP_COLS && row >= 0 && row < HEATMAP_ROWS) {
        density[row * HEATMAP_COLS + col]++;
      }
    }

    // Light 3×3 Gaussian blur
    const blurred = gaussianBlur3x3(density, HEATMAP_COLS, HEATMAP_ROWS);

    // Normalize by max
    let maxVal = 0;
    for (let i = 0; i < blurred.length; i++) if (blurred[i] > maxVal) maxVal = blurred[i];
    if (maxVal > 0) for (let i = 0; i < blurred.length; i++) blurred[i] /= maxVal;

    return { frameIndex, density: blurred };
  }

  async preload(fromFrame: number, toFrame: number): Promise<void> {
    for (let f = fromFrame; f <= toFrame; f++) {
      await this.getParticleFrame(f);
    }
  }
}

// ─── 3×3 Gaussian blur ────────────────────────────────────────────────────────
function gaussianBlur3x3(
  data: Float32Array,
  cols: number,
  rows: number,
): Float32Array {
  const kernel = [1/16, 2/16, 1/16, 2/16, 4/16, 2/16, 1/16, 2/16, 1/16];
  const out = new Float32Array(data.length);

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      let sum = 0;
      let k = 0;
      for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
          const nr = r + dr;
          const nc = c + dc;
          if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) {
            sum += data[nr * cols + nc] * kernel[k];
          }
          k++;
        }
      }
      out[r * cols + c] = sum;
    }
  }
  return out;
}
