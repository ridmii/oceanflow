// src/lib/binaryLoader.ts
// Utility for loading binary particle frame data.
// In MockParticleSource this is unused; in RemoteParticleSource it will
// fetch binary blobs from a worker endpoint and parse them into ParticleFrame.

import type { ParticleFrame } from '../types/particle';

/** Wire format header (32 bytes) */
interface FrameHeader {
  magic: number;         // 0x4F50 'OP'
  schemaVersion: number; // 1
  frameIndex: number;
  particleCount: number;
  reserved: number;
}

const MAGIC = 0x4f50;

/**
 * Parse a binary ArrayBuffer into a ParticleFrame.
 * Layout: [header 32B] [lon f32*N] [lat f32*N] [speed f32*N]
 *         [age f32*N] [sourceIndex i16*N, padded to 4B] [alive u8*N, padded to 4B]
 *
 * This function is intentionally unused in M1–M4; it will be wired in M6 / remote source.
 */
export function parseBinaryFrame(buffer: ArrayBuffer): ParticleFrame {
  const view = new DataView(buffer);
  const magic = view.getUint16(0, true);
  if (magic !== MAGIC) throw new Error(`Invalid frame magic: 0x${magic.toString(16)}`);

  const header: FrameHeader = {
    magic,
    schemaVersion: view.getUint16(2, true),
    frameIndex: view.getUint32(4, true),
    particleCount: view.getUint32(8, true),
    reserved: view.getUint32(12, true),
  };

  const N = header.particleCount;
  let offset = 32;

  const lon         = new Float32Array(buffer, offset, N); offset += N * 4;
  const lat         = new Float32Array(buffer, offset, N); offset += N * 4;
  const speed       = new Float32Array(buffer, offset, N); offset += N * 4;
  const age         = new Float32Array(buffer, offset, N); offset += N * 4;
  const sourceIndex = new Int16Array(buffer, offset, N);   offset += align4(N * 2);
  const alive       = new Uint8Array(buffer, offset, N);

  return {
    frameIndex: header.frameIndex,
    lon, lat, speed, age, sourceIndex, alive,
  };
}

function align4(n: number): number {
  return Math.ceil(n / 4) * 4;
}
