import { useRef, useEffect } from 'react';
import { useThree } from '@react-three/fiber';
import { TransformControls } from '@react-three/drei';
import * as THREE from 'three';
import { useSceneStore } from '../../store/useSceneStore';
import type { TransformMode } from '../../types/scene';

interface GizmoProps {
  objectId: string | null;
  mode: TransformMode;
}

export function Gizmo({ objectId, mode }: GizmoProps) {
  const { scene } = useThree();
  const groupRef = useRef<THREE.Group>(null);
  const { objects, updateObject } = useSceneStore();

  const selectedObject = objects.find((obj) => obj.id === objectId);

  useEffect(() => {
    if (groupRef.current && selectedObject) {
      groupRef.current.position.set(...selectedObject.position);
      groupRef.current.rotation.set(...selectedObject.rotation);
      groupRef.current.scale.set(...selectedObject.scale);
    }
  }, [selectedObject]);

  if (!objectId || !selectedObject) {
    return null;
  }

  const handleTransform = () => {
    if (groupRef.current) {
      updateObject(objectId, {
        position: [groupRef.current.position.x, groupRef.current.position.y, groupRef.current.position.z],
        rotation: [groupRef.current.rotation.x, groupRef.current.rotation.y, groupRef.current.rotation.z],
        scale: [groupRef.current.scale.x, groupRef.current.scale.y, groupRef.current.scale.z],
      });
    }
  };

  return (
    <TransformControls
      mode={mode}
      onObjectChange={handleTransform}
      position={selectedObject.position}
    >
      <group ref={groupRef}>
        <mesh position={[0, 0, 0]} visible={false}>
          <boxGeometry args={[0.1, 0.1, 0.1]} />
          <meshBasicMaterial transparent opacity={0} />
        </mesh>
      </group>
    </TransformControls>
  );
}
