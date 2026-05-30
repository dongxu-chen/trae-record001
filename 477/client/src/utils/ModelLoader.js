import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';

export class ModelLoader {
  constructor() {
    this.gltfLoader = new GLTFLoader();
    this.objLoader = new OBJLoader();
    this.stlLoader = new STLLoader();
    this.textureLoader = new THREE.TextureLoader();
  }

  async loadModel(url, fileName) {
    const extension = this.getFileExtension(fileName || url);
    
    switch (extension.toLowerCase()) {
      case 'glb':
      case 'gltf':
        return this.loadGLTF(url);
      case 'obj':
        return this.loadOBJ(url);
      case 'stl':
        return this.loadSTL(url);
      default:
        throw new Error(`不支持的文件格式: ${extension}`);
    }
  }

  getFileExtension(filename) {
    const parts = filename.split('.');
    return parts[parts.length - 1].toLowerCase();
  }

  async loadGLTF(url) {
    return new Promise((resolve, reject) => {
      this.gltfLoader.load(
        url,
        (gltf) => {
          const result = this.processLoadedModel(gltf.scene, url);
          resolve(result);
        },
        (progress) => {
          console.log('GLTF加载进度:', progress);
        },
        (error) => {
          reject(new Error(`GLTF加载失败: ${error.message}`));
        }
      );
    });
  }

  async loadOBJ(url) {
    return new Promise((resolve, reject) => {
      this.objLoader.load(
        url,
        (object) => {
          const result = this.processLoadedModel(object, url);
          resolve(result);
        },
        (progress) => {
          console.log('OBJ加载进度:', progress);
        },
        (error) => {
          reject(new Error(`OBJ加载失败: ${error.message}`));
        }
      );
    });
  }

  async loadSTL(url) {
    return new Promise((resolve, reject) => {
      this.stlLoader.load(
        url,
        (geometry) => {
          geometry.computeVertexNormals();
          
          const material = new THREE.MeshStandardMaterial({
            color: 0xcccccc,
            metalness: 0.1,
            roughness: 0.6
          });
          
          const mesh = new THREE.Mesh(geometry, material);
          mesh.castShadow = true;
          mesh.receiveShadow = true;
          
          const group = new THREE.Group();
          group.add(mesh);
          
          const result = this.processLoadedModel(group, url);
          resolve(result);
        },
        (progress) => {
          console.log('STL加载进度:', progress);
        },
        (error) => {
          reject(new Error(`STL加载失败: ${error.message}`));
        }
      );
    });
  }

  processLoadedModel(group, url) {
    const meshes = [];
    let totalVertices = 0;
    let totalFaces = 0;
    
    group.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
        
        if (!child.material) {
          child.material = new THREE.MeshStandardMaterial({
            color: 0xcccccc,
            metalness: 0.1,
            roughness: 0.6
          });
        }
        
        if (Array.isArray(child.material)) {
          child.material = child.material[0];
        }
        
        if (child.material) {
          child.material.side = THREE.DoubleSide;
        }
        
        if (child.geometry) {
          if (!child.geometry.attributes.normal) {
            child.geometry.computeVertexNormals();
          }
          
          if (!child.geometry.index) {
            child.geometry = child.geometry.toNonIndexed();
          }
          
          const positionAttr = child.geometry.getAttribute('position');
          if (positionAttr) {
            totalVertices += positionAttr.count;
            totalFaces += positionAttr.count / 3;
          }
        }
        
        meshes.push(child);
      }
    });
    
    const boundingBox = new THREE.Box3().setFromObject(group);
    const center = boundingBox.getCenter(new THREE.Vector3());
    const size = boundingBox.getSize(new THREE.Vector3());
    
    const maxDimension = Math.max(size.x, size.y, size.z);
    const scale = 4 / maxDimension;
    
    group.scale.setScalar(scale);
    group.position.sub(center.multiplyScalar(scale));
    
    const newBoundingBox = new THREE.Box3().setFromObject(group);
    
    return {
      group,
      meshes,
      boundingBox: newBoundingBox,
      stats: {
        meshCount: meshes.length,
        vertexCount: Math.round(totalVertices),
        faceCount: Math.round(totalFaces),
        originalSize: size,
        scaledSize: newBoundingBox.getSize(new THREE.Vector3())
      }
    };
  }

  async uploadModel(file) {
    const formData = new FormData();
    formData.append('model', file);
    
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || '上传失败');
    }
    
    return response.json();
  }

  async loadFromFile(file) {
    const uploadResult = await this.uploadModel(file);
    const modelUrl = uploadResult.url;
    const result = await this.loadModel(modelUrl, file.name);
    result.uploadInfo = uploadResult;
    return result;
  }

  async loadFromLocalFile(file) {
    const url = URL.createObjectURL(file);
    try {
      const result = await this.loadModel(url, file.name);
      result.uploadInfo = {
        originalName: file.name,
        size: file.size
      };
      return result;
    } finally {
      setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 5000);
    }
  }

  dispose() {
    this.gltfLoader = null;
    this.objLoader = null;
    this.stlLoader = null;
    this.textureLoader = null;
  }
}
