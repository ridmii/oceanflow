// src/scene/DensityHeatmap.tsx
// Optional density heatmap overlay on the globe surface.
// Rendered as a sphere slightly larger than the globe (R=1.002).

import { useEffect, useRef, useContext, memo } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { ParticleDataContext } from '../hooks/useParticleData';
import { usePlaybackStore } from '../store/playbackStore';
import { useFilterStore } from '../store/filterStore';

const HEATMAP_VERT = /* glsl */`
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const HEATMAP_FRAG = /* glsl */`
  uniform sampler2D uDensity;
  uniform float uOpacity;
  varying vec2 vUv;

  // Viridis-like color map: low→high density
  vec3 densityColor(float t) {
    t = clamp(t, 0.0, 1.0);
    vec3 a = vec3(0.267, 0.004, 0.329); // dark purple
    vec3 b = vec3(0.282, 0.440, 0.612); // teal-blue
    vec3 c = vec3(0.129, 0.694, 0.557); // green
    vec3 d = vec3(0.993, 0.906, 0.144); // yellow

    if (t < 0.333) return mix(a, b, t / 0.333);
    if (t < 0.667) return mix(b, c, (t - 0.333) / 0.334);
    return mix(c, d, (t - 0.667) / 0.333);
  }

  void main() {
    float density = texture2D(uDensity, vUv).r;
    if (density < 0.01) discard;
    vec3 color = densityColor(density);
    gl_FragColor = vec4(color, density * uOpacity);
  }
`;

const DensityHeatmap = memo(function DensityHeatmap() {
  const ctx        = useContext(ParticleDataContext);
  const { scene }  = useThree();
  const meshRef    = useRef<THREE.Mesh | null>(null);
  const texRef     = useRef<THREE.DataTexture | null>(null);
  const lastFrameRef = useRef(-1);

  useEffect(() => {
    if (!ctx?.meta) return;
    const { cols, rows } = ctx.meta.heatmapGrid;

    const data = new Float32Array(cols * rows);
    const tex  = new THREE.DataTexture(data, cols, rows, THREE.RedFormat, THREE.FloatType);
    tex.needsUpdate = true;
    texRef.current = tex;

    const geo = new THREE.SphereGeometry(1.002, 128, 64);
    const mat = new THREE.ShaderMaterial({
      vertexShader:   HEATMAP_VERT,
      fragmentShader: HEATMAP_FRAG,
      uniforms: {
        uDensity: { value: tex },
        uOpacity: { value: 0.5 },
      },
      transparent: true,
      depthWrite:  false,
      blending:    THREE.NormalBlending,
    });

    const mesh = new THREE.Mesh(geo, mat);
    meshRef.current = mesh;
    scene.add(mesh);

    return () => {
      scene.remove(mesh);
      geo.dispose();
      mat.dispose();
      tex.dispose();
    };
  }, [ctx?.meta, scene]);

  useFrame(() => {
    const filter = useFilterStore.getState();
    if (!meshRef.current) return;
    meshRef.current.visible = filter.showHeatmap;
    if (!filter.showHeatmap) return;

    const frame = usePlaybackStore.getState().currentFrame;
    if (frame === lastFrameRef.current) return;
    lastFrameRef.current = frame;

    ctx?.source
      .getDensityFrame(frame)
      .then((df) => {
        if (!texRef.current) return;
        (texRef.current.image as unknown as { data: Float32Array }).data.set(df.density);
        texRef.current.needsUpdate = true;
      })
      .catch(() => {
        // Silently ignore – heatmap is optional
      });
  });

  return null;
});

export default DensityHeatmap;
