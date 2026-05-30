import * as THREE from 'three';
import { computeBoundsTree, disposeBoundsTree, acceleratedRaycast } from 'three-mesh-bvh';
import { SUBTRACTION, ADDITION, Brush, Evaluator } from 'three-bvh-csg';

THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.BufferGeometry.prototype.disposeBoundsTree = disposeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;

export class CsgCutter {
  constructor() {
    this.evaluator = new Evaluator();
  }

  createCutPlaneBrush(plane, modelBounds, sizeMultiplier = 2) {
    const size = modelBounds.getSize(new THREE.Vector3()).multiplyScalar(sizeMultiplier);
    const maxSize = Math.max(size.x, size.y, size.z);
    
    const geometry = new THREE.BoxGeometry(maxSize * 2, maxSize * 2, maxSize * 2);
    const material = new THREE.MeshStandardMaterial({
      color: 0x00ff00,
      transparent: true,
      opacity: 0.3,
      side: THREE.DoubleSide
    });
    
    const boxMesh = new THREE.Mesh(geometry, material);
    
    const planeNormal = plane.normal.clone();
    const planeConstant = plane.constant;
    
    const targetNormal = new THREE.Vector3(0, -1, 0);
    const quaternion = new THREE.Quaternion().setFromUnitVectors(targetNormal, planeNormal);
    boxMesh.quaternion.copy(quaternion);
    
    const center = modelBounds.getCenter(new THREE.Vector3());
    const planePoint = planeNormal.clone().multiplyScalar(-planeConstant);
    const offset = planePoint.clone().add(center);
    const moveDir = planeNormal.clone().multiplyScalar(-maxSize);
    boxMesh.position.copy(offset).add(moveDir);
    
    boxMesh.updateMatrixWorld(true);
    
    return new Brush(boxMesh.geometry, boxMesh.material, boxMesh.matrix);
  }

  cutMeshByPlane(mesh, plane, modelBounds) {
    if (!mesh || !mesh.geometry) return null;
    
    try {
      const sourceBrush = this.createBrushFromMesh(mesh);
      if (!sourceBrush) return null;
      
      const cutBrush = this.createCutPlaneBrush(plane, modelBounds);
      
      this.evaluator.useGroups = true;
      
      const positiveResult = this.evaluator.evaluate(sourceBrush, cutBrush, SUBTRACTION);
      
      const inversePlane = new THREE.Plane(plane.normal.clone().negate(), -plane.constant);
      const inverseCutBrush = this.createCutPlaneBrush(inversePlane, modelBounds);
      
      const negativeResult = this.evaluator.evaluate(sourceBrush, inverseCutBrush, SUBTRACTION);
      
      const positiveMesh = this.createMeshFromResult(positiveResult, 0x4fc3f7);
      const negativeMesh = this.createMeshFromResult(negativeResult, 0xffb74d);
      
      return {
        positive: positiveMesh,
        negative: negativeMesh
      };
    } catch (error) {
      console.error('CSG切割失败:', error);
      return null;
    }
  }

  createBrushFromMesh(mesh) {
    try {
      let geometry = mesh.geometry;
      
      if (!geometry.index) {
        geometry = geometry.toNonIndexed();
      }
      
      const positionAttr = geometry.getAttribute('position');
      if (!positionAttr || positionAttr.count < 3) {
        console.warn('几何体顶点不足');
        return null;
      }
      
      const clonedGeometry = geometry.clone();
      clonedGeometry.applyMatrix4(mesh.matrixWorld);
      
      if (!clonedGeometry.boundsTree) {
        clonedGeometry.computeBoundsTree();
      }
      
      const material = mesh.material.clone();
      material.side = THREE.FrontSide;
      
      return new Brush(clonedGeometry, material);
    } catch (error) {
      console.error('创建Brush失败:', error);
      return null;
    }
  }

  createMeshFromResult(result, color) {
    if (!result || !result.geometry) return null;
    
    const geometry = result.geometry;
    
    if (!geometry.attributes.normal) {
      geometry.computeVertexNormals();
    }
    
    const material = new THREE.MeshStandardMaterial({
      color: color,
      metalness: 0.1,
      roughness: 0.5,
      side: THREE.DoubleSide,
      flatShading: false
    });
    
    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    
    return mesh;
  }

