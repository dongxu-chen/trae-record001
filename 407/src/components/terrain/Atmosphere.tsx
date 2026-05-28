import { Sky, Stars, OrbitControls } from '@react-three/drei';
import { useTerrainStore } from '@/store/terrainStore';

export function Atmosphere() {
  const autoRotate = useTerrainStore((s) => s.autoRotate);
  return (
    <>
      <Sky
        distance={450000}
        sunPosition={[100, 80, 100]}
        inclination={0.5}
        azimuth={0.25}
        rayleigh={0.5}
        turbidity={10}
        mieCoefficient={0.005}
        mieDirectionalG={0.8}
      />
      <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
      <fog attach="fog" args={['#87ceeb', 500, 2500]} />
      <ambientLight intensity={0.35} />
      <directionalLight
        position={[200, 300, 200]}
        intensity={1.4}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-far={1500}
        shadow-camera-left={-500}
        shadow-camera-right={500}
        shadow-camera-top={500}
        shadow-camera-bottom={-500}
        shadow-bias={-0.0001}
      />
      <hemisphereLight color="#87ceeb" groundColor="#3d5c2e" intensity={0.6} />
      <OrbitControls
        enablePan
        enableZoom
        enableRotate
        maxPolarAngle={Math.PI / 2.1}
        minDistance={50}
        maxDistance={1500}
        autoRotate={autoRotate}
        autoRotateSpeed={0.3}
      />
    </>
  );
}
