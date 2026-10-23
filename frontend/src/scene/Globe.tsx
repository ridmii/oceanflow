import { memo, Suspense } from 'react';
import { useLoader } from '@react-three/fiber';
import * as THREE from 'three';

const GlobeInner = memo(function Globe() {
  const [colorMap, bumpMap] = useLoader(THREE.TextureLoader, [
    '/textures/earth-blue-marble.jpg',
    '/textures/earth-topology.png',
  ]);

  // three.js textures default to flipY=true, which is correct for sphere UVs
  colorMap.colorSpace = THREE.SRGBColorSpace;
  colorMap.anisotropy = 8;

  return (
    <mesh>
      <sphereGeometry args={[1, 96, 96]} />
      <meshPhongMaterial
        map={colorMap}
        bumpMap={bumpMap}
        bumpScale={0.015}
        shininess={8}
        specular={new THREE.Color(0x111111)}
        color={new THREE.Color(0.55, 0.55, 0.55)}
        emissive={new THREE.Color(0x0a1520)}
        emissiveIntensity={0.4}
      />
    </mesh>
  );
});

export default function Globe() {
  return (
    <Suspense fallback={null}>
      <GlobeInner />
    </Suspense>
  );
}