import { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';
import { useEditorStore } from '../store/editorStore';
import type { BoneNode } from '../types/skeleton';
import { traverseBones, updateBoneMatrix } from '../utils/three/SkeletonHelper';

interface TransformCache {
  position: [number, number, number];
  rotation: [number, number, number, number];
  scale: [number, number, number];
}

export function useSkeletonData(model: THREE.Group | null) {
  const boneTransformCacheRef = useRef<Map<string, TransformCache>>(new Map());
  const animationFrameRef = useRef<number | null>(null);
  const isListeningRef = useRef(false);

  const { skeleton, updateBoneTransform } = useEditorStore();

  const extractSkeleton = useCallback((group: THREE.Group): BoneNode[] => {
    const bones: BoneNode[] = [];
    const boneMap = new Map<string, THREE.Bone>();

    group.traverse((obj) => {
      if (obj instanceof THREE.Bone) {
        boneMap.set(obj.uuid, obj);
      }
    });

    let boneIndex = 0;
    boneMap.forEach((bone) => {
      const parentUuid = bone.parent instanceof THREE.Bone ? bone.parent.uuid : null;
      const childrenUuids: string[] = [];
      bone.children.forEach((child) => {
        if (child instanceof THREE.Bone) {
          childrenUuids.push(child.uuid);
        }
      });

      bones.push({
        uuid: bone.uuid,
        name: bone.name,
        parentUuid,
        children: childrenUuids,
        position: [bone.position.x, bone.position.y, bone.position.z],
        rotation: [bone.quaternion.x, bone.quaternion.y, bone.quaternion.z, bone.quaternion.w],
        scale: [bone.scale.x, bone.scale.y, bone.scale.z],
        boneIndex: boneIndex++,
      });
    });

    return bones;
  }, []);

  const initializeTransformCache = useCallback((group: THREE.Group) => {
    boneTransformCacheRef.current.clear();
    const bones = traverseBones(group);

    bones.forEach((bone) => {
      boneTransformCacheRef.current.set(bone.uuid, {
        position: [bone.position.x, bone.position.y, bone.position.z],
        rotation: [bone.quaternion.x, bone.quaternion.y, bone.quaternion.z, bone.quaternion.w],
        scale: [bone.scale.x, bone.scale.y, bone.scale.z],
      });
    });
  }, []);

  const hasTransformChanged = useCallback((bone: THREE.Bone, cache: TransformCache): boolean => {
    const eps = 1e-6;

    if (
      Math.abs(bone.position.x - cache.position[0]) > eps ||
      Math.abs(bone.position.y - cache.position[1]) > eps ||
      Math.abs(bone.position.z - cache.position[2]) > eps
    ) {
      return true;
    }

    if (
      Math.abs(bone.quaternion.x - cache.rotation[0]) > eps ||
      Math.abs(bone.quaternion.y - cache.rotation[1]) > eps ||
      Math.abs(bone.quaternion.z - cache.rotation[2]) > eps ||
      Math.abs(bone.quaternion.w - cache.rotation[3]) > eps
    ) {
      return true;
    }

    if (
      Math.abs(bone.scale.x - cache.scale[0]) > eps ||
      Math.abs(bone.scale.y - cache.scale[1]) > eps ||
      Math.abs(bone.scale.z - cache.scale[2]) > eps
    ) {
      return true;
    }

    return false;
  }, []);

  const updateTransformCache = useCallback((bone: THREE.Bone) => {
    boneTransformCacheRef.current.set(bone.uuid, {
      position: [bone.position.x, bone.position.y, bone.position.z],
      rotation: [bone.quaternion.x, bone.quaternion.y, bone.quaternion.z, bone.quaternion.w],
      scale: [bone.scale.x, bone.scale.y, bone.scale.z],
    });
  }, []);

  const checkAndSyncTransforms = useCallback(() => {
    if (!model) return;

    const bones = traverseBones(model);

    bones.forEach((bone) => {
      const cache = boneTransformCacheRef.current.get(bone.uuid);

      if (!cache) {
        updateTransformCache(bone);
        return;
      }

      if (hasTransformChanged(bone, cache)) {
        updateBoneTransform(bone.uuid, 'position', [bone.position.x, bone.position.y, bone.position.z]);
        updateBoneTransform(bone.uuid, 'rotation', [bone.quaternion.x, bone.quaternion.y, bone.quaternion.z, bone.quaternion.w]);
        updateBoneTransform(bone.uuid, 'scale', [bone.scale.x, bone.scale.y, bone.scale.z]);
        updateTransformCache(bone);
      }
    });
  }, [model, updateBoneTransform, hasTransformChanged, updateTransformCache]);

  useEffect(() => {
    if (!model) return;

    const skeletonData = extractSkeleton(model);
    initializeTransformCache(model);

    useEditorStore.setState({ skeleton: skeletonData });

    isListeningRef.current = true;

    const animate = () => {
      if (isListeningRef.current) {
        checkAndSyncTransforms();
        animationFrameRef.current = requestAnimationFrame(animate);
      }
    };

    animate();

    return () => {
      isListeningRef.current = false;
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [model, extractSkeleton, initializeTransformCache, checkAndSyncTransforms]);

  const getBoneByUuid = useCallback((uuid: string): THREE.Bone | null => {
    if (!model) return null;
    const obj = model.getObjectByProperty('uuid', uuid);
    return obj instanceof THREE.Bone ? obj : null;
  }, [model]);

  const getBoneByName = useCallback((name: string): THREE.Bone | null => {
    if (!model) return null;
    const bones = traverseBones(model);
    return bones.find((b) => b.name === name) || null;
  }, [model]);

  const setBonePosition = useCallback((uuid: string, position: [number, number, number]) => {
    const bone = getBoneByUuid(uuid);
    if (!bone) return;

    bone.position.set(position[0], position[1], position[2]);
    updateBoneMatrix(bone);
    updateBoneTransform(uuid, 'position', position);
    updateTransformCache(bone);
  }, [getBoneByUuid, updateBoneTransform, updateTransformCache]);

  const setBoneRotation = useCallback((uuid: string, rotation: [number, number, number, number]) => {
    const bone = getBoneByUuid(uuid);
    if (!bone) return;

    bone.quaternion.set(rotation[0], rotation[1], rotation[2], rotation[3]);
    updateBoneMatrix(bone);
    updateBoneTransform(uuid, 'rotation', rotation);
    updateTransformCache(bone);
  }, [getBoneByUuid, updateBoneTransform, updateTransformCache]);

  const setBoneScale = useCallback((uuid: string, scale: [number, number, number]) => {
    const bone = getBoneByUuid(uuid);
    if (!bone) return;

    bone.scale.set(scale[0], scale[1], scale[2]);
    updateBoneMatrix(bone);
    updateBoneTransform(uuid, 'scale', scale);
    updateTransformCache(bone);
  }, [getBoneByUuid, updateBoneTransform, updateTransformCache]);

  const getBoneChildren = useCallback((uuid: string): BoneNode[] => {
    const bone = skeleton.find((b) => b.uuid === uuid);
    if (!bone) return [];
    return skeleton.filter((b) => bone.children.includes(b.uuid));
  }, [skeleton]);

  const getRootBones = useCallback((): BoneNode[] => {
    return skeleton.filter((b) => b.parentUuid === null);
  }, [skeleton]);

  const resetBonePose = useCallback((uuid: string) => {
    const bone = getBoneByUuid(uuid);
    if (!bone) return;

    bone.position.set(0, 0, 0);
    bone.quaternion.identity();
    bone.scale.set(1, 1, 1);
    updateBoneMatrix(bone);
    updateBoneTransform(uuid, 'position', [0, 0, 0]);
    updateBoneTransform(uuid, 'rotation', [0, 0, 0, 1]);
    updateBoneTransform(uuid, 'scale', [1, 1, 1]);
    updateTransformCache(bone);
  }, [getBoneByUuid, updateBoneTransform, updateTransformCache]);

  const resetAllBonePoses = useCallback(() => {
    skeleton.forEach((boneNode) => {
      resetBonePose(boneNode.uuid);
    });
  }, [skeleton, resetBonePose]);

  return {
    skeleton,
    getBoneByUuid,
    getBoneByName,
    setBonePosition,
    setBoneRotation,
    setBoneScale,
    getBoneChildren,
    getRootBones,
    resetBonePose,
    resetAllBonePoses,
  };
}
