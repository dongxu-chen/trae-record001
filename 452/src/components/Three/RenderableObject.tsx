import { useRef, useMemo, useEffect } from 'react';
import { useThree, ThreeEvent, useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import type { SceneObject } from '../../types/scene';
import { useSceneStore } from '../../store/useSceneStore';

interface RenderableObjectProps {
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

export function RenderableObject({ object }: RenderableObjectProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const { selectObject, selectedObjectId } = useSceneStore();

  const isSelected = selectedObjectId === object.id;

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    selectObject(object.id);
  };

  if (object.type === 'gltf' && object.gltfUrl) {
    return <GLTFObject url={object.gltfUrl} object={object} />;
  }

  return (
    <mesh
      ref={meshRef}
      position={object.position}
      rotation={object.rotation as unknown as THREE.Euler}
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
  );
}

function GLTFObject({ url, object }: { url: string; object: SceneObject }) {
  const { scene: gltfScene, animations } = useGLTF(url);
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
    mixer.timeScale = object.animation.timeScale;

    if (object.animation.enabled && object.animation.isPlaying) {
      let clip: THREE.AnimationClip | undefined;

      if (object.animation.currentClip) {
        clip = animations.find((a) => a.name === object.animation.currentClip);
      }

      if (!clip && animations.length > 0) {
        clip = animations[0];
      }

      if (clip) {
        let targetClip = clip;

        const customClip = object.animation.clips.find(
          (c) => c.name === object.animation.currentClip
        );
        if (customClip) {
          targetClip = clip.clone();
          targetClip = THREE.AnimationUtils.subclip(
            targetClip,
            customClip.name,
            Math.floor(customClip.start * 30),
            Math.floor(customClip.end * 30)
          );
        }

        const action = mixer.clipAction(targetClip);
        action.setLoop(object.animation.clips.find((c) => c.name === object.animation.currentClip)?.loop !== false ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
        action.reset().play();
      }
    }

    return () => {
      mixer.stopAllAction();
      mixerRef.current = null;
    };
  }, [animations, object.animation]);

  useFrame((_, delta) => {
    if (mixerRef.current) {
      mixerRef.current.update(delta);
    }
  });

  return (
    <group
      ref={groupRef}
      position={object.position}
      rotation={object.rotation as unknown as THREE.Euler}
      scale={object.scale}
      onClick={handleClick}
      userData={{ id: object.id }}
    >
      <primitive object={gltfScene.clone()} />
    </group>
  );
}

useGLTF.preload('https://threejs.org/examples/models/gltf/DamagedHelmet/glTF/DamagedHelmet.gltf');
