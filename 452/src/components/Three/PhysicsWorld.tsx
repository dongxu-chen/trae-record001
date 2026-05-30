import { RigidBody, CuboidCollider, BallCollider, Physics } from '@react-three/rapier';
import type { SceneObject } from '../../types/scene';
import { useSceneStore } from '../../store/useSceneStore';
import * as THREE from 'three';
import { useRef, useMemo, useEffect } from 'react';
import { useThree, ThreeEvent } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';

interface PhysicsObjectProps {
  object: SceneObject;
}

function NormalMapMaterial({ object }: { object: SceneObject }) {
  const { showNormalMaps } = useSceneStore();
  const matRef = useRef<THREE.MeshStandardMaterial>(null);

  const normalMap = useMemo(() => {
    if (!object.material.normalMapUrl || !showNormalMaps) return null;
    try {
      const loader = new THREE.TextureLoader();
      const tex = loader.load(object.material.normalMapUrl);
      tex.wrapS = THREE.RepeatWrapping;
      tex.wrapT = THREE.RepeatWrapping;
      return tex;
    } catch {
      return null;
    }
  }, [object.material.normalMapUrl, showNormalMaps]);

  useEffect(() => {
    if (matRef.current) {
      matRef.current.normalMap = normalMap;
      matRef.current.normalScale = new THREE.Vector2(
        object.material.normalScale,
        object.material.normalScale
      );
      matRef.current.needsUpdate = true;
    }
  }, [normalMap, object.material.normalScale]);

  return (
    <meshStandardMaterial
      ref={matRef}
      color={object.material.color}
      metalness={object.material.metalness}
      roughness={object.material.roughness}
      emissive={object.material.emissive}
      emissiveIntensity={object.material.emissiveIntensity}
    />
  );
}

function PhysicsMesh({ object }: PhysicsObjectProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const { selectObject, selectedObjectId } = useSceneStore();

  const isSelected = selectedObjectId === object.id;
  const physics = object.physics;

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    selectObject(object.id);
  };

  return (
    <RigidBody
      type={physics.enabled ? physics.bodyType : 'fixed'}
      position={object.position}
      rotation={object.rotation as unknown as THREE.Euler}
      mass={physics.mass}
      restitution={physics.restitution}
      friction={physics.friction}
      linearDamping={physics.linearDamping}
      angularDamping={physics.angularDamping}
      colliders={false}
      enabled={physics.enabled}
    >
      {object.type === 'box' && (
        <CuboidCollider args={[object.scale[0] / 2, object.scale[1] / 2, object.scale[2] / 2]} />
      )}
      {object.type === 'sphere' && <BallCollider args={[0.5 * object.scale[0]]} />}

      <mesh
        ref={meshRef}
        scale={object.scale}
        onClick={handleClick}
        userData={{ id: object.id }}
        castShadow
        receiveShadow
      >
        {object.type === 'box' && <boxGeometry args={[1, 1, 1]} />}
        {object.type === 'sphere' && <sphereGeometry args={[0.5, 32, 32]} />}
        <NormalMapMaterial object={object} />

        {isSelected && (
          <lineSegments>
            <edgesGeometry args={[meshRef.current?.geometry]} />
            <lineBasicMaterial color="#00d4ff" linewidth={2} />
          </lineSegments>
        )}
      </mesh>
    </RigidBody>
  );
}

function PhysicsGLTFObject({ object }: { object: SceneObject }) {
  const { scene: gltfScene, animations } = useGLTF(object.gltfUrl!);
  const groupRef = useRef<THREE.Group>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const { selectObject, selectedObjectId, showNormalMaps } = useSceneStore();

  const isSelected = selectedObjectId === object.id;

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    selectObject(object.id);
  };

  useEffect(() => {
    if (!groupRef.current) return;
    groupRef.current.traverse((child) => {
      if (child instanceof THREE.Mesh && child.material) {
        const materials = Array.isArray(child.material)
          ? child.material
          : [child.material];
        materials.forEach((mat) => {
          if (mat instanceof THREE.MeshStandardMaterial) {
            mat.normalMap = showNormalMaps ? mat.normalMap : null;
            mat.needsUpdate = true;
          }
        });
      }
    });
  }, [showNormalMaps]);

  useEffect(() => {
    if (!animations.length || !groupRef.current) return;

    const mixer = new THREE.AnimationMixer(groupRef.current);
    mixerRef.current = mixer;

    if (object.animation.enabled && object.animation.currentClip) {
      const clip = animations.find((a) => a.name === object.animation.currentClip);
      if (clip) {
        const action = mixer.clipAction(clip);
        action.play();
      }
    } else if (object.animation.enabled && animations.length > 0) {
      const action = mixer.clipAction(animations[0]);
      action.play();
    }

    return () => {
      mixer.stopAllAction();
      mixerRef.current = null;
    };
  }, [animations, object.animation.enabled, object.animation.currentClip]);

  const physics = object.physics;

  return (
    <RigidBody
      type={physics.enabled ? physics.bodyType : 'fixed'}
      position={object.position}
      rotation={object.rotation as unknown as THREE.Euler}
      mass={physics.mass}
      restitution={physics.restitution}
      friction={physics.friction}
      linearDamping={physics.linearDamping}
      angularDamping={physics.angularDamping}
      colliders="trimesh"
      enabled={physics.enabled}
    >
      <group
        ref={groupRef}
        scale={object.scale}
        onClick={handleClick}
        userData={{ id: object.id }}
      >
        <primitive object={gltfScene.clone()} />
      </group>
    </RigidBody>
  );
}

export function PhysicsObject({ object }: PhysicsObjectProps) {
  if (object.type === 'gltf' && object.gltfUrl) {
    return <PhysicsGLTFObject object={object} />;
  }
  return <PhysicsMesh object={object} />;
}

interface PhysicsWorldProps {
  children: React.ReactNode;
}

export function PhysicsWorld({ children }: PhysicsWorldProps) {
  const { physicsEnabled, gravity } = useSceneStore();

  return (
    <Physics gravity={gravity} paused={!physicsEnabled}>
      {children}
      <RigidBody type="fixed" position={[0, -0.5, 0]}>
        <CuboidCollider args={[50, 0.5, 50]} />
        <mesh receiveShadow visible={physicsEnabled}>
          <boxGeometry args={[100, 1, 100]} />
          <meshStandardMaterial color="#2a2a4a" transparent opacity={0.3} />
        </mesh>
      </RigidBody>
    </Physics>
  );
}
