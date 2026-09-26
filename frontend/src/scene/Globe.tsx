// src/scene/Globe.tsx
// Textured Earth globe built with three-globe.
// Renders as a sibling to ParticleLayer – NOT a parent.

import { useEffect, useRef, memo } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import ThreeGlobe from 'three-globe';
import * as THREE from 'three';

// Atmosphere fresnel shader
const ATMO_VERT = /* glsl */`
  varying vec3 vNormal;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const ATMO_FRAG = /* glsl */`
  varying vec3 vNormal;
  void main() {
    float intensity = pow(0.65 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.0);
    gl_FragColor = vec4(0.3, 0.6, 1.0, 1.0) * intensity * 0.15;
  }
`;

const Globe = memo(function Globe() {
  const globeRef     = useRef<ThreeGlobe | null>(null);
  const atmoRef      = useRef<THREE.Mesh | null>(null);
  const groupRef     = useRef<THREE.Group | null>(null);
  const { scene }    = useThree();

  useEffect(() => {
    const globe = new ThreeGlobe()
      .globeImageUrl('//unpkg.com/three-globe/example/img/earth-dark.jpg')
      .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png');

    // three-globe renders at radius 100 by default – we normalize to 1.0
    // by wrapping in a group and scaling down
    globe.scale.setScalar(1 / 100);

    // Atmosphere sphere (Fresnel glow)
    const atmoGeo = new THREE.SphereGeometry(1.015, 64, 64);
    const atmoMat = new THREE.ShaderMaterial({
      vertexShader:   ATMO_VERT,
      fragmentShader: ATMO_FRAG,
      side:           THREE.BackSide,
      blending:       THREE.AdditiveBlending,
      transparent:    true,
      depthWrite:     false,
    });
    const atmo = new THREE.Mesh(atmoGeo, atmoMat);
    atmoRef.current  = atmo;
    globeRef.current = globe;

    const group = new THREE.Group();
    group.add(globe);
    group.add(atmo);
    groupRef.current = group;
    scene.add(group);

    return () => {
      scene.remove(group);
      // ThreeGlobe doesn't expose dispose; let GC clean up internals
      atmoGeo.dispose();
      atmoMat.dispose();
    };
  }, [scene]);

  // No per-frame logic needed for the static globe
  useFrame(() => {
    // Intentionally empty – globe rotation is handled by OrbitControls auto-rotate
  });

  return null; // Imperatively managed
});

export default Globe;
