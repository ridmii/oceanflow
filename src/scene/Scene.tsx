// src/scene/Scene.tsx
// Main R3F canvas composition. Sets up camera, lighting, starfield,
// and all scene layers. All layers are siblings of Globe.

import { memo, useRef, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import Globe from './Globe';
import ParticleLayer from './ParticleLayer';
import DensityHeatmap from './DensityHeatmap';
import TrailPass from './TrailPass';
import { usePrefersReducedMotion } from '../hooks/usePlayback';
import { FpsSampler } from '../ui/StatsPanel';

// ─── Starfield ────────────────────────────────────────────────────────────────
const Starfield = memo(function Starfield() {
  const countRef = useRef<THREE.Points | null>(null);
  const { scene } = useThree();

  useEffect(() => {
    const N = 2000;
    const positions = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const phi   = Math.acos(2 * Math.random() - 1);
      const theta = 2 * Math.PI * Math.random();
      const r     = 45 + Math.random() * 10;
      positions[i * 3 + 0] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.cos(phi);
      positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const mat = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.05,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.7,
    });
    const stars = new THREE.Points(geo, mat);
    countRef.current = stars;
    scene.add(stars);

    return () => {
      scene.remove(stars);
      geo.dispose();
      mat.dispose();
    };
  }, [scene]);

  return null;
});

// ─── Camera & Controls ────────────────────────────────────────────────────────
const CameraRig = memo(function CameraRig() {
  const controlsRef   = useRef<OrbitControlsImpl | null>(null);
  const hasInteracted = useRef(false);
  const reducedMotion = usePrefersReducedMotion();

  const handleStart = () => {
    hasInteracted.current = true;
    if (controlsRef.current) {
      controlsRef.current.autoRotate = false;
    }
  };

  useFrame(() => {
    if (!controlsRef.current) return;
    controlsRef.current.update();
  });

  return (
    <OrbitControls
      ref={controlsRef}
      minDistance={1.3}
      maxDistance={4.0}
      enablePan={false}
      autoRotate={!reducedMotion}
      autoRotateSpeed={0.3}
      onStart={handleStart}
    />
  );
});

// ─── Scene content ────────────────────────────────────────────────────────────
const SceneContent = memo(function SceneContent() {
  return (
    <>
      <ambientLight intensity={0.15} />
      <directionalLight position={[5, 3, 5]} intensity={0.8} color="#ffffff" />
      <Starfield />
      <Globe />
      <ParticleLayer />
      <DensityHeatmap />
      <TrailPass />
      <CameraRig />
      <FpsSampler />
    </>
  );
});

// ─── Main canvas export ───────────────────────────────────────────────────────
const Scene = memo(function Scene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 2.5], fov: 45, near: 0.01, far: 1000 }}
      gl={{
        antialias: true,
        alpha: false,
        powerPreference: 'high-performance',
        logarithmicDepthBuffer: false,
      }}
      style={{ background: '#050810', position: 'absolute', inset: 0 }}
      dpr={[1, 1.5]}
    >
      <SceneContent />
    </Canvas>
  );
});

export default Scene;
