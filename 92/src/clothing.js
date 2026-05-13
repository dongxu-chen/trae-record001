import * as THREE from 'three';

export class ClothingSystem {
  constructor(vrm = null) {
    this.vrm = vrm;
    this.materials = new Map();
    this.originalMaterials = new Map();
    this.clothingItems = new Map();
    this.activeClothing = new Map();
    this.skinningCache = new Map();
    
    if (this.vrm) {
      this._initialize();
    }
  }

  setVRM(vrm) {
    this.vrm = vrm;
    this._initialize();
  }

  _initialize() {
    if (!this.vrm?.scene) return;
    
    this.materials.clear();
    this.originalMaterials.clear();
    this.skinningCache.clear();
    
    this.vrm.scene.traverse((object) => {
      if (object.isMesh) {
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        
        materials.forEach((mat, index) => {
          if (mat) {
            const key = `${object.uuid}_${index}`;
            this.materials.set(key, {
              mesh: object,
              materialIndex: index,
              material: mat,
              name: mat.name || `material_${this.materials.size}`
            });
            
            this.originalMaterials.set(key, mat.clone());
          }
        });
        
        if (object.isSkinnedMesh) {
          this._cacheSkinning(object);
        }
      }
    });
  }

  _cacheSkinning(mesh) {
    if (!mesh.isSkinnedMesh) return;
    
    this.skinningCache.set(mesh.uuid, {
      skeleton: mesh.skeleton,
      bindMatrix: mesh.bindMatrix ? mesh.bindMatrix.clone() : new THREE.Matrix4().identity(),
      bindMatrixInverse: mesh.bindMatrixInverse ? mesh.bindMatrixInverse.clone() : new THREE.Matrix4().identity(),
      skinIndices: mesh.geometry?.attributes?.skinIndex,
      skinWeights: mesh.geometry?.attributes?.skinWeight,
      bindMode: mesh.bindMode,
      bones: mesh.skeleton?.bones ? [...mesh.skeleton.bones] : []
    });
  }

  _restoreSkinning(mesh) {
    const cache = this.skinningCache.get(mesh.uuid);
    if (!cache) return false;
    
    mesh.bindMode = cache.bindMode;
    
    if (cache.skeleton) {
      mesh.bind(cache.skeleton, cache.bindMatrix);
    }
    
    mesh.bindMatrix = cache.bindMatrix.clone();
    mesh.bindMatrixInverse = cache.bindMatrixInverse.clone();
    
    if (mesh.geometry) {
      if (cache.skinIndices) {
        mesh.geometry.setAttribute('skinIndex', cache.skinIndices);
      }
      if (cache.skinWeights) {
        mesh.geometry.setAttribute('skinWeight', cache.skinWeights);
      }
    }
    
    mesh.updateMatrix();
    mesh.updateMatrixWorld(true);
    
    return true;
  }

  _rebindSkinnedMesh(targetMesh, sourceSkeleton) {
    if (!targetMesh.isSkinnedMesh || !sourceSkeleton) return false;
    
    const boneMap = new Map();
    sourceSkeleton.bones.forEach((bone) => {
      boneMap.set(bone.name, bone);
    });
    
    const newBones = [];
    if (targetMesh.skeleton?.bones) {
      targetMesh.skeleton.bones.forEach((bone) => {
        if (boneMap.has(bone.name)) {
          newBones.push(boneMap.get(bone.name));
        } else {
          const closestBone = this._findClosestBone(bone.name, boneMap);
          newBones.push(closestBone || bone);
        }
      });
    }
    
    const newSkeleton = new THREE.Skeleton(
      newBones.length > 0 ? newBones : sourceSkeleton.bones,
      sourceSkeleton.boneInverses
    );
    
    const bindMatrix = targetMesh.bindMatrix || new THREE.Matrix4().identity();
    targetMesh.bind(newSkeleton, bindMatrix);
    
    targetMesh.updateMatrix();
    targetMesh.updateMatrixWorld(true);
    
    return true;
  }

  _findClosestBone(boneName, boneMap) {
    for (const [name, bone] of boneMap) {
      if (name.includes(boneName) || boneName.includes(name)) {
        return bone;
      }
    }
    
    let bestMatch = null;
    let bestScore = 0;
    
    for (const [name, bone] of boneMap) {
      const score = this._stringSimilarity(boneName, name);
      if (score > bestScore && score > 0.5) {
        bestScore = score;
        bestMatch = bone;
      }
    }
    
    return bestMatch;
  }

  _stringSimilarity(str1, str2) {
    const s1 = str1.toLowerCase();
    const s2 = str2.toLowerCase();
    
    if (s1 === s2) return 1;
    if (s1.length === 0 || s2.length === 0) return 0;
    
    let matches = 0;
    const maxLen = Math.max(s1.length, s2.length);
    
    for (let i = 0; i < Math.min(s1.length, s2.length); i++) {
      if (s1[i] === s2[i]) matches++;
    }
    
    return matches / maxLen;
  }

