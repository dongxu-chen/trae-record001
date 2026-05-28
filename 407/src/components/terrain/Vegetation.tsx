import { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useHeightmapStore } from '@/store/heightmapStore';
import { useTerrainStore } from '@/store/terrainStore';

export function Vegetation() {
  const amplitude = useTerrainStore((s) => s.amplitude);
  const waterLevel = useTerrainStore((s) => s.waterLevel);
  const chunkSize = useTerrainStore((s) => s.chunkSize);
  const chunks = useTerrainStore((s) => s.chunks);
  const getInterpolatedHeight = useHeightmapStore((s) => s.getInterpolatedHeight);
  const vegetation = useHeightmapStore((s) => s.vegetation);
  const modified = useHeightmapStore((s) => s.modified);

  const worldSize = chunkSize * chunks;

  const treesRef = useRef<THREE.InstancedMesh>(null);
  const leavesRef = useRef<THREE.InstancedMesh>(null);
  const grassRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const treePlacements = useMemo(() => {
    if (!vegetation.enabled) return [];
    const placements: { pos: THREE.Vector3; scale: number; rot: number }[] = [];
    const { treeCount, maxAltitude, maxSlope, density } = vegetation;

    for (let i = 0; i < treeCount * density; i++) {
      const wx = (Math.random() - 0.5) * worldSize * 0.9;
      const wz = (Math.random() - 0.5) * worldSize * 0.9;
      const h = getInterpolatedHeight(wx, wz, worldSize);

      const normalizedH = (h - waterLevel) / Math.max(0.001, amplitude);
      if (normalizedH < 0.1 || normalizedH > maxAltitude) continue;

      const step = 5;
      const hL = getInterpolatedHeight(wx - step, wz, worldSize);
      const hR = getInterpolatedHeight(wx + step, wz, worldSize);
      const hU = getInterpolatedHeight(wx, wz - step, worldSize);
      const hD = getInterpolatedHeight(wx, wz + step, worldSize);
      const slope = Math.max(Math.abs(hR - hL), Math.abs(hD - hU)) / step;
      if (slope > maxSlope) continue;

      placements.push({
        pos: new THREE.Vector3(wx, h, wz),
        scale: 0.7 + Math.random() * 0.9,
        rot: Math.random() * Math.PI * 2,
      });
    }

    return placements;
  }, [vegetation, modified, amplitude, waterLevel, worldSize, getInterpolatedHeight]);

  const grassPlacements = useMemo(() => {
    if (!vegetation.enabled) return [];
    const placements: { pos: THREE.Vector3; scale: number; rot: number }[] = [];
    const { grassCount, maxAltitude, maxSlope, density } = vegetation;

    for (let i = 0; i < grassCount * density; i++) {
      const wx = (Math.random() - 0.5) * worldSize * 0.9;
      const wz = (Math.random() - 0.5) * worldSize * 0.9;
      const h = getInterpolatedHeight(wx, wz, worldSize);

      const normalizedH = (h - waterLevel) / Math.max(0.001, amplitude);
      if (normalizedH < 0.15 || normalizedH > maxAltitude * 0.8) continue;

      const step = 3;
      const hL = getInterpolatedHeight(wx - step, wz, worldSize);
      const hR = getInterpolatedHeight(wx + step, wz, worldSize);
      const hU = getInterpolatedHeight(wx, wz - step, worldSize);
      const hD = getInterpolatedHeight(wx, wz + step, worldSize);
      const slope = Math.max(Math.abs(hR - hL), Math.abs(hD - hU)) / step;
      if (slope > maxSlope * 1.2) continue;

      placements.push({
        pos: new THREE.Vector3(wx, h + 0.2, wz),
        scale: 0.6 + Math.random() * 0.8,
        rot: Math.random() * Math.PI * 2,
      });
    }

    return placements;
  }, [vegetation, modified, amplitude, waterLevel, worldSize, getInterpolatedHeight]);

  useEffect(() => {
    if (!treesRef.current || !leavesRef.current) return;

    treePlacements.forEach((p, i) => {
      dummy.position.copy(p.pos);
      dummy.rotation.y = p.rot;
      dummy.scale.setScalar(p.scale);
      dummy.updateMatrix();
      treesRef.current!.setMatrixAt(i, dummy.matrix);
      leavesRef.current!.setMatrixAt(i, dummy.matrix);
    });

    treesRef.current.count = treePlacements.length;
    treesRef.current.instanceMatrix.needsUpdate = true;
    leavesRef.current.count = treePlacements.length;
    leavesRef.current.instanceMatrix.needsUpdate = true;
  }, [treePlacements, dummy]);

  useEffect(() => {
    if (!grassRef.current) return;

    grassPlacements.forEach((p, i) => {
      dummy.position.copy(p.pos);
      dummy.rotation.y = p.rot;
      dummy.scale.setScalar(p.scale);
      dummy.updateMatrix();
      grassRef.current!.setMatrixAt(i, dummy.matrix);
    });

    grassRef.current.count = grassPlacements.length;
    grassRef.current.instanceMatrix.needsUpdate = true;
  }, [grassPlacements, dummy]);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    if (grassRef.current) {
      for (let i = 0; i < Math.min(grassPlacements.length, 200); i += 3) {
        const p = grassPlacements[i];
        if (!p) continue;
        dummy.position.copy(p.pos);
        dummy.rotation.y = p.rot + Math.sin(t + i) * 0.1;
        dummy.scale.setScalar(p.scale);
        dummy.updateMatrix();
        grassRef.current.setMatrixAt(i, dummy.matrix);
      }
      if (grassPlacements.length > 0) {
        grassRef.current.instanceMatrix.needsUpdate = true;
      }
    }
  });

  if (!vegetation.enabled) return null;

  return (
    <group>
      <instancedMesh
        ref={treesRef}
        args={[undefined, undefined, Math.max(treePlacements.length, 1)]}
        castShadow
        receiveShadow
      >
        <cylinderGeometry args={[0.3, 0.5, 4, 6]} />
        <meshStandardMaterial color="#5c4033" roughness={1} />
      </instancedMesh>

      <instancedMesh
        ref={leavesRef}
        args={[undefined, undefined, Math.max(treePlacements.length, 1)]}
        castShadow
      >
        <coneGeometry args={[2, 4, 8]} />
        <meshStandardMaterial color="#2d5a27" roughness={0.9} />
      </instancedMesh>

      <instancedMesh
        ref={grassRef}
        args={[undefined, undefined, Math.max(grassPlacements.length, 1)]}
        castShadow
      >
        <coneGeometry args={[0.15, 0.6, 4]} />
        <meshStandardMaterial color="#7cb342" roughness={1} side={THREE.DoubleSide} />
      </instancedMesh>
    </group>
  );
}
