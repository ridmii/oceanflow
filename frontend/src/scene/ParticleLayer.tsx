// src/scene/ParticleLayer.tsx
// Custom THREE.Points with ShaderMaterial for ocean plastic particles.
// Reads from ParticleDataContext; updates GPU buffers in-place each frame.
// Never creates new geometry or typed arrays per frame.

import { useEffect, useRef, useCallback, useContext, memo } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { ParticleDataContext } from '../hooks/useParticleData';
import { usePlaybackStore } from '../store/playbackStore';
import { useFilterStore } from '../store/filterStore';
import { buildColorScaleTexture } from '../lib/colorScale';
import { RIVER_SOURCES } from '../data/sourceConfig';

// Import shaders as raw strings via Vite's ?raw import
import particleVert from './shaders/particle.vert.glsl?raw';
import particleFrag from './shaders/particle.frag.glsl?raw';

const MAX_SPEED    = 2.0;
const BASE_POINT_SIZE = 3.0;
const DEG2RAD      = Math.PI / 180;
const SOURCE_COUNT = RIVER_SOURCES.length; // 20

/** Convert geographic coordinates to Cartesian on unit sphere (R=1).
 *  Matches three-globe's convention exactly. */
export function lonLatToCartesian(
  lon: number,
  lat: number,
  R = 1.0,
): [number, number, number] {
  const phi   = (90 - lat) * DEG2RAD;
  const theta = (lon + 180) * DEG2RAD;
  return [
    -R * Math.sin(phi) * Math.cos(theta),
     R * Math.cos(phi),
     R * Math.sin(phi) * Math.sin(theta),
  ];
}

