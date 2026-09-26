# OceanFlow – Ocean Plastic Transport Tracker

A visually stunning, interactive 3D globe visualization of simulated ocean plastic particle transport. Built with React 18, TypeScript, Three.js, @react-three/fiber, and Zustand.

> **Note:** This release uses procedurally generated mock data. No real ocean models or external APIs are used. The architecture is designed so a real Lagrangian simulation can be swapped in with minimal changes.

---

## Quick Start

```bash
npm install
npm run dev
```

Open http://localhost:5173 in a modern browser.

## Build for Production

```bash
npm run build      # Type-checks then builds
npm run preview    # Serve the production bundle
```

## Lint & Type-check

```bash
npm run lint       # ESLint (zero warnings allowed)
npm run typecheck  # tsc --noEmit
npm test           # Vitest unit tests
```

---

## How to Swap in a Real Data Source

1. **Implement `ParticleDataSource`** in `src/data/RemoteParticleSource.ts`:

```typescript
import type { ParticleDataSource } from './ParticleDataSource';

export class RemoteParticleSource implements ParticleDataSource {
  readonly name = 'Real Ocean Model';

  async loadMeta() { /* fetch from your API */ }
  async getParticleFrame(frameIndex: number) { /* fetch binary frame */ }
  async getDensityFrame(frameIndex: number) { /* fetch density grid */ }
  async preload(from: number, to: number) { /* warm up cache */ }
}
```

2. **Change the flag** in `src/data/sourceConfig.ts`:

```typescript
export const ACTIVE_SOURCE: SourceKey = 'remote'; // was 'mock'
```

3. **That's it.** All components use `ParticleDataContext` and never import concrete sources.

---

## Data Contract

All components receive data through the `ParticleDataSource` interface (see `src/data/ParticleDataSource.ts`).

### `ParticleFrame` (frame-major layout)

```typescript
interface ParticleFrame {
  frameIndex: number;
  lon: Float32Array;        // degrees [-180, 180]
  lat: Float32Array;        // degrees [-85, 85]
  speed: Float32Array;      // m/s [0, 2]
  age: Float32Array;        // simulated hours since spawn
  sourceIndex: Int16Array;  // index into sources array; -1 = unassigned
  alive: Uint8Array;        // 1 = visible, 0 = dead/not-yet-spawned
}
```

**Why frame-major?** Only 2–3 frames are in memory at once. A single GPU buffer update per frame. Compatible with streaming from disk or worker without restructuring.

### Coordinate Convention

Lon/lat → 3D Cartesian matches `three-globe`:

```
phi   = (90 - lat) * DEG2RAD
theta = (lon + 180) * DEG2RAD
x = -R * sin(phi) * cos(theta)
y =  R * cos(phi)
z =  R * sin(phi) * sin(theta)
```

---

## Architecture

```
src/
├── types/               # Data contract interfaces (particle.ts)
├── data/
│   ├── ParticleDataSource.ts   # Interface (swap point)
│   ├── MockParticleSource.ts   # Procedural generator
│   ├── RemoteParticleSource.ts # Stub for real backend
│   └── sourceConfig.ts         # ACTIVE_SOURCE flag + river sources
├── scene/
│   ├── Scene.tsx         # R3F Canvas composition
│   ├── Globe.tsx         # three-globe with atmosphere shader
│   ├── ParticleLayer.tsx # THREE.Points with ShaderMaterial
│   ├── DensityHeatmap.tsx
│   ├── TrailPass.tsx     # Screen-space trails (optional)
│   └── shaders/          # GLSL vertex/fragment shaders
├── ui/
│   ├── ControlBar.tsx    # Wrapper
│   ├── Timeline.tsx      # Play/pause, speed, scrubber
│   ├── StatsPanel.tsx    # FPS, particle count, toggles
│   ├── SourceFilter.tsx  # River source checkboxes
│   └── Legend.tsx        # Speed color scale
├── store/
│   ├── playbackStore.ts  # Zustand: frame, play state
│   └── filterStore.ts    # Zustand: visibility, toggles
├── hooks/
│   ├── useParticleData.ts  # Context + meta loader
│   └── usePlayback.ts      # Keyboard + reduced-motion
└── lib/
    ├── colorScale.ts     # Speed → color gradient + DataTexture
    ├── format.ts         # Date/number formatting
    └── binaryLoader.ts   # Binary frame parser (for remote source)
```

---

## Mock Data Generator

The `MockParticleSource` produces gyre-like particle transport using:

- **6 rotational vortices** at real ocean gyre centers (North/South Pacific, North/South Atlantic, Indian, Arctic)
- **Global westward zonal drift** (−0.6°/h)
- **Time-varying perturbation** (sinusoidal)
- **20 river sources** from Meijer et al. 2021, distributed proportionally
- **240 frames** × **6 hours/frame** = 60 simulated days
- **40,000 particles** total

---

## Known Limitations

1. **Trail occlusion**: Screen-space trails do not respect globe geometry. Particles on the far side leave trails on the near side. Gate behind the "Motion trails" toggle (default off).

2. **Mock integration performance**: The mock source re-integrates each particle from birth to the requested frame on demand. With 40,000 particles × 240 frames, scrubbing to late frames may take ~200ms. A real source streams pre-computed frames instantly.

3. **No interpolation**: Particle positions jump discretely between frames (6-hour steps). Inter-frame interpolation would require storing two frames simultaneously.

4. **Heatmap resolution**: The density heatmap is 720×360 (0.5° resolution) and updates the full GPU texture every frame when enabled.

5. **three-globe vs. ParticleLayer positioning**: If the earth texture has not loaded yet, particles may appear floating. This resolves once the texture loads.

6. **Volga River**: The Volga drains into the Caspian Sea, not an ocean. Included per Meijer et al. 2021 dataset but particles will accumulate inland.

---

## Performance Targets

| Metric              | Target  |
|---------------------|---------|
| FPS (40k particles) | ≥ 60    |
| FPS minimum         | ≥ 30    |
| JS heap peak        | ≤ 400 MB |
| React tick budget   | ≤ 8 ms  |

---

## License

MIT – see LICENSE file.
