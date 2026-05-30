import { useRef, useEffect } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';
import { useSceneStore } from '../../store/useSceneStore';
import { RenderableObject } from './RenderableObject';
import { PhysicsObject, PhysicsWorld } from './PhysicsWorld';
import { Lights } from './Lights';
import { Gizmo } from './Gizmo';
import type { ViewMode, CameraPreset } from '../../types/scene';

const CAMERA_PRESETS: Record<ViewMode, CameraPreset> = {
  perspective: { position: [5, 5, 5], target: [0, 0, 0] },
  front: { position: [0, 0, 10], target: [0, 0, 0] },
  top: { position: [0, 10, 0.001], target: [0, 0, 0] },
  side: { position: [10, 0, 0], target: [0, 0, 0] },
};

const LERP_SPEED = 0.04;

function CameraAnimator({ viewMode }: { viewMode: ViewMode }) {
  const { camera } = useThree();
  const controlsRef = useRef<any>(null);
  const animating = useRef(false);
  const targetPosition = useRef(new THREE.Vector3());
  const targetLookAt = useRef(new THREE.Vector3());

  useEffect(() => {
    const preset = CAMERA_PRESETS[viewMode];
    targetPosition.current.set(...preset.position);
    targetLookAt.current.set(...preset.target);
    animating.current = true;
  }, [viewMode]);

  useFrame(() => {
    if (!animating.current) return;

    camera.position.lerp(targetPosition.current, LERP_SPEED);

    if (controlsRef.current) {
      controlsRef.current.target.lerp(targetLookAt.current, LERP_SPEED);
      controlsRef.current.update();
    }

    const posDist = camera.position.distanceTo(targetPosition.current);
    const targetDist = controlsRef.current
      ? controlsRef.current.target.distanceTo(targetLookAt.current)
      : 0;

    if (posDist < 0.01 && targetDist < 0.01) {
      camera.position.copy(targetPosition.current);
      if (controlsRef.current) {
        controlsRef.current.target.copy(targetLookAt.current);
        controlsRef.current.update();
      }
      animating.current = false;
    }
  });

  return <OrbitControls ref={controlsRef} makeDefault enableDamping dampingFactor={0.08} />;
}

function SceneContent({ viewMode }: { viewMode: ViewMode }) {
  const { objects, selectedObjectId, transformMode, selectObject, backgroundColor, fog, physicsEnabled } = useSceneStore();
  const { scene } = useThree();

  useEffect(() => {
    scene.background = new THREE.Color(backgroundColor);
    if (fog.enabled) {
      scene.fog = new THREE.Fog(fog.color, fog.near, fog.far);
    } else {
      scene.fog = null;
    }
  }, [backgroundColor, fog, scene]);

  const hasPhysicsObjects = objects.some((obj) => obj.physics.enabled);

  const objectRenderer = hasPhysicsObjects || physicsEnabled ? (
    <PhysicsWorld>
      {objects.map((object) => (
        <PhysicsObject key={object.id} object={object} />
      ))}
    </PhysicsWorld>
  ) : (
    <>
      {objects.map((object) => (
        <RenderableObject key={object.id} object={object} />
      ))}
    </>
  );

  return (
    <>
      <PerspectiveCamera makeDefault position={[5, 5, 5]} fov={50} />
      <CameraAnimator viewMode={viewMode} />

      <Lights />

      <Grid
        infiniteGrid
        cellSize={1}
        cellThickness={0.5}
        cellColor="#4a4a6a"
        sectionSize={5}
        sectionThickness={1}
        sectionColor="#6a6a8a"
        fadeDistance={30}
        fadeStrength={1}
        followCamera={false}
        maxDistance={100}
      />

      {objectRenderer}

      {!physicsEnabled && <Gizmo objectId={selectedObjectId} mode={transformMode} />}
    </>
  );
}

interface SceneProps {
  className?: string;
  onSceneReady?: (scene: THREE.Scene) => void;
}

export function Scene({ className, onSceneReady }: SceneProps) {
  const { viewMode } = useSceneStore();

  return (
    <Canvas
      className={className}
      shadows
      gl={{ antialias: true, preserveDrawingBuffer: true }}
      onPointerMissed={() => useSceneStore.getState().selectObject(null)}
      onCreated={({ scene }) => {
        onSceneReady?.(scene);
      }}
    >
      <SceneContent viewMode={viewMode} />
    </Canvas>
  );
}