  _cloneWithSkinning(sourceMesh, targetSkeleton) {
    const clone = sourceMesh.clone(false);
    clone.geometry = sourceMesh.geometry.clone();
    
    if (sourceMesh.isSkinnedMesh) {
      if (targetSkeleton) {
        if (sourceMesh.skeleton) {
          this._rebindSkinnedMesh(clone, targetSkeleton);
        } else {
          const newSkeleton = new THREE.Skeleton(targetSkeleton.bones);
          clone.bind(newSkeleton, sourceMesh.bindMatrix || new THREE.Matrix4().identity());
        }
      }
      
      clone.bindMode = sourceMesh.bindMode || 'attached';
    }
    
    if (Array.isArray(sourceMesh.material)) {
      clone.material = sourceMesh.material.map(m => m.clone());
    } else if (sourceMesh.material) {
      clone.material = sourceMesh.material.clone();
    }
    
    clone.updateMatrix();
    clone.updateMatrixWorld(true);
    
    return clone;
  }

  getAllMaterials() {
    const result = [];
    this.materials.forEach((data, key) => {
      result.push({
        key,
        name: data.name,
        meshName: data.mesh.name
      });
    });
    return result;
  }

  getMaterialByKey(key) {
    return this.materials.get(key);
  }

  changeMaterialColor(materialKey, color) {
    const data = this.materials.get(materialKey);
    if (!data) return false;
    
    const threeColor = new THREE.Color(color);
    
    if (data.material.color) {
      data.material.color.copy(threeColor);
    } else if (data.material.baseColorFactor) {
      data.material.baseColorFactor = [
        threeColor.r,
        threeColor.g,
        threeColor.b,
        data.material.baseColorFactor?.[3] ?? 1
      ];
    }
    
    return true;
  }

  changeMaterialOpacity(materialKey, opacity) {
    const data = this.materials.get(materialKey);
    if (!data) return false;
    
    opacity = THREE.MathUtils.clamp(opacity, 0, 1);
    
    if (opacity < 1) {
      data.material.transparent = true;
    }
    
    if (data.material.opacity !== undefined) {
      data.material.opacity = opacity;
    } else if (data.material.baseColorFactor) {
      data.material.baseColorFactor[3] = opacity;
    }
    
    if (opacity >= 1 && data.material.opacity !== undefined) {
      data.material.transparent = false;
    }
    
    return true;
  }

  changeMaterialTexture(materialKey, textureUrl, textureType = 'map') {
    return new Promise((resolve, reject) => {
      const data = this.materials.get(materialKey);
      if (!data) {
        reject(new Error('Material not found'));
        return;
      }
      
      const loader = new THREE.TextureLoader();
      loader.load(
        textureUrl,
        (texture) => {
          texture.flipY = false;
          texture.colorSpace = THREE.SRGBColorSpace;
          
          if (data.material[textureType] !== undefined) {
            if (data.material[textureType]) {
              data.material[textureType].dispose();
            }
            data.material[textureType] = texture;
            data.material.needsUpdate = true;
          }
          
          resolve(texture);
        },
        undefined,
        (error) => {
          reject(error);
        }
      );
    });
  }

  createPresetMaterial(presetName, options = {}) {
    const material = new THREE.MeshStandardMaterial({
      color: options.color ?? 0xffffff,
      metalness: options.metalness ?? 0,
      roughness: options.roughness ?? 0.5,
      transparent: options.transparent ?? false,
      opacity: options.opacity ?? 1,
      emissive: options.emissive ?? 0x000000,
      emissiveIntensity: options.emissiveIntensity ?? 0
    });
    
    this.clothingItems.set(presetName, {
      type: 'material',
      material,
      options
    });
    
    return material;
  }

  applyPresetMaterial(materialKey, presetName) {
    const item = this.clothingItems.get(presetName);
    if (!item || item.type !== 'material') return false;
    
    const data = this.materials.get(materialKey);
    if (!data) return false;
    
    const newMaterial = item.material.clone();
    
    if (Array.isArray(data.mesh.material)) {
      data.mesh.material[data.materialIndex] = newMaterial;
    } else {
      data.mesh.material = newMaterial;
    }
    
    data.material = newMaterial;
    this.materials.set(materialKey, data);
    
    return true;
  }

  replaceMeshGeometry(targetMeshName, newGeometry, preserveSkinning = true) {
    if (!this.vrm?.scene) return false;
    
    let targetMesh = null;
    this.vrm.scene.traverse((object) => {
      if (object.name === targetMeshName && object.isMesh) {
        targetMesh = object;
      }
    });
    
    if (!targetMesh) return false;
    
    if (preserveSkinning && targetMesh.isSkinnedMesh) {
      if (newGeometry.attributes) {
        if (targetMesh.geometry?.attributes?.skinIndex && !newGeometry.attributes.skinIndex) {
          newGeometry.setAttribute('skinIndex', targetMesh.geometry.attributes.skinIndex);
        }
        if (targetMesh.geometry?.attributes?.skinWeight && !newGeometry.attributes.skinWeight) {
          newGeometry.setAttribute('skinWeight', targetMesh.geometry.attributes.skinWeight);
        }
      }
    }
    
    targetMesh.geometry.dispose();
    targetMesh.geometry = newGeometry;
    
    if (targetMesh.isSkinnedMesh) {
      this._restoreSkinning(targetMesh);
    }
    
    targetMesh.updateMatrix();
    targetMesh.updateMatrixWorld(true);
    
    return true;
  }