  createDecimatedBrush(mesh, decimationRatio = 0.25) {
    try {
      let geometry = mesh.geometry;
      if (!geometry.index) {
        geometry = geometry.toNonIndexed();
      }

      const positionAttr = geometry.getAttribute('position');
      if (!positionAttr || positionAttr.count < 9) {
        return this.createBrushFromMesh(mesh);
      }

      const totalFaces = positionAttr.count / 3;
      const targetFaces = Math.max(8, Math.floor(totalFaces * decimationRatio));
      const step = Math.max(1, Math.floor(totalFaces / targetFaces));

      const positions = [];
      for (let i = 0; i < totalFaces; i += step) {
        const baseIdx = i * 3;
        for (let j = 0; j < 3; j++) {
          const idx = (baseIdx + j) * 3;
          positions.push(
            positionAttr.array[idx],
            positionAttr.array[idx + 1],
            positionAttr.array[idx + 2]
          );
        }
      }

      const decimatedGeometry = new THREE.BufferGeometry();
      decimatedGeometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      decimatedGeometry.computeVertexNormals();
      decimatedGeometry.applyMatrix4(mesh.matrixWorld);

      if (!decimatedGeometry.boundsTree) {
        decimatedGeometry.computeBoundsTree();
      }

      const material = mesh.material.clone();
      material.side = THREE.FrontSide;

      return new Brush(decimatedGeometry, material);
    } catch (error) {
      console.warn('粗切割降面失败，使用原始网格:', error);
      return this.createBrushFromMesh(mesh);
    }
  }

  cutMeshByPlaneCoarse(mesh, plane, modelBounds, decimationRatio = 0.25) {
    if (!mesh || !mesh.geometry) return null;

    try {
      const sourceBrush = this.createDecimatedBrush(mesh, decimationRatio);
      if (!sourceBrush) return null;

      const cutBrush = this.createCutPlaneBrush(plane, modelBounds);
      this.evaluator.useGroups = true;

      const positiveResult = this.evaluator.evaluate(sourceBrush, cutBrush, SUBTRACTION);

      const inversePlane = new THREE.Plane(plane.normal.clone().negate(), -plane.constant);
      const inverseCutBrush = this.createCutPlaneBrush(inversePlane, modelBounds);

      const negativeResult = this.evaluator.evaluate(sourceBrush, inverseCutBrush, SUBTRACTION);

      const positiveBounds = positiveResult?.geometry
        ? new THREE.Box3().setFromBufferAttribute(positiveResult.geometry.getAttribute('position'))
        : null;
      const negativeBounds = negativeResult?.geometry
        ? new THREE.Box3().setFromBufferAttribute(negativeResult.geometry.getAttribute('position'))
        : null;

      return {
        positiveBounds,
        negativeBounds,
        hasPositive: positiveResult?.geometry?.getAttribute('position')?.count > 0,
        hasNegative: negativeResult?.geometry?.getAttribute('position')?.count > 0
      };
    } catch (error) {
      console.warn('粗切割失败:', error);
      return null;
    }
  }

  cutMeshByPlaneFine(mesh, plane, modelBounds, coarseResult) {
    if (!mesh || !mesh.geometry) return null;

    try {
      const sourceBrush = this.createBrushFromMesh(mesh);
      if (!sourceBrush) return null;

      const cutBrush = this.createCutPlaneBrush(plane, modelBounds);
      this.evaluator.useGroups = true;

      const results = {};

      if (!coarseResult || coarseResult.hasPositive) {
        const positiveResult = this.evaluator.evaluate(sourceBrush, cutBrush, SUBTRACTION);
        if (positiveResult?.geometry?.getAttribute('position')?.count > 0) {
          results.positive = this.createMeshFromResult(positiveResult, 0x4fc3f7);
        }
      }

      if (!coarseResult || coarseResult.hasNegative) {
        const inversePlane = new THREE.Plane(plane.normal.clone().negate(), -plane.constant);
        const inverseCutBrush = this.createCutPlaneBrush(inversePlane, modelBounds);
        const negativeResult = this.evaluator.evaluate(sourceBrush, inverseCutBrush, SUBTRACTION);
        if (negativeResult?.geometry?.getAttribute('position')?.count > 0) {
          results.negative = this.createMeshFromResult(negativeResult, 0xffb74d);
        }
      }

      return results;
    } catch (error) {
      console.error('细切割失败:', error);
      return this.cutMeshByPlane(mesh, plane, modelBounds);
    }
  }

  cutMeshByMultiplePlanes(mesh, planes, modelBounds, options = {}) {
    const {
      hierarchical = false,
      decimationRatio = 0.25,
      onProgress = null
    } = options;

    if (!hierarchical) {
      return this._cutSimple(mesh, planes, modelBounds, onProgress);
    }

    return this._cutHierarchical(mesh, planes, modelBounds, decimationRatio, onProgress);
  }

