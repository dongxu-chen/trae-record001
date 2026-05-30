import * as THREE from 'three';

const PLANE_COLORS = [
  0xe94560,
  0x4fc3f7,
  0xffb74d,
  0x81c784,
  0xba68c8,
  0xffd54f,
  0x4db6ac,
  0xf06292
];

export class PlaneManager {
  constructor(scene, modelBounds) {
    this.scene = scene;
    this.modelBounds = modelBounds || new THREE.Box3();
    this.planes = [];
    this.planeMeshes = [];
    this.activePlaneIndex = -1;
    this.planeSize = this.calculatePlaneSize();
  }

  calculatePlaneSize() {
    if (!this.modelBounds || this.modelBounds.isEmpty()) {
      return 5;
    }
    const size = this.modelBounds.getSize(new THREE.Vector3());
    return Math.max(size.x, size.y, size.z) * 1.5;
  }

  updateModelBounds(bounds) {
    this.modelBounds = bounds;
    this.planeSize = this.calculatePlaneSize();
    
    this.planeMeshes.forEach((mesh, index) => {
      if (mesh) {
        const plane = this.planes[index];
        this.updatePlaneMesh(mesh, plane, index);
      }
    });
  }

  addPlane(normal = new THREE.Vector3(0, 1, 0), constant = 0, name = null) {
    const planeIndex = this.planes.length;
    const color = PLANE_COLORS[planeIndex % PLANE_COLORS.length];
    
    const plane = new THREE.Plane(normal.clone().normalize(), constant);
    plane.userData = {
      id: Date.now(),
      name: name || `切割平面 ${planeIndex + 1}`,
      color: color
    };
    
    this.planes.push(plane);
    
    const planeMesh = this.createPlaneMesh(plane, color);
    this.planeMeshes.push(planeMesh);
    this.scene.add(planeMesh);
    
    this.setActivePlane(planeIndex);
    
    return { plane, planeMesh, index: planeIndex };
  }

  createPlaneMesh(plane, color) {
    const geometry = new THREE.PlaneGeometry(this.planeSize, this.planeSize, 1, 1);
    const material = new THREE.MeshBasicMaterial({
      color: color,
      transparent: true,
      opacity: 0.4,
      side: THREE.DoubleSide,
      depthWrite: false
    });
    
    const mesh = new THREE.Mesh(geometry, material);
    
    const edgesGeometry = new THREE.EdgesGeometry(geometry);
    const edgesMaterial = new THREE.LineBasicMaterial({
      color: color,
      transparent: true,
      opacity: 0.8
    });
    const edges = new THREE.LineSegments(edgesGeometry, edgesMaterial);
    mesh.add(edges);
    
    this.updatePlaneMesh(mesh, plane);
    
    return mesh;
  }

  updatePlaneMesh(mesh, plane, index) {
    const normal = plane.normal.clone();
    const constant = plane.constant;
    
    const targetNormal = new THREE.Vector3(0, 0, 1);
    const quaternion = new THREE.Quaternion().setFromUnitVectors(targetNormal, normal);
    mesh.quaternion.copy(quaternion);
    
    const center = this.modelBounds.getCenter(new THREE.Vector3());
    const planePoint = normal.clone().multiplyScalar(-constant);
    
    if (!this.modelBounds.isEmpty()) {
      mesh.position.copy(center).add(planePoint);
    } else {
      mesh.position.copy(planePoint);
    }
    
    const newGeometry = new THREE.PlaneGeometry(this.planeSize, this.planeSize, 1, 1);
    mesh.geometry.dispose();
    mesh.geometry = newGeometry;
    
    if (mesh.children[0]) {
      const newEdgesGeometry = new THREE.EdgesGeometry(newGeometry);
      mesh.children[0].geometry.dispose();
      mesh.children[0].geometry = newEdgesGeometry;
    }
    
    mesh.updateMatrixWorld(true);
  }

