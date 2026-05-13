import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRM } from '@pixiv/three-vrm';

export class VRMLoader {
  constructor() {
    this.currentVRM = null;
    this.gltfLoader = new GLTFLoader();
    this.gltfLoader.register((parser) => new VRMLoaderPlugin(parser));
  }

  async load(url, onProgress = null) {
    return new Promise((resolve, reject) => {
      this.gltfLoader.load(
        url,
        (gltf) => {
          this.currentVRM = gltf.userData.vrm;
          
          this._postProcessVRM(this.currentVRM);
          
          resolve(this.currentVRM);
        },
        onProgress,
        (error) => {
          console.error('VRM 加载失败:', error);
          reject(error);
        }
      );
    });
  }

  _postProcessVRM(vrm) {
    if (!vrm || !vrm.scene) return;
    
    vrm.scene.traverse((object) => {
      if (object.isSkinnedMesh) {
        this._fixSkinnedMesh(object);
      }
      
      if (object.isMesh) {
        this._fixMeshBindMatrices(object);
      }
    });
    
    if (vrm.humanoid) {
      vrm.humanoid.normalizedHumanBones.forEach((bone) => {
        if (bone?.node?.matrix) {
          bone.node.matrixAutoUpdate = true;
        }
      });
    }
    
    vrm.scene.updateMatrixWorld(true);
  }

  _fixSkinnedMesh(mesh) {
    if (!mesh.skeleton) return;
    
    mesh.bindMode = 'attached';
    mesh.matrixAutoUpdate = true;
    
    if (mesh.skeleton.bones) {
      mesh.skeleton.bones.forEach((bone) => {
        if (bone) {
          bone.matrixAutoUpdate = true;
          bone.updateMatrix();
          bone.updateMatrixWorld(true);
        }
      });
    }
    
    mesh.skeleton.calculateInverses();
    mesh.bind(mesh.skeleton, mesh.bindMatrix);
    
    if (mesh.geometry && mesh.geometry.attributes) {
      if (mesh.geometry.attributes.skinIndex) {
        mesh.geometry.attributes.skinIndex.needsUpdate = true;
      }
      if (mesh.geometry.attributes.skinWeight) {
        mesh.geometry.attributes.skinWeight.needsUpdate = true;
      }
    }
    
    mesh.updateMatrix();
    mesh.updateMatrixWorld(true);
  }

  _fixMeshBindMatrices(mesh) {
    if (!mesh.geometry || !mesh.skeleton) return;
    
    if (!mesh.bindMatrix) {
      mesh.bindMatrix = new THREE.Matrix4().identity();
    }
    
    if (!mesh.bindMatrixInverse) {
      mesh.bindMatrixInverse = new THREE.Matrix4().copy(mesh.bindMatrix).invert();
    }
    
    mesh.bindMatrix.decompose(
      mesh.position,
      mesh.quaternion,
      mesh.scale
    );
    
    mesh.updateMatrix();
  }

  getVRM() {
    return this.currentVRM;
  }

  getScene() {
    return this.currentVRM?.scene;
  }

  getSkeletonByMesh(meshName) {
    if (!this.currentVRM?.scene) return null;
    
    let skeleton = null;
    this.currentVRM.scene.traverse((object) => {
      if (object.name === meshName && object.isSkinnedMesh) {
        skeleton = object.skeleton;
      }
    });
    
    return skeleton;
  }

  getBoneByName(boneName) {
    if (!this.currentVRM?.humanoid) return null;
    
    const bones = this.currentVRM.humanoid.normalizedHumanBones;
    for (const bone of bones) {
      if (bone?.node?.name === boneName) {
        return bone.node;
      }
    }
    
    if (this.currentVRM.scene) {
      let found = null;
      this.currentVRM.scene.traverse((object) => {
        if (object.name === boneName && object.isBone) {
          found = object;
        }
      });
      return found;
    }
    
    return null;
  }

  getAllBones() {
    const bones = [];
    
    if (this.currentVRM?.scene) {
      this.currentVRM.scene.traverse((object) => {
        if (object.isBone) {
          bones.push({
            name: object.name,
            bone: object
          });
        }
      });
    }
    
    return bones;
  }

  dispose() {
    if (this.currentVRM) {
      this.currentVRM.dispose();
      this.currentVRM = null;
    }
  }
}

export default VRMLoader;
