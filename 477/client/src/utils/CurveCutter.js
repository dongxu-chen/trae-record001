import * as THREE from 'three';
import { computeBoundsTree } from 'three-mesh-bvh';

export class CurveCutter {
  constructor() {
    this.points = [];
    this.curveLine = null;
    this.curveTube = null;
    this.controlPoints = [];
    this.scene = null;
    this.isDrawing = false;
    this.minDistance = 0.1;
  }

  startDrawing(scene) {
    this.scene = scene;
    this.isDrawing = true;
    this.clearDrawing();
  }

  stopDrawing() {
    this.isDrawing = false;
  }

  addPoint(worldPoint, faceNormal) {
    if (!this.isDrawing) return;

    if (this.points.length > 0) {
      const lastPoint = this.points[this.points.length - 1].position;
      const dist = worldPoint.distanceTo(lastPoint);
      if (dist < this.minDistance) return;
    }

    this.points.push({
      position: worldPoint.clone(),
      normal: faceNormal ? faceNormal.clone().normalize() : new THREE.Vector3(0, 1, 0)
    });

    this._addControlPoint(worldPoint);
    this._updateCurveVisual();
  }

  _addControlPoint(position) {
    const sphereGeo = new THREE.SphereGeometry(0.06, 12, 12);
    const sphereMat = new THREE.MeshBasicMaterial({
      color: 0xff4444,
      depthTest: false
    });
    const sphere = new THREE.Mesh(sphereGeo, sphereMat);
    sphere.position.copy(position);
    sphere.renderOrder = 999;
    this.scene.add(sphere);
    this.controlPoints.push(sphere);
  }

  _updateCurveVisual() {
    if (this.curveLine) {
      this.scene.remove(this.curveLine);
      this.curveLine.geometry.dispose();
      this.curveLine.material.dispose();
    }
    if (this.curveTube) {
      this.scene.remove(this.curveTube);
      this.curveTube.geometry.dispose();
      this.curveTube.material.dispose();
    }

    if (this.points.length < 2) return;

    const positions = this.points.map(p => p.position);

    if (positions.length >= 4) {
      const curve = new THREE.CatmullRomCurve3(positions);
      
      const tubeGeo = new THREE.TubeGeometry(curve, positions.length * 8, 0.025, 8, false);
      const tubeMat = new THREE.MeshBasicMaterial({
        color: 0xe94560,
        transparent: true,
        opacity: 0.8
      });
      this.curveTube = new THREE.Mesh(tubeGeo, tubeMat);
      this.curveTube.renderOrder = 998;
      this.scene.add(this.curveTube);
    } else {
      const lineGeo = new THREE.BufferGeometry().setFromPoints(positions);
      const lineMat = new THREE.LineBasicMaterial({
        color: 0xe94560,
        linewidth: 2
      });
      this.curveLine = new THREE.Line(lineGeo, lineMat);
      this.curveLine.renderOrder = 998;
      this.scene.add(this.curveLine);
    }
  }

  createExtrudedCutBrush(modelBounds) {
    if (this.points.length < 3) {
      console.warn('曲线点数不足，至少需要3个点');
      return null;
    }

    const positions = this.points.map(p => p.position);
    const curve = new THREE.CatmullRomCurve3(positions);

    const tangents = [];
    const upVectors = [];
    
    for (let i = 0; i <= 100; i++) {
      const t = i / 100;
      const tangent = curve.getTangentAt(Math.min(t, 0.9999));
      tangents.push(tangent);
      
      let up;
      const idx = Math.min(Math.round(t * (this.points.length - 1)), this.points.length - 1);
      up = this.points[idx].normal.clone();
      
      if (Math.abs(up.dot(tangent)) > 0.99) {
        up = new THREE.Vector3(0, 1, 0);
        if (Math.abs(up.dot(tangent)) > 0.99) {
          up = new THREE.Vector3(1, 0, 0);
        }
      }
      
      upVectors.push(up);
    }

    const shape = new THREE.Shape();
    const halfWidth = 0.01;
    const halfHeight = 0.01;
    shape.moveTo(-halfWidth, -halfHeight);
    shape.lineTo(halfWidth, -halfHeight);
    shape.lineTo(halfWidth, halfHeight);
    shape.lineTo(-halfWidth, halfHeight);
    shape.closePath();

    const extrudePath = curve;
    const extrudeGeo = new THREE.ExtrudeGeometry(shape, {
      steps: positions.length * 10,
      extrudePath: extrudePath,
    });

    const size = modelBounds.getSize(new THREE.Vector3());
    const maxSize = Math.max(size.x, size.y, size.z);

    const scale = maxSize * 4;
    extrudeGeo.scale(scale, scale, scale);

    const center = curve.getPointAt(0.5);
    const direction = center.clone().normalize();
    const offset = direction.multiplyScalar(maxSize * 2);
    
    const cutGeo1 = extrudeGeo.clone();
    const cutGeo2 = extrudeGeo.clone();
    cutGeo2.translate(-offset.x * 2, -offset.y * 2, -offset.z * 2);

    const mergedPositions = [];
    const pos1 = cutGeo1.getAttribute('position');
    const pos2 = cutGeo2.getAttribute('position');
    
    for (let i = 0; i < pos1.count; i++) {
      mergedPositions.push(pos1.getX(i), pos1.getY(i), pos1.getZ(i));
    }
    for (let i = 0; i < pos2.count; i++) {
      mergedPositions.push(pos2.getX(i), pos2.getY(i), pos2.getZ(i));
    }

    return this._createCutBrushFromPoints(positions, modelBounds);
  }

