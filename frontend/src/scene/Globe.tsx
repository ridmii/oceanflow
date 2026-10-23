import { memo, Suspense } from 'react';
import { useLoader } from '@react-three/fiber';
import * as THREE from 'three';
import { useQueryStore } from '../store/queryStore';

const GlobeInner = memo(function Globe() {
  const [colorMap, bumpMap] = useLoader(THREE.TextureLoader, [
    '/textures/earth-blue-marble.jpg',
    '/textures/earth-topology.png',
  ]);

  // three.js textures default to flipY=true, which is correct for sphere UVs
  colorMap.colorSpace = THREE.SRGBColorSpace;
  colorMap.anisotropy = 8;
  
  const setPoint = useQueryStore(state => state.setPoint);

  const handleClick = (event: any) => {
    event.stopPropagation();
    const point = event.point; // THREE.Vector3
    const R = point.length();
    const phi = Math.acos(point.y / R);
    const lat = 90 - (phi * 180 / Math.PI);
    const theta = Math.atan2(point.z, -point.x);
    const lon = (theta * 180 / Math.PI) - 180;
    setPoint({ lon, lat });
  };

  return (
    <mesh onClick={handleClick}>
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