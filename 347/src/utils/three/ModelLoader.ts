import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

export interface LoadedModel {
  scene: THREE.Group;
  animations: THREE.AnimationClip[];
  skeleton?: THREE.Skeleton;
  bones: THREE.Bone[];
  type: 'fbx' | 'gltf' | 'glb';
}

export class ModelLoader {
  private fbxLoader: FBXLoader;
  private gltfLoader: GLTFLoader;
  private dracoLoader: DRACOLoader;

  constructor() {
    this.fbxLoader = new FBXLoader();
    this.gltfLoader = new GLTFLoader();
    this.dracoLoader = new DRACOLoader();
    this.dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');
    this.gltfLoader.setDRACOLoader(this.dracoLoader);
  }

  async loadFromFile(file: File): Promise<LoadedModel> {
    const ext = file.name.split('.').pop()?.toLowerCase();

    if (ext === 'fbx') {
      return this.loadFBX(file);
    } else if (ext === 'gltf' || ext === 'glb') {
      return this.loadGLTF(file);
    } else {
      throw new Error(`Unsupported file format: ${ext}`);
    }
  }

  private async loadFBX(file: File): Promise<LoadedModel> {
    const arrayBuffer = await file.arrayBuffer();
    const buffer = new Uint8Array(arrayBuffer);

    const group = this.fbxLoader.parse(buffer.buffer, '');
    const bones = this.extractBones(group);
    const skeleton = this.createSkeletonFromBones(bones);

    return {
      scene: group,
      animations: group.animations || [],
      skeleton,
      bones,
      type: 'fbx',
    };
  }

  private async loadGLTF(file: File): Promise<LoadedModel> {
    const arrayBuffer = await file.arrayBuffer();
    const buffer = new Uint8Array(arrayBuffer);

    const gltf = await this.gltfLoader.parseAsync(buffer.buffer, '');
    const scene = gltf.scene || gltf.scenes[0];
    const bones = this.extractBones(scene);
    const skeleton = this.createSkeletonFromBones(bones);

    return {
      scene,
      animations: gltf.animations || [],
      skeleton,
      bones,
      type: file.name.toLowerCase().endsWith('.glb') ? 'glb' : 'gltf',
    };
  }

  private extractBones(root: THREE.Object3D): THREE.Bone[] {
    const bones: THREE.Bone[] = [];

    root.traverse((child) => {
      if (child instanceof THREE.Bone) {
        bones.push(child);
      }
    });

    return bones;
  }

  private createSkeletonFromBones(bones: THREE.Bone[]): THREE.Skeleton | undefined {
    if (bones.length === 0) return undefined;

    const boneInverses: THREE.Matrix4[] = [];

    bones.forEach((bone) => {
      bone.updateMatrixWorld(true);
      const inverse = new THREE.Matrix4().copy(bone.matrixWorld).invert();
      boneInverses.push(inverse);
    });

    return new THREE.Skeleton(bones, boneInverses);
  }

  dispose(): void {
    this.dracoLoader.dispose();
  }
}

export function getSkeletonFromModel(model: LoadedModel): THREE.Skeleton | undefined {
  if (model.skeleton) return model.skeleton;

  const bones: THREE.Bone[] = [];
  model.scene.traverse((child) => {
    if (child instanceof THREE.Bone) {
      bones.push(child);
    }
  });

  if (bones.length === 0) return undefined;

  const boneInverses = bones.map((bone) => {
    bone.updateMatrixWorld(true);
    return new THREE.Matrix4().copy(bone.matrixWorld).invert();
  });

  return new THREE.Skeleton(bones, boneInverses);
}

export function getAnimationByName(
  animations: THREE.AnimationClip[],
  name: string
): THREE.AnimationClip | undefined {
  return animations.find((anim) => anim.name === name);
}
