import * as THREE from 'three';

export class CutFiller {
  constructor() {
    this.fillTypes = {
      GRID: 'grid',
      HONEYCOMB: 'honeycomb',
      LATTICE: 'lattice',
      CONCENTRIC: 'concentric',
      TRIANGLE: 'triangle'
    };
  }

  generateFill(cutPiece, plane, modelBounds, options = {}) {
    const {
      fillType = this.fillTypes.GRID,
      fillDensity = 5,
      fillThickness = 0.03,
      fillDepth = 0.2,
      fillMaterial = null
    } = options;

    const crossSection = this._extractCrossSection(cutPiece, plane);
    if (!crossSection || crossSection.length < 3) {
      console.warn('无法提取截面轮廓');
      return null;
    }

    const fillGeometry = this._generateFillGeometry(
      crossSection,
      plane,
      fillType,
      fillDensity,
      fillThickness,
      fillDepth
    );

    if (!fillGeometry) return null;

    const material = fillMaterial || new THREE.MeshStandardMaterial({
      color: 0x66bb6a,
      metalness: 0.2,
      roughness: 0.6,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9
    });

    const fillMesh = new THREE.Mesh(fillGeometry, material);
    fillMesh.castShadow = true;
    fillMesh.receiveShadow = true;
    fillMesh.userData.isFill = true;
    fillMesh.userData.fillType = fillType;

    return fillMesh;
  }

  _extractCrossSection(mesh, plane) {
    if (!mesh || !mesh.geometry || !plane) return null;

    const geometry = mesh.geometry;
    const positionAttr = geometry.getAttribute('position');
    if (!positionAttr) return null;

    const normal = plane.normal.clone();
    const constant = plane.constant;
    const threshold = 0.05;

    const boundaryPoints = [];

    const index = geometry.index;
    const triangleCount = index ? index.count / 3 : positionAttr.count / 3;

    for (let i = 0; i < triangleCount; i++) {
      let i0, i1, i2;
      if (index) {
        i0 = index.getX(i * 3);
        i1 = index.getX(i * 3 + 1);
        i2 = index.getX(i * 3 + 2);
      } else {
        i0 = i * 3;
        i1 = i * 3 + 1;
        i2 = i * 3 + 2;
      }

      const v0 = new THREE.Vector3(positionAttr.getX(i0), positionAttr.getY(i0), positionAttr.getZ(i0));
      const v1 = new THREE.Vector3(positionAttr.getX(i1), positionAttr.getY(i1), positionAttr.getZ(i1));
      const v2 = new THREE.Vector3(positionAttr.getX(i2), positionAttr.getY(i2), positionAttr.getZ(i2));

      const d0 = normal.dot(v0) + constant;
      const d1 = normal.dot(v1) + constant;
      const d2 = normal.dot(v2) + constant;

      const edges = [[v0, d0, v1, d1], [v1, d1, v2, d2], [v2, d2, v0, d0]];

      for (const [va, da, vb, db] of edges) {
        if ((da >= -threshold && da <= threshold) || (db >= -threshold && db <= threshold)) {
          const midPoint = va.clone().lerp(vb, 0.5);
          const dist = normal.dot(midPoint) + constant;
          if (Math.abs(dist) < threshold * 2) {
            boundaryPoints.push(midPoint);
          }
        } else if ((da > 0 && db < 0) || (da < 0 && db > 0)) {
          const t = da / (da - db);
          const intersection = va.clone().lerp(vb, t);
          boundaryPoints.push(intersection);
        }
      }
    }

    if (boundaryPoints.length < 3) return null;

    return this._sortBoundaryPoints(boundaryPoints, normal);
  }

  _sortBoundaryPoints(points, normal) {
    if (points.length < 3) return points;

    const centroid = new THREE.Vector3();
    points.forEach(p => centroid.add(p));
    centroid.divideScalar(points.length);

    let tangent = new THREE.Vector3(1, 0, 0);
    if (Math.abs(normal.dot(tangent)) > 0.9) {
      tangent = new THREE.Vector3(0, 1, 0);
    }
    tangent = new THREE.Vector3().crossVectors(normal, tangent).normalize();
    const bitangent = new THREE.Vector3().crossVectors(normal, tangent).normalize();

    const sorted = [...points];
    sorted.sort((a, b) => {
      const da = a.clone().sub(centroid);
      const db = b.clone().sub(centroid);
      const angleA = Math.atan2(da.dot(bitangent), da.dot(tangent));
      const angleB = Math.atan2(db.dot(bitangent), db.dot(tangent));
      return angleA - angleB;
    });

    const simplified = [sorted[0]];
    for (let i = 1; i < sorted.length; i++) {
      if (sorted[i].distanceTo(simplified[simplified.length - 1]) > 0.02) {
        simplified.push(sorted[i]);
      }
    }

    return simplified;
  }

