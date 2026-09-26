// src/scene/TrailPass.tsx
// Optional screen-space trail effect via ping-pong render targets.
// WARNING: Screen-space trails do not respect globe occlusion.
// Disabled by default; toggle in Stats panel.

import { useEffect, useRef, memo } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useFilterStore } from '../store/filterStore';
import trailVert from './shaders/trail.vert.glsl?raw';
import trailFrag from './shaders/trail.frag.glsl?raw';

const TrailPass = memo(function TrailPass() {
  const { gl, size, scene, camera } = useThree();
  const rtA      = useRef<THREE.WebGLRenderTarget | null>(null);
  const rtB      = useRef<THREE.WebGLRenderTarget | null>(null);
  const quadRef  = useRef<THREE.Mesh | null>(null);
  const matRef   = useRef<THREE.ShaderMaterial | null>(null);
  const pingRef  = useRef(0); // 0 = A read, B write; 1 = B read, A write

  useEffect(() => {
    const { width, height } = size;
    const opts = { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter };
    rtA.current = new THREE.WebGLRenderTarget(width, height, opts);
    rtB.current = new THREE.WebGLRenderTarget(width, height, opts);

    const geo = new THREE.PlaneGeometry(2, 2);
    const mat = new THREE.ShaderMaterial({
      vertexShader:   trailVert,
      fragmentShader: trailFrag,
      uniforms: {
        tPrevTrail:    { value: rtA.current.texture },
        tCurrentFrame: { value: rtB.current.texture },
        uDecay:        { value: 0.94 },
      },
      depthTest:  false,
      depthWrite: false,
    });

    matRef.current = mat;
    quadRef.current = new THREE.Mesh(geo, mat);

    return () => {
      rtA.current?.dispose();
      rtB.current?.dispose();
      geo.dispose();
      mat.dispose();
    };
  }, [size]);

  useFrame(() => {
    const filter = useFilterStore.getState();
    if (!filter.showTrails) return;
    if (!rtA.current || !rtB.current || !matRef.current) return;

    // Ping-pong: render scene → rtB, blend rtA+rtB → display
    const read  = pingRef.current === 0 ? rtA.current : rtB.current;
    const write = pingRef.current === 0 ? rtB.current : rtA.current;
    pingRef.current = 1 - pingRef.current;

    gl.setRenderTarget(write);
    gl.render(scene, camera);
    gl.setRenderTarget(null);

    matRef.current.uniforms.tPrevTrail.value    = read.texture;
    matRef.current.uniforms.tCurrentFrame.value = write.texture;
  });

  return null;
});

export default TrailPass;