  removePlane(index) {
    if (index < 0 || index >= this.planes.length) return false;
    
    const planeMesh = this.planeMeshes[index];
    if (planeMesh) {
      this.scene.remove(planeMesh);
      if (planeMesh.geometry) planeMesh.geometry.dispose();
      if (planeMesh.material) planeMesh.material.dispose();
      if (planeMesh.children[0]) {
        if (planeMesh.children[0].geometry) planeMesh.children[0].geometry.dispose();
        if (planeMesh.children[0].material) planeMesh.children[0].material.dispose();
      }
    }
    
    this.planes.splice(index, 1);
    this.planeMeshes.splice(index, 1);
    
    if (this.activePlaneIndex >= this.planes.length) {
      this.activePlaneIndex = this.planes.length - 1;
    }
    
    this.planes.forEach((plane, i) => {
      const color = PLANE_COLORS[i % PLANE_COLORS.length];
      plane.userData.color = color;
      plane.userData.name = `切割平面 ${i + 1}`;
      
      if (this.planeMeshes[i]) {
        this.planeMeshes[i].material.color.setHex(color);
        if (this.planeMeshes[i].children[0]) {
          this.planeMeshes[i].children[0].material.color.setHex(color);
        }
      }
    });
    
    return true;
  }

  setActivePlane(index) {
    this.activePlaneIndex = index;
    
    this.planeMeshes.forEach((mesh, i) => {
      if (mesh) {
        const isActive = i === index;
        mesh.material.opacity = isActive ? 0.6 : 0.4;
        mesh.scale.setScalar(isActive ? 1.05 : 1);
      }
    });
  }

  getActivePlane() {
    if (this.activePlaneIndex >= 0 && this.activePlaneIndex < this.planes.length) {
      return {
        plane: this.planes[this.activePlaneIndex],
        mesh: this.planeMeshes[this.activePlaneIndex],
        index: this.activePlaneIndex
      };
    }
    return null;
  }

  updatePlanePosition(index, delta) {
    if (index < 0 || index >= this.planes.length) return;
    
    const plane = this.planes[index];
    const mesh = this.planeMeshes[index];
    
    plane.constant += delta;
    
    this.updatePlaneMesh(mesh, plane, index);
  }

  updatePlaneNormal(index, normal) {
    if (index < 0 || index >= this.planes.length) return;
    
    const plane = this.planes[index];
    const mesh = this.planeMeshes[index];
    
    plane.normal.copy(normal).normalize();
    
    this.updatePlaneMesh(mesh, plane, index);
  }

  updatePlaneConstant(index, constant) {
    if (index < 0 || index >= this.planes.length) return;
    
    const plane = this.planes[index];
    const mesh = this.planeMeshes[index];
    
    plane.constant = constant;
    
    this.updatePlaneMesh(mesh, plane, index);
  }

  rotatePlane(index, axis, angle) {
    if (index < 0 || index >= this.planes.length) return;
    
    const plane = this.planes[index];
    const mesh = this.planeMeshes[index];
    
    const rotationMatrix = new THREE.Matrix4();
    rotationMatrix.makeRotationAxis(axis.normalize(), angle);
    
    plane.normal.applyMatrix4(rotationMatrix).normalize();
    
    this.updatePlaneMesh(mesh, plane, index);
  }

  resetPlane(index) {
    if (index < 0 || index >= this.planes.length) return;
    
    const plane = this.planes[index];
    plane.normal.set(0, 1, 0);
    plane.constant = 0;
    
    const mesh = this.planeMeshes[index];
    this.updatePlaneMesh(mesh, plane, index);
  }

  flipPlane(index) {
    if (index < 0 || index >= this.planes.length) return;
    
    const plane = this.planes[index];
    plane.normal.negate();
    plane.constant = -plane.constant;
    
    const mesh = this.planeMeshes[index];
    this.updatePlaneMesh(mesh, plane, index);
  }

  setPlaneVisibility(index, visible) {
    if (index < 0 || index >= this.planeMeshes.length) return;
    this.planeMeshes[index].visible = visible;
  }

  setAllPlanesVisibility(visible) {
    this.planeMeshes.forEach(mesh => {
      if (mesh) mesh.visible = visible;
    });
  }

  getAllPlanes() {
    return this.planes.map((plane, index) => ({
      plane,
      mesh: this.planeMeshes[index],
      index,
      name: plane.userData.name,
      color: plane.userData.color
    }));
  }

  getPlaneCount() {
    return this.planes.length;
  }

  clearAll() {
    this.planeMeshes.forEach(mesh => {
      if (mesh) {
        this.scene.remove(mesh);
        if (mesh.geometry) mesh.geometry.dispose();
        if (mesh.material) mesh.material.dispose();
        if (mesh.children[0]) {
          if (mesh.children[0].geometry) mesh.children[0].geometry.dispose();
          if (mesh.children[0].material) mesh.children[0].material.dispose();
        }
      }
    });
    
    this.planes = [];
    this.planeMeshes = [];
    this.activePlaneIndex = -1;
  }

  dispose() {
    this.clearAll();
    this.scene = null;
    this.modelBounds = null;
  }
}
