import * as THREE from 'three';

export interface BoneInfo {
  bone: THREE.Bone;
  name: string;
  index: number;
  parentIndex: number;
  children: number[];
  worldPosition: THREE.Vector3;
  worldRotation: THREE.Quaternion;
  worldScale: THREE.Vector3;
  localPosition: THREE.Vector3;
  localRotation: THREE.Quaternion;
  localScale: THREE.Vector3;
}

export function traverseBones(root: THREE.Object3D): THREE.Bone[] {
  const bones: THREE.Bone[] = [];

  root.traverse((child) => {
    if (child instanceof THREE.Bone) {
      bones.push(child);
    }
  });

  return bones;
}

export function traverseBonesWithCallback(
  root: THREE.Object3D,
  callback: (bone: THREE.Bone, parent: THREE.Bone | null, depth: number) => void
): void {
  function traverse(node: THREE.Object3D, parent: THREE.Bone | null, depth: number): void {
    if (node instanceof THREE.Bone) {
      callback(node, parent, depth);
    }

    for (const child of node.children) {
      traverse(child, node instanceof THREE.Bone ? node : parent, depth + 1);
    }
  }

  traverse(root, null, 0);
}

export function getBoneWorldPosition(bone: THREE.Bone): THREE.Vector3 {
  bone.updateMatrixWorld(true);
  const position = new THREE.Vector3();
  position.setFromMatrixPosition(bone.matrixWorld);
  return position;
}

export function getBoneWorldRotation(bone: THREE.Bone): THREE.Quaternion {
  bone.updateMatrixWorld(true);
  const rotation = new THREE.Quaternion();
  rotation.setFromRotationMatrix(bone.matrixWorld);
  return rotation;
}

export function getBoneWorldScale(bone: THREE.Bone): THREE.Vector3 {
  bone.updateMatrixWorld(true);
  const scale = new THREE.Vector3();
  scale.setFromMatrixScale(bone.matrixWorld);
  return scale;
}

export function updateBoneMatrix(bone: THREE.Bone): void {
  bone.updateMatrix();
  bone.updateMatrixWorld(true);
}

export function updateSkeletonMatrices(skeleton: THREE.Skeleton): void {
  skeleton.bones.forEach((bone) => {
    updateBoneMatrix(bone);
  });
}

export function getBoneHierarchy(root: THREE.Object3D): Map<string, BoneInfo> {
  const boneMap = new Map<string, BoneInfo>();
  const bones = traverseBones(root);
  const nameToIndex = new Map<string, number>();

  bones.forEach((bone, index) => {
    nameToIndex.set(bone.name, index);
  });

  bones.forEach((bone, index) => {
    const parent = bone.parent;
    const parentIndex = parent instanceof THREE.Bone ? nameToIndex.get(parent.name) ?? -1 : -1;

    const children: number[] = [];
    bone.children.forEach((child) => {
      if (child instanceof THREE.Bone) {
        const childIndex = nameToIndex.get(child.name);
        if (childIndex !== undefined) {
          children.push(childIndex);
        }
      }
    });

    bone.updateMatrixWorld(true);

    boneMap.set(bone.name, {
      bone,
      name: bone.name,
      index,
      parentIndex,
      children,
      worldPosition: getBoneWorldPosition(bone),
      worldRotation: getBoneWorldRotation(bone),
      worldScale: getBoneWorldScale(bone),
      localPosition: bone.position.clone(),
      localRotation: bone.quaternion.clone(),
      localScale: bone.scale.clone(),
    });
  });

  return boneMap;
}

export function getRootBones(bones: THREE.Bone[]): THREE.Bone[] {
  return bones.filter((bone) => !(bone.parent instanceof THREE.Bone));
}

export function getBoneChildren(bone: THREE.Bone): THREE.Bone[] {
  return bone.children.filter((child) => child instanceof THREE.Bone) as THREE.Bone[];
}

export function getBoneByName(root: THREE.Object3D, name: string): THREE.Bone | null {
  const bones = traverseBones(root);
  return bones.find((b) => b.name === name) || null;
}

export function setBoneWorldPosition(bone: THREE.Bone, position: THREE.Vector3): void {
  const parent = bone.parent;
  if (parent) {
    parent.updateMatrixWorld(true);
    const inverseParent = new THREE.Matrix4().copy(parent.matrixWorld).invert();
    const localPosition = position.clone().applyMatrix4(inverseParent);
    bone.position.copy(localPosition);
  } else {
    bone.position.copy(position);
  }
  updateBoneMatrix(bone);
}

export function setBoneWorldRotation(bone: THREE.Bone, rotation: THREE.Quaternion): void {
  const parent = bone.parent;
  if (parent) {
    parent.updateMatrixWorld(true);
    const parentRotation = new THREE.Quaternion().setFromRotationMatrix(parent.matrixWorld);
    const inverseParent = parentRotation.clone().invert();
    const localRotation = inverseParent.multiply(rotation);
    bone.quaternion.copy(localRotation);
  } else {
    bone.quaternion.copy(rotation);
  }
  updateBoneMatrix(bone);
}

export function computeBoneLength(bone: THREE.Bone): number {
  const children = getBoneChildren(bone);
  if (children.length === 0) {
    return 0;
  }

  bone.updateMatrixWorld(true);
  const startPos = getBoneWorldPosition(bone);
  const endPos = getBoneWorldPosition(children[0]);

  return startPos.distanceTo(endPos);
}

export function createBoneMap(bones: THREE.Bone[]): Map<string, THREE.Bone> {
  const map = new Map<string, THREE.Bone>();
  bones.forEach((bone) => {
    map.set(bone.name, bone);
  });
  return map;
}

export function resetBonePose(bone: THREE.Bone): void {
  bone.position.set(0, 0, 0);
  bone.quaternion.identity();
  bone.scale.set(1, 1, 1);
  updateBoneMatrix(bone);
}

export function resetAllBonePoses(root: THREE.Object3D): void {
  const bones = traverseBones(root);
  bones.forEach((bone) => resetBonePose(bone));
}