const ParticleLayer = memo(function ParticleLayer() {
  const ctx = useContext(ParticleDataContext);
  const { scene } = useThree();

  // Refs to GPU objects – never recreated
  const pointsRef       = useRef<THREE.Points | null>(null);
  const materialRef     = useRef<THREE.ShaderMaterial | null>(null);
  const posAttrRef      = useRef<THREE.BufferAttribute | null>(null);
  const speedAttrRef    = useRef<THREE.BufferAttribute | null>(null);
  const ageAttrRef      = useRef<THREE.BufferAttribute | null>(null);
  const srcIdxAttrRef   = useRef<THREE.BufferAttribute | null>(null);
  const colorTexRef     = useRef<THREE.DataTexture | null>(null);

  // Current frame ref – updated imperatively, never triggers re-render
  const currentFrameRef = useRef(0);
  const loadingRef      = useRef(false);

  const setupGeometry = useCallback(
    (particleCount: number) => {
      if (!ctx?.source) return;

      const N = particleCount;
      const positions    = new Float32Array(N * 3);
      const speeds       = new Float32Array(N);
      const ages         = new Float32Array(N);
      const sourceIdxs   = new Float32Array(N).fill(-1);

      const geo = new THREE.BufferGeometry();
      const posAttr    = new THREE.BufferAttribute(positions, 3);
      const speedAttr  = new THREE.BufferAttribute(speeds, 1);
      const ageAttr    = new THREE.BufferAttribute(ages, 1);
      const srcAttr    = new THREE.BufferAttribute(sourceIdxs, 1);

      posAttr.usage = THREE.DynamicDrawUsage;
      speedAttr.usage = THREE.DynamicDrawUsage;
      ageAttr.usage   = THREE.DynamicDrawUsage;
      srcAttr.usage   = THREE.DynamicDrawUsage;

      geo.setAttribute('position',     posAttr);
      geo.setAttribute('aSpeed',       speedAttr);
      geo.setAttribute('aAge',         ageAttr);
      geo.setAttribute('aSourceIndex', srcAttr);

      posAttrRef.current    = posAttr;
      speedAttrRef.current  = speedAttr;
      ageAttrRef.current    = ageAttr;
      srcIdxAttrRef.current = srcAttr;

      const colorTex = buildColorScaleTexture();
      colorTexRef.current = colorTex;

      // Initial source visibility array (all 1.0)
      const vis = new Array(SOURCE_COUNT).fill(1.0) as number[];

      const mat = new THREE.ShaderMaterial({
        vertexShader:   particleVert,
        fragmentShader: particleFrag,
        uniforms: {
          uMaxSpeed:          { value: MAX_SPEED },
          uPointSize:         { value: BASE_POINT_SIZE },
          uColorScale:        { value: colorTex },
          uMaxAge:            { value: 3 * 365 * 24 }, // hours
          uSimTime:           { value: 0 },
          uSourceVisibility:  { value: vis },
        },
        transparent: true,
        depthWrite:  false,
        blending:    THREE.AdditiveBlending,
      });

      materialRef.current = mat;
      const points = new THREE.Points(geo, mat);
      points.frustumCulled = false; // particles span the whole globe
      pointsRef.current = points;
      scene.add(points);
    },
    [ctx, scene],
  );

  // Initialize geometry once meta is loaded
  useEffect(() => {
    if (!ctx?.meta) return;
    setupGeometry(ctx.meta.particleCount);

    return () => {
      if (pointsRef.current) {
        scene.remove(pointsRef.current);
        pointsRef.current.geometry.dispose();
        (pointsRef.current.material as THREE.ShaderMaterial).dispose();
        colorTexRef.current?.dispose();
        pointsRef.current = null;
      }
    };
  }, [ctx?.meta, setupGeometry, scene]);

  // Per-frame: advance playback, update GPU buffers
  useFrame((_state, dt) => {
    const store = usePlaybackStore.getState();
    store.tick(dt);

    const frame = store.currentFrame;
    if (frame === currentFrameRef.current && !loadingRef.current) return;
    currentFrameRef.current = frame;

    const filter = useFilterStore.getState();

    // Update source visibility uniform
    const mat = materialRef.current;
    if (mat) {
      const vis = mat.uniforms.uSourceVisibility.value as number[];
      for (let i = 0; i < SOURCE_COUNT; i++) {
        const src = RIVER_SOURCES[i];
        vis[i] = (filter.visibility[src.id] ?? true) ? 1.0 : 0.0;
      }
      mat.uniforms.uSimTime.value = frame * (ctx?.meta?.timeStepHours ?? 6);
      mat.blending = filter.blendingMode === 'additive'
        ? THREE.AdditiveBlending
        : THREE.NormalBlending;
    }

    if (!ctx?.source || loadingRef.current) return;
    loadingRef.current = true;

    ctx.source
      .getParticleFrame(frame)
      .then((pf) => {
        const posArr  = posAttrRef.current?.array  as Float32Array | undefined;
        const spdArr  = speedAttrRef.current?.array as Float32Array | undefined;
        const ageArr  = ageAttrRef.current?.array  as Float32Array | undefined;
        const srcArr  = srcIdxAttrRef.current?.array as Float32Array | undefined;

        if (!posArr || !spdArr || !ageArr || !srcArr) {
          loadingRef.current = false;
          return;
        }

        const N = pf.lon.length;
        for (let i = 0; i < N; i++) {
          const [x, y, z] = lonLatToCartesian(pf.lon[i], pf.lat[i], 1.0);
          posArr[i * 3 + 0] = x;
          posArr[i * 3 + 1] = y;
          posArr[i * 3 + 2] = z;
          spdArr[i] = pf.speed[i];
          ageArr[i] = pf.age[i];
          srcArr[i] = pf.sourceIndex[i];
        }

        if (posAttrRef.current)    posAttrRef.current.needsUpdate    = true;
        if (speedAttrRef.current)  speedAttrRef.current.needsUpdate  = true;
        if (ageAttrRef.current)    ageAttrRef.current.needsUpdate    = true;
        if (srcIdxAttrRef.current) srcIdxAttrRef.current.needsUpdate = true;

        loadingRef.current = false;
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        usePlaybackStore.getState().setError(msg);
        loadingRef.current = false;
      });
  });

  return null; // All Three.js objects managed imperatively
});

export default ParticleLayer;