  registerClothingItem(itemName, meshOrUrl, options = {}) {
    if (meshOrUrl.isMesh) {
      this.clothingItems.set(itemName, {
        type: 'mesh',
        mesh: meshOrUrl,
        options
      });
      return Promise.resolve(meshOrUrl);
    }
    
    return new Promise((resolve, reject) => {
      const loader = new THREE.ObjectLoader();
      loader.load(
        meshOrUrl,
        (object) => {
          let mesh = object;
          if (!object.isMesh) {
            object.traverse((child) => {
              if (child.isMesh && !mesh) {
                mesh = child;
              }
            });
          }
          
          this.clothingItems.set(itemName, {
            type: 'mesh',
            mesh,
            options
          });
          
          resolve(mesh);
        },
        undefined,
        (error) => {
          reject(error);
        }
      );
    });
  }

  equipClothing(itemName, slotName = 'default') {
    const item = this.clothingItems.get(itemName);
    if (!item) return false;
    
    if (this.activeClothing.has(slotName)) {
      const oldItem = this.activeClothing.get(slotName);
      if (oldItem.mesh) {
        oldItem.mesh.removeFromParent();
        if (oldItem.mesh.geometry) {
          oldItem.mesh.geometry.dispose();
        }
      }
    }
    
    if (item.type === 'mesh' && this.vrm?.scene) {
      let targetSkeleton = null;
      
      if (item.options.sourceMeshName) {
        this.vrm.scene.traverse((object) => {
          if (object.name === item.options.sourceMeshName && object.isSkinnedMesh) {
            targetSkeleton = object.skeleton;
          }
        });
      }
      
      if (!targetSkeleton && this.vrm.scene) {
        this.vrm.scene.traverse((object) => {
          if (object.isSkinnedMesh && object.skeleton && !targetSkeleton) {
            targetSkeleton = object.skeleton;
          }
        });
      }
      
      let clone;
      if (item.mesh.isSkinnedMesh && targetSkeleton) {
        clone = this._cloneWithSkinning(item.mesh, targetSkeleton);
      } else {
        clone = item.mesh.clone(true);
      }
      
      let parent = this.vrm.scene;
      
      if (item.options.parentBone && this.vrm.humanoid) {
        const bone = this.vrm.humanoid.getNormalizedBone(item.options.parentBone);
        if (bone) {
          parent = bone.node || bone;
        }
      } else if (item.options.parentBoneName) {
        this.vrm.scene.traverse((object) => {
          if (object.name === item.options.parentBoneName && object.isBone) {
            parent = object;
          }
        });
      }
      
      parent.add(clone);
      
      if (clone.isSkinnedMesh) {
        clone.updateMatrix();
        clone.updateMatrixWorld(true);
      }
      
      this.activeClothing.set(slotName, {
        name: itemName,
        mesh: clone
      });
    }
    
    return true;
  }

  unequipClothing(slotName) {
    if (!this.activeClothing.has(slotName)) return false;
    
    const item = this.activeClothing.get(slotName);
    if (item.mesh) {
      item.mesh.removeFromParent();
      if (item.mesh.geometry) {
        item.mesh.geometry.dispose();
      }
      if (item.mesh.material) {
        if (Array.isArray(item.mesh.material)) {
          item.mesh.material.forEach(m => m.dispose());
        } else {
          item.mesh.material.dispose();
        }
      }
    }
    
    this.activeClothing.delete(slotName);
    return true;
  }

  toggleMeshVisibility(meshName, visible) {
    if (!this.vrm?.scene) return false;
    
    let found = false;
    this.vrm.scene.traverse((object) => {
      if (object.name === meshName && object.isMesh) {
        object.visible = visible;
        found = true;
      }
    });
    
    return found;
  }

  getMeshNames() {
    const names = [];
    if (!this.vrm?.scene) return names;
    
    this.vrm.scene.traverse((object) => {
      if (object.isMesh) {
        names.push({
          name: object.name,
          visible: object.visible,
          isSkinned: object.isSkinnedMesh
        });
      }
    });
    
    return names;
  }

  restoreOriginalMaterial(materialKey) {
    const data = this.materials.get(materialKey);
    if (!data) return false;
    
    const original = this.originalMaterials.get(materialKey);
    if (!original) return false;
    
    const clone = original.clone();
    
    if (Array.isArray(data.mesh.material)) {
      data.mesh.material[data.materialIndex] = clone;
    } else {
      data.mesh.material = clone;
    }
    
    data.material = clone;
    this.materials.set(materialKey, data);
    
    return true;
  }

  restoreAllOriginalMaterials() {
    this.materials.forEach((data, key) => {
      this.restoreOriginalMaterial(key);
    });
  }
}

export default ClothingSystem;