  _cutSimple(mesh, planes, modelBounds, onProgress) {
    let pieces = [mesh];

    for (let i = 0; i < planes.length; i++) {
      const plane = planes[i];
      const newPieces = [];

      for (const piece of pieces) {
        const cutResult = this.cutMeshByPlane(piece, plane, modelBounds);
        if (cutResult) {
          if (cutResult.positive) {
            cutResult.positive.userData.cutPlaneIndex = i;
            cutResult.positive.userData.side = 'positive';
            newPieces.push(cutResult.positive);
          }
          if (cutResult.negative) {
            cutResult.negative.userData.cutPlaneIndex = i;
            cutResult.negative.userData.side = 'negative';
            newPieces.push(cutResult.negative);
          }
        } else {
          newPieces.push(piece);
        }
      }

      pieces = newPieces;
      if (onProgress) onProgress(i + 1, planes.length, 'simple');
    }

    pieces.forEach((piece, index) => {
      piece.userData.pieceIndex = index;
      piece.userData.originalName = mesh.name || `piece_${index}`;
    });

    return pieces;
  }

  _cutHierarchical(mesh, planes, modelBounds, decimationRatio, onProgress) {
    const totalPlanes = planes.length;

    if (onProgress) onProgress(0, totalPlanes, 'coarse-start');

    const coarseResults = [];
    for (let i = 0; i < totalPlanes; i++) {
      const plane = planes[i];
      const coarseResult = this.cutMeshByPlaneCoarse(mesh, plane, modelBounds, decimationRatio);
      coarseResults.push(coarseResult);
      if (onProgress) onProgress(i + 1, totalPlanes, 'coarse');
    }

    if (onProgress) onProgress(0, totalPlanes, 'fine-start');

    let pieces = [mesh];

    for (let i = 0; i < totalPlanes; i++) {
      const plane = planes[i];
      const coarseResult = coarseResults[i];
      const newPieces = [];

      for (const piece of pieces) {
        const fineResult = this.cutMeshByPlaneFine(piece, plane, modelBounds, coarseResult);
        if (fineResult) {
          if (fineResult.positive) {
            fineResult.positive.userData.cutPlaneIndex = i;
            fineResult.positive.userData.side = 'positive';
            newPieces.push(fineResult.positive);
          }
          if (fineResult.negative) {
            fineResult.negative.userData.cutPlaneIndex = i;
            fineResult.negative.userData.side = 'negative';
            newPieces.push(fineResult.negative);
          }
          if (!fineResult.positive && !fineResult.negative) {
            newPieces.push(piece);
          }
        } else {
          newPieces.push(piece);
        }
      }

      pieces = newPieces;
      if (onProgress) onProgress(i + 1, totalPlanes, 'fine');
    }

    pieces = this._filterDegeneratePieces(pieces);

    pieces.forEach((piece, index) => {
      piece.userData.pieceIndex = index;
      piece.userData.originalName = mesh.name || `piece_${index}`;
      piece.userData.cutMode = 'hierarchical';
    });

    return pieces;
  }

  _filterDegeneratePieces(pieces) {
    return pieces.filter(piece => {
      if (!piece || !piece.geometry) return false;
      const positionAttr = piece.geometry.getAttribute('position');
      if (!positionAttr || positionAttr.count < 3) return false;

      const box = new THREE.Box3().setFromObject(piece);
      const size = box.getSize(new THREE.Vector3());
      return size.x > 0.001 && size.y > 0.001 && size.z > 0.001;
    });
  }

  getMeshStats(mesh) {
    if (!mesh || !mesh.geometry) return null;
    
    const geometry = mesh.geometry;
    const vertexCount = geometry.attributes.position 
      ? geometry.attributes.position.count 
      : 0;
    const faceCount = geometry.index 
      ? geometry.index.count / 3 
      : (geometry.attributes.position ? geometry.attributes.position.count / 3 : 0);
    
    const boundingBox = new THREE.Box3().setFromObject(mesh);
    const size = boundingBox.getSize(new THREE.Vector3());
    const volume = size.x * size.y * size.z;
    
    return {
      vertexCount: Math.round(vertexCount),
      faceCount: Math.round(faceCount),
      volume: volume,
      boundingBox: boundingBox
    };
  }

  dispose() {
    this.evaluator = null;
  }
}
