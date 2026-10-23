import { memo, useMemo } from 'react';
import * as THREE from 'three';
import { useQueryStore } from '../store/queryStore';

const QueryRing = memo(function QueryRing() {
  const point = useQueryStore((state) => state.point);
  const radiusKm = useQueryStore((state) => state.radiusKm);

  const { position, quaternion } = useMemo(() => {
    if (!point) return { position: null, quaternion: null };
    
    // lat, lon to Cartesian
    const phi = (90 - point.lat) * (Math.PI / 180);
    const theta = (point.lon + 180) * (Math.PI / 180);
    
    const x = -Math.sin(phi) * Math.cos(theta);
    const y = Math.cos(phi);
    const z = Math.sin(phi) * Math.sin(theta);
    
    const pos = new THREE.Vector3(x, y, z);
    
    // To orient the ring tangent to the sphere, we make it look away from origin
    const normal = pos.clone().normalize();
    // Default ring geometry faces +Z, orient to normal
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);

    return { position: pos.multiplyScalar(1.002), quaternion: q }; // offset slightly to prevent z-fighting
  }, [point]);

  if (!point || !position || !quaternion) return null;

  const r3d = radiusKm / 6371.0;

  return (
    <mesh position={position} quaternion={quaternion}>
      <ringGeometry args={[r3d * 0.9, r3d, 64]} />
      <meshBasicMaterial color="#00ffcc" transparent opacity={0.6} side={THREE.DoubleSide} />
    </mesh>
  );
});

export default QueryRing;