  _generateFillGeometry(boundaryPoints, plane, fillType, density, thickness, depth) {
    const normal = plane.normal.clone().normalize();
    const centroid = new THREE.Vector3();
    boundaryPoints.forEach(p => centroid.add(p));
    centroid.divideScalar(boundaryPoints.length);

    let tangent = new THREE.Vector3(1, 0, 0);
    if (Math.abs(normal.dot(tangent)) > 0.9) {
      tangent = new THREE.Vector3(0, 1, 0);
    }
    tangent = new THREE.Vector3().crossVectors(normal, tangent).normalize();
    const bitangent = new THREE.Vector3().crossVectors(normal, tangent).normalize();

    const localPoints = boundaryPoints.map(p => {
      const d = p.clone().sub(centroid);
      return new THREE.Vector2(d.dot(tangent), d.dot(bitangent));
    });

    let minU = Infinity, maxU = -Infinity, minV = Infinity, maxV = -Infinity;
    localPoints.forEach(p => {
      minU = Math.min(minU, p.x);
      maxU = Math.max(maxU, p.x);
      minV = Math.min(minV, p.y);
      maxV = Math.max(maxV, p.y);
    });

    const fillLines = [];

    switch (fillType) {
      case this.fillTypes.GRID:
        fillLines.push(...this._generateGridFill(minU, maxU, minV, maxV, density));
        break;
      case this.fillTypes.HONEYCOMB:
        fillLines.push(...this._generateHoneycombFill(minU, maxU, minV, maxV, density));
        break;
      case this.fillTypes.LATTICE:
        fillLines.push(...this._generateLatticeFill(minU, maxU, minV, maxV, density));
        break;
      case this.fillTypes.CONCENTRIC:
        fillLines.push(...this._generateConcentricFill(minU, maxU, minV, maxV, density));
        break;
      case this.fillTypes.TRIANGLE:
        fillLines.push(...this._generateTriangleFill(minU, maxU, minV, maxV, density));
        break;
    }

    const positions = [];
    const halfDepth = depth / 2;

    for (const line of fillLines) {
      const startLocal = line.start;
      const endLocal = line.end;

      const startWorld = centroid.clone()
        .add(tangent.clone().multiplyScalar(startLocal.x))
        .add(bitangent.clone().multiplyScalar(startLocal.y));
      const endWorld = centroid.clone()
        .add(tangent.clone().multiplyScalar(endLocal.x))
        .add(bitangent.clone().multiplyScalar(endLocal.y));

      const dir = endWorld.clone().sub(startWorld);
      const len = dir.length();
      if (len < 0.001) continue;
      dir.normalize();

      const sideVec = new THREE.Vector3().crossVectors(dir, normal).normalize().multiplyScalar(thickness / 2);

      const s0 = startWorld.clone().add(normal.clone().multiplyScalar(-halfDepth)).add(sideVec);
      const s1 = startWorld.clone().add(normal.clone().multiplyScalar(-halfDepth)).sub(sideVec);
      const s2 = startWorld.clone().add(normal.clone().multiplyScalar(halfDepth)).add(sideVec);
      const s3 = startWorld.clone().add(normal.clone().multiplyScalar(halfDepth)).sub(sideVec);
      const e0 = endWorld.clone().add(normal.clone().multiplyScalar(-halfDepth)).add(sideVec);
      const e1 = endWorld.clone().add(normal.clone().multiplyScalar(-halfDepth)).sub(sideVec);
      const e2 = endWorld.clone().add(normal.clone().multiplyScalar(halfDepth)).add(sideVec);
      const e3 = endWorld.clone().add(normal.clone().multiplyScalar(halfDepth)).sub(sideVec);

      positions.push(
        s0.x,s0.y,s0.z, e0.x,e0.y,e0.z, s2.x,s2.y,s2.z,
        e0.x,e0.y,e0.z, e2.x,e2.y,e2.z, s2.x,s2.y,s2.z,
        s1.x,s1.y,s1.z, s3.x,s3.y,s3.z, e1.x,e1.y,e1.z,
        e1.x,e1.y,e1.z, s3.x,s3.y,s3.z, e3.x,e3.y,e3.z,
        s0.x,s0.y,s0.z, s1.x,s1.y,s1.z, e0.x,e0.y,e0.z,
        e0.x,e0.y,e0.z, s1.x,s1.y,s1.z, e1.x,e1.y,e1.z,
        s2.x,s2.y,s2.z, e2.x,e2.y,e2.z, s3.x,s3.y,s3.z,
        e2.x,e2.y,e2.z, e3.x,e3.y,e3.z, s3.x,s3.y,s3.z,
      );
    }

    if (positions.length < 9) return null;

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.computeVertexNormals();

    return geometry;
  }

