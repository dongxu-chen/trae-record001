import { useRef, useMemo } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useTerrainStore } from '@/store/terrainStore';

export function WaterWithReflection() {
  const waterLevel = useTerrainStore((s) => s.waterLevel);
  const showWater = useTerrainStore((s) => s.showWater);
  const chunkSize = useTerrainStore((s) => s.chunkSize);
  const chunks = useTerrainStore((s) => s.chunks);

  const meshRef = useRef<THREE.Mesh>(null);
  const { scene, gl } = useThree();

  const cubeRenderTarget = useMemo(() => {
    const rt = new THREE.WebGLCubeRenderTarget(512, {
      generateMipmaps: true,
      minFilter: THREE.LinearMipmapLinearFilter,
    });
    return rt;
  }, []);

  const cubeCamera = useMemo(() => {
    const cam = new THREE.CubeCamera(0.1, 10000, cubeRenderTarget);
    return cam;
  }, [cubeRenderTarget]);

  const size = chunkSize * chunks;

  useFrame((state) => {
    if (!meshRef.current || !showWater) return;

    meshRef.current.visible = false;
    cubeCamera.position.set(0, waterLevel, 0);
    cubeCamera.update(gl, scene);
    meshRef.current.visible = true;

    const t = state.clock.elapsedTime * 0.2;
    const mat = meshRef.current.material as THREE.MeshPhysicalMaterial;
    mat.emissiveIntensity = 0.5 + Math.sin(t) * 0.1;
  });

  if (!showWater) return null;

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, waterLevel, 0]} receiveShadow>
      <planeGeometry args={[size, size, 1, 1]} />
      <meshPhysicalMaterial
        color="#0ea5e9"
        envMap={cubeRenderTarget.texture}
        envMapIntensity={0.8}
        transparent
        opacity={0.85}
        roughness={0.1}
        metalness={0.1}
        clearcoat={1}
        clearcoatRoughness={0.1}
        transmission={0.3}
        ior={1.4}
        thickness={2}
      />
    </mesh>
  );
}
