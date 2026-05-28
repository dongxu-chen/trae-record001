import { Canvas } from '@react-three/fiber';
import { Suspense } from 'react';
import { TerrainLOD } from './TerrainLOD';
import { WaterWithReflection } from './WaterWithReflection';
import { Atmosphere } from './Atmosphere';
import { Vegetation } from './Vegetation';

export function TerrainScene() {
  return (
    <Canvas
      shadows
      gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }}
      camera={{ position: [300, 250, 300], fov: 55, near: 1, far: 10000 }}
      dpr={[1, 2]}
    >
      <Suspense fallback={null}>
        <Atmosphere />
        <TerrainLOD />
        <Vegetation />
        <WaterWithReflection />
      </Suspense>
    </Canvas>
  );
}