  _generateGridFill(minU, maxU, minV, maxV, density) {
    const lines = [];
    const stepU = (maxU - minU) / density;
    const stepV = (maxV - minV) / density;

    for (let i = 0; i <= density; i++) {
      const u = minU + i * stepU;
      lines.push({ start: { x: u, y: minV }, end: { x: u, y: maxV } });
    }

    for (let i = 0; i <= density; i++) {
      const v = minV + i * stepV;
      lines.push({ start: { x: minU, y: v }, end: { x: maxU, y: v } });
    }

    return lines;
  }

  _generateHoneycombFill(minU, maxU, minV, maxV, density) {
    const lines = [];
    const size = Math.max((maxU - minU) / density, 0.05);
    const hexHeight = size * Math.sqrt(3);

    for (let row = -1; row < density + 2; row++) {
      for (let col = -1; col < density + 2; col++) {
        const cx = minU + col * size * 1.5;
        const cy = minV + row * hexHeight + (col % 2 ? hexHeight / 2 : 0);

        for (let k = 0; k < 6; k++) {
          const angle1 = (Math.PI / 3) * k;
          const angle2 = (Math.PI / 3) * (k + 1);
          const x1 = cx + size * Math.cos(angle1);
          const y1 = cy + size * Math.sin(angle1);
          const x2 = cx + size * Math.cos(angle2);
          const y2 = cy + size * Math.sin(angle2);

          if (x1 >= minU - size && x1 <= maxU + size && y1 >= minV - size && y1 <= maxV + size) {
            lines.push({ start: { x: x1, y: y1 }, end: { x: x2, y: y2 } });
          }
        }
      }
    }

    return lines;
  }

  _generateLatticeFill(minU, maxU, minV, maxV, density) {
    const lines = [];
    const stepU = (maxU - minU) / density;
    const stepV = (maxV - minV) / density;

    for (let i = 0; i <= density; i++) {
      const u = minU + i * stepU;
      lines.push({ start: { x: u, y: minV }, end: { x: maxU, y: minV + (maxV - minV) * (i / density) } });
    }

    for (let i = 0; i <= density; i++) {
      const v = minV + i * stepV;
      lines.push({ start: { x: minU, y: v }, end: { x: minU + (maxU - minU) * (i / density), y: maxV } });
    }

    for (let i = 0; i <= density; i++) {
      const u = minU + i * stepU;
      lines.push({ start: { x: u, y: maxV }, end: { x: maxU, y: maxV - (maxV - minV) * (i / density) } });
    }

    return lines;
  }

  _generateConcentricFill(minU, maxU, minV, maxV, density) {
    const lines = [];
    const centerU = (minU + maxU) / 2;
    const centerV = (minV + maxV) / 2;
    const maxRadius = Math.max(maxU - minU, maxV - minV) / 2;

    for (let i = 1; i <= density; i++) {
      const r = (i / density) * maxRadius;
      const segments = Math.max(12, i * 4);

      for (let j = 0; j < segments; j++) {
        const a1 = (j / segments) * Math.PI * 2;
        const a2 = ((j + 1) / segments) * Math.PI * 2;
        lines.push({
          start: { x: centerU + r * Math.cos(a1), y: centerV + r * Math.sin(a1) },
          end: { x: centerU + r * Math.cos(a2), y: centerV + r * Math.sin(a2) }
        });
      }
    }

    const spokeCount = density * 2;
    for (let i = 0; i < spokeCount; i++) {
      const angle = (i / spokeCount) * Math.PI * 2;
      lines.push({
        start: { x: centerU, y: centerV },
        end: { x: centerU + maxRadius * Math.cos(angle), y: centerV + maxRadius * Math.sin(angle) }
      });
    }

    return lines;
  }

  _generateTriangleFill(minU, maxU, minV, maxV, density) {
    const lines = [];
    const stepU = (maxU - minU) / density;
    const stepV = (maxV - minV) / density;

    for (let i = 0; i <= density; i++) {
      const u = minU + i * stepU;
      lines.push({ start: { x: u, y: minV }, end: { x: u, y: maxV } });
    }

    for (let i = 0; i < density; i++) {
      for (let j = 0; j < density; j++) {
        const u = minU + i * stepU;
        const v = minV + j * stepV;
        const uNext = u + stepU;
        const vNext = v + stepV;

        if ((i + j) % 2 === 0) {
          lines.push({ start: { x: u, y: v }, end: { x: uNext, y: vNext } });
        } else {
          lines.push({ start: { x: uNext, y: v }, end: { x: u, y: vNext } });
        }
      }
    }

    return lines;
  }

  addFillToPieces(pieces, planes, modelBounds, options = {}) {
    const filledPieces = [];

    for (const piece of pieces) {
      const pieceCopy = piece.clone();
      const fills = [];

      for (const plane of planes) {
        const fill = this.generateFill(piece, plane, modelBounds, options);
        if (fill) {
          fills.push(fill);
        }
      }

      filledPieces.push({
        piece: pieceCopy,
        fills: fills
      });
    }

    return filledPieces;
  }
}
