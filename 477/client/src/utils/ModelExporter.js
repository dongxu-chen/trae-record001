import * as THREE from 'three';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { STLExporter } from 'three/examples/jsm/exporters/STLExporter.js';

export class ModelExporter {
  constructor() {
    this.gltfExporter = new GLTFExporter();
    this.objExporter = new OBJExporter();
    this.stlExporter = new STLExporter();
  }

  exportToGLB(mesh, filename = 'model') {
    return new Promise((resolve, reject) => {
      const exportMesh = this.prepareMeshForExport(mesh);
      
      this.gltfExporter.parse(
        exportMesh,
        (result) => {
          if (result instanceof ArrayBuffer) {
            this.downloadFile(result, `${filename}.glb`, 'application/octet-stream');
            resolve();
          } else {
            reject(new Error('GLB导出失败'));
          }
        },
        (error) => {
          reject(error);
        },
        { binary: true }
      );
    });
  }

  exportToGLTF(mesh, filename = 'model') {
    return new Promise((resolve, reject) => {
      const exportMesh = this.prepareMeshForExport(mesh);
      
      this.gltfExporter.parse(
        exportMesh,
        (result) => {
          if (typeof result === 'object') {
            const jsonString = JSON.stringify(result, null, 2);
            this.downloadFile(jsonString, `${filename}.gltf`, 'application/json');
            resolve();
          } else {
            reject(new Error('GLTF导出失败'));
          }
        },
        (error) => {
          reject(error);
        },
        { binary: false }
      );
    });
  }

  exportToOBJ(mesh, filename = 'model') {
    try {
      const exportMesh = this.prepareMeshForExport(mesh);
      const objData = this.objExporter.parse(exportMesh);
      this.downloadFile(objData, `${filename}.obj`, 'text/plain');
      return Promise.resolve();
    } catch (error) {
      return Promise.reject(error);
    }
  }

  exportToSTL(mesh, filename = 'model', binary = true) {
    try {
      const exportMesh = this.prepareMeshForExport(mesh);
      let stlData;
      let mimeType;
      
      if (binary) {
        stlData = this.stlExporter.parse(exportMesh, { binary: true });
        mimeType = 'application/octet-stream';
      } else {
        stlData = this.stlExporter.parse(exportMesh, { binary: false });
        mimeType = 'text/plain';
      }
      
      this.downloadFile(stlData, `${filename}.stl`, mimeType);
      return Promise.resolve();
    } catch (error) {
      return Promise.reject(error);
    }
  }

  normalizeGeometry(mesh) {
    const clonedMesh = mesh.clone();
    clonedMesh.updateMatrixWorld(true);

    const geometry = clonedMesh.geometry.clone();
    geometry.applyMatrix4(clonedMesh.matrixWorld);

    if (geometry.boundsTree) {
      geometry.disposeBoundsTree();
    }

    geometry.computeBoundingBox();
    const boundingBox = geometry.boundingBox;
    const center = new THREE.Vector3();
    boundingBox.getCenter(center);

    const positionAttr = geometry.getAttribute('position');
    for (let i = 0; i < positionAttr.count; i++) {
      positionAttr.setX(i, positionAttr.getX(i) - center.x);
      positionAttr.setY(i, positionAttr.getY(i) - center.y);
      positionAttr.setZ(i, positionAttr.getZ(i) - center.z);
    }
    positionAttr.needsUpdate = true;

    geometry.computeBoundingBox();
    const size = new THREE.Vector3();
    geometry.boundingBox.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale = maxDim > 0 ? 1 / maxDim : 1;

    for (let i = 0; i < positionAttr.count; i++) {
      positionAttr.setX(i, positionAttr.getX(i) * scale);
      positionAttr.setY(i, positionAttr.getY(i) * scale);
      positionAttr.setZ(i, positionAttr.getZ(i) * scale);
    }
    positionAttr.needsUpdate = true;

    if (geometry.attributes.normal) {
      geometry.computeVertexNormals();
    } else {
      geometry.computeVertexNormals();
    }

    const material = new THREE.MeshStandardMaterial({
      color: clonedMesh.material?.color || 0xffffff,
      metalness: clonedMesh.material?.metalness || 0.1,
      roughness: clonedMesh.material?.roughness || 0.5
    });

    const exportMesh = new THREE.Mesh(geometry, material);
    exportMesh.position.set(0, 0, 0);
    exportMesh.rotation.set(0, 0, 0);
    exportMesh.scale.set(1, 1, 1);
    exportMesh.name = clonedMesh.name || 'exported_mesh';

    if (clonedMesh.userData) {
      exportMesh.userData = {
        ...clonedMesh.userData,
        normalized: true,
        originalCenter: { x: center.x, y: center.y, z: center.z },
        normalizationScale: scale
      };
    }

    return exportMesh;
  }

  prepareMeshForExport(mesh, normalize = true) {
    if (normalize) {
      return this.normalizeGeometry(mesh);
    }

    const clonedMesh = mesh.clone();
    clonedMesh.updateMatrixWorld(true);
    
    const geometry = clonedMesh.geometry.clone();
    
    if (geometry.boundsTree) {
      geometry.disposeBoundsTree();
    }
    
    if (clonedMesh.userData) {
      geometry.userData = { ...clonedMesh.userData };
    }
    
    const material = new THREE.MeshStandardMaterial({
      color: clonedMesh.material?.color || 0xffffff,
      metalness: clonedMesh.material?.metalness || 0.1,
      roughness: clonedMesh.material?.roughness || 0.5
    });
    
    const exportMesh = new THREE.Mesh(geometry, material);
    exportMesh.position.copy(clonedMesh.position);
    exportMesh.rotation.copy(clonedMesh.rotation);
    exportMesh.scale.copy(clonedMesh.scale);
    exportMesh.name = clonedMesh.name || 'exported_mesh';
    
    return exportMesh;
  }

  exportMultipleToGLB(meshes, filename = 'models') {
    return new Promise((resolve, reject) => {
      const group = new THREE.Group();
      
      meshes.forEach((mesh, index) => {
        const exportMesh = this.prepareMeshForExport(mesh);
        exportMesh.name = mesh.name || `piece_${index}`;
        group.add(exportMesh);
      });
      
      this.gltfExporter.parse(
        group,
        (result) => {
          if (result instanceof ArrayBuffer) {
            this.downloadFile(result, `${filename}.glb`, 'application/octet-stream');
            resolve();
          } else {
            reject(new Error('GLB批量导出失败'));
          }
        },
        (error) => {
          reject(error);
        },
        { binary: true }
      );
    });
  }

  exportAllPieces(pieces, baseName = 'piece', format = 'glb') {
    const promises = pieces.map((piece, index) => {
      const pieceName = piece.name || `${baseName}_${index + 1}`;
      
      switch (format.toLowerCase()) {
        case 'glb':
          return this.exportToGLB(piece, pieceName);
        case 'gltf':
          return this.exportToGLTF(piece, pieceName);
        case 'obj':
          return this.exportToOBJ(piece, pieceName);
        case 'stl':
          return this.exportToSTL(piece, pieceName);
        default:
          return this.exportToGLB(piece, pieceName);
      }
    });
    
    return Promise.all(promises);
  }

  downloadFile(data, filename, mimeType) {
    let blob;
    
    if (data instanceof ArrayBuffer) {
      blob = new Blob([data], { type: mimeType });
    } else {
      blob = new Blob([data], { type: mimeType });
    }
    
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 1000);
  }

  dispose() {
    this.gltfExporter = null;
    this.objExporter = null;
    this.stlExporter = null;
  }
}
