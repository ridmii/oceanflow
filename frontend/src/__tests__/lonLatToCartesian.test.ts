// src/__tests__/lonLatToCartesian.test.ts
// Unit test verifying that lonLatToCartesian matches three-globe's convention.
//
// three-globe uses the geographic convention:
//   phi   = (90 - lat) * DEG2RAD   (co-latitude from north pole)
//   theta = (lon + 180) * DEG2RAD  (longitude from the date line)
//   x = -R * sin(phi) * cos(theta)
//   y =  R * cos(phi)
//   z =  R * sin(phi) * sin(theta)

import { describe, it, expect } from 'vitest';
import { lonLatToCartesian } from '../scene/ParticleLayer';

const DEG2RAD = Math.PI / 180;
const EPS = 1e-6;

function approxEq(a: number, b: number, eps = EPS): boolean {
  return Math.abs(a - b) < eps;
}

describe('lonLatToCartesian', () => {
  it('North Pole (lat=90) maps to (0, 1, 0)', () => {
    const [x, y, z] = lonLatToCartesian(0, 90, 1);
    expect(approxEq(x, 0)).toBe(true);
    expect(approxEq(y, 1)).toBe(true);
    expect(approxEq(z, 0)).toBe(true);
  });

  it('South Pole (lat=-90) maps to (0, -1, 0)', () => {
    const [x, y, z] = lonLatToCartesian(0, -90, 1);
    expect(approxEq(x, 0)).toBe(true);
    expect(approxEq(y, -1)).toBe(true);
    expect(approxEq(z, 0)).toBe(true);
  });

  it('Equator at lon=0 has y=0', () => {
    const [, y] = lonLatToCartesian(0, 0, 1);
    expect(approxEq(y, 0)).toBe(true);
  });

  it('All points lie on unit sphere', () => {
    const testCases: [number, number][] = [
      [0, 0], [90, 0], [-90, 0], [180, 0],
      [121, 31.4],   // Yangtze mouth
      [-90, 29],     // Mississippi mouth
      [75, -25],     // Indian Ocean gyre center
    ];
    for (const [lon, lat] of testCases) {
      const [x, y, z] = lonLatToCartesian(lon, lat, 1);
      const r = Math.sqrt(x * x + y * y + z * z);
      expect(approxEq(r, 1, 1e-5)).toBe(true);
    }
  });

  it('Matches three-globe reference formula exactly', () => {
    const lon = 121.0, lat = 31.4, R = 1;
    const phi   = (90 - lat) * DEG2RAD;
    const theta = (lon + 180) * DEG2RAD;
    const refX  = -R * Math.sin(phi) * Math.cos(theta);
    const refY  =  R * Math.cos(phi);
    const refZ  =  R * Math.sin(phi) * Math.sin(theta);

    const [x, y, z] = lonLatToCartesian(lon, lat, R);
    expect(approxEq(x, refX)).toBe(true);
    expect(approxEq(y, refY)).toBe(true);
    expect(approxEq(z, refZ)).toBe(true);
  });

  it('Scales with radius parameter', () => {
    const [x1, y1, z1] = lonLatToCartesian(45, 45, 1);
    const [x2, y2, z2] = lonLatToCartesian(45, 45, 2);
    expect(approxEq(x2, x1 * 2)).toBe(true);
    expect(approxEq(y2, y1 * 2)).toBe(true);
    expect(approxEq(z2, z1 * 2)).toBe(true);
  });
});
