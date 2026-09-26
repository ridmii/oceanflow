// src/lib/colorScale.ts
// Speed → color gradient used by both the shader and the UI legend.
// Modify this to change the particle color ramp.

import * as THREE from 'three';

/** Control points: [speed_m_s, r, g, b] */
const SPEED_RAMP: [number, number, number, number][] = [
  [0.0,  0x1a / 255, 0x3a / 255, 0x5c / 255],  // deep blue   #1a3a5c
  [0.5,  0x2e / 255, 0x7f / 255, 0xb8 / 255],  // ocean blue  #2e7fb8
  [1.25, 0x6e / 255, 0xc6 / 255, 0xe8 / 255],  // light cyan  #6ec6e8
  [2.0,  0xf2 / 255, 0xf2 / 255, 0xf2 / 255],  // near-white  #f2f2f2
];

const GRADIENT_SIZE = 256;

/** Create a 1D DataTexture (256 × 1) encoding the speed color scale. */
export function buildColorScaleTexture(): THREE.DataTexture {
  const data = new Uint8Array(GRADIENT_SIZE * 4);

  for (let i = 0; i < GRADIENT_SIZE; i++) {
    const t = i / (GRADIENT_SIZE - 1); // 0–1 maps to 0–2 m/s
    const speed = t * 2.0;

    // Find bracketing control points
    let lo = SPEED_RAMP[0];
    let hi = SPEED_RAMP[SPEED_RAMP.length - 1];
    for (let j = 0; j < SPEED_RAMP.length - 1; j++) {
      if (speed >= SPEED_RAMP[j][0] && speed <= SPEED_RAMP[j + 1][0]) {
        lo = SPEED_RAMP[j];
        hi = SPEED_RAMP[j + 1];
        break;
      }
    }

    const range = hi[0] - lo[0];
    const f = range > 0 ? (speed - lo[0]) / range : 0;
    data[i * 4 + 0] = Math.round((lo[1] + (hi[1] - lo[1]) * f) * 255);
    data[i * 4 + 1] = Math.round((lo[2] + (hi[2] - lo[2]) * f) * 255);
    data[i * 4 + 2] = Math.round((lo[3] + (hi[3] - lo[3]) * f) * 255);
    data[i * 4 + 3] = 255;
  }

  const tex = new THREE.DataTexture(data, GRADIENT_SIZE, 1, THREE.RGBAFormat);
  tex.needsUpdate = true;
  return tex;
}

/** Sample the scale for a given speed (m/s). Returns CSS hex. */
export function sampleColorScale(speed: number): string {
  const t = Math.max(0, Math.min(1, speed / 2.0));
  const idx = Math.round(t * (SPEED_RAMP.length - 1));
  const [, r, g, b] = SPEED_RAMP[idx];
  const toHex = (v: number) => Math.round(v * 255).toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

/** CSS gradient string for legend bar */
export const LEGEND_GRADIENT =
  `linear-gradient(to right, #1a3a5c, #2e7fb8, #6ec6e8, #f2f2f2)`;

/** Speed ticks for legend */
export const LEGEND_TICKS = [0, 0.5, 1.0, 1.5, 2.0]; // m/s