  _createCutBrushFromPoints(positions, modelBounds) {
    if (positions.length < 3) return null;

    const curve = new THREE.CatmullRomCurve3(positions, false);
    const size = modelBounds.getSize(new THREE.Vector3());
    const maxSize = Math.max(size.x, size.y, size.z);
    const center = modelBounds.getCenter(new THREE.Vector3());

    const avgNormal = new THREE.Vector3();
    this.points.forEach(p => avgNormal.add(p.normal));
    avgNormal.divideScalar(this.points.length).normalize();

    const sampleCount = Math.max(positions.length * 4, 20);
    const allTriangles = [];

    for (let i = 0; i < sampleCount; i++) {
      const t1 = i / sampleCount;
      const t2 = (i + 1) / sampleCount;

      const p1 = curve.getPointAt(Math.min(t1, 0.9999));
      const p2 = curve.getPointAt(Math.min(t2, 0.9999));

      const tangent = curve.getTangentAt(Math.min((t1 + t2) / 2, 0.9999));
      
      let localNormal = avgNormal.clone();
      if (Math.abs(localNormal.dot(tangent)) > 0.95) {
        localNormal = new THREE.Vector3(0, 1, 0);
        if (Math.abs(localNormal.dot(tangent)) > 0.95) {
          localNormal = new THREE.Vector3(1, 0, 0);
        }
      }
      
      const binormal = new THREE.Vector3().crossVectors(tangent, localNormal).normalize();
      const correctedNormal = new THREE.Vector3().crossVectors(binormal, tangent).normalize();

      const ext = maxSize * 2;

      const v1 = p1.clone().add(binormal.clone().multiplyScalar(ext));
      const v2 = p1.clone().add(binormal.clone().multiplyScalar(-ext));
      const v3 = p2.clone().add(binormal.clone().multiplyScalar(ext));
      const v4 = p2.clone().add(binormal.clone().multiplyScalar(-ext));

      const v5 = v1.clone().add(correctedNormal.clone().multiplyScalar(ext));
      const v6 = v2.clone().add(correctedNormal.clone().multiplyScalar(ext));
      const v7 = v3.clone().add(correctedNormal.clone().multiplyScalar(ext));
      const v8 = v4.clone().add(correctedNormal.clone().multiplyScalar(ext));

      allTriangles.push(
        v1.x, v1.y, v1.z, v3.x, v3.y, v3.z, v5.x, v5.y, v5.z,
        v3.x, v3.y, v3.z, v7.x, v7.y, v7.z, v5.x, v5.y, v5.z,
        v2.x, v2.y, v2.z, v4.x, v4.y, v4.z, v6.x, v6.y, v6.z,
        v4.x, v4.y, v4.z, v8.x, v8.y, v8.z, v6.x, v6.y, v6.z,
        v1.x, v1.y, v1.z, v2.x, v2.y, v2.z, v5.x, v5.y, v5.z,
        v2.x, v2.y, v2.z, v6.x, v6.y, v6.z, v5.x, v5.y, v5.z,
        v3.x, v3.y, v3.z, v4.x, v4.y, v4.z, v7.x, v7.y, v7.z,
        v4.x, v4.y, v4.z, v8.x, v8.y, v8.z, v7.x, v7.y, v7.z,
      );
    }

    if (allTriangles.length < 9) return null;

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(allTriangles, 3));
    geometry.computeVertexNormals();

    if (computeBoundsTree) {
      geometry.computeBoundsTree();
    }

    const material = new THREE.MeshStandardMaterial({
      color: 0xff0000,
      transparent: true,
      opacity: 0.2,
      side: THREE.DoubleSide
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.updateMatrixWorld(true);

    return mesh;
  }

  getCurvePoints() {
    return this.points.map(p => p.position.clone());
  }

  getCurve() {
    if (this.points.length < 4) return null;
    const positions = this.points.map(p => p.position);
    return new THREE.CatmullRomCurve3(positions);
  }

  getPointCount() {
    return this.points.length;
  }

  clearDrawing() {
    if (this.curveLine) {
      this.scene?.remove(this.curveLine);
      this.curveLine.geometry.dispose();
      this.curveLine.material.dispose();
      this.curveLine = null;
    }
    if (this.curveTube) {
      this.scene?.remove(this.curveTube);
      this.curveTube.geometry.dispose();
      this.curveTube.material.dispose();
      this.curveTube = null;
    }
    this.controlPoints.forEach(cp => {
      this.scene?.remove(cp);
      cp.geometry.dispose();
      cp.material.dispose();
    });
    this.controlPoints = [];
    this.points = [];
  }

  dispose() {
    this.clearDrawing();
    this.scene = null;
  }
}
