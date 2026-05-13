import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

export class FollowCamera {
  constructor(renderer, vrm = null) {
    this.renderer = renderer;
    this.vrm = vrm;
    
    this.camera = new THREE.PerspectiveCamera(
      45,
      window.innerWidth / window.innerHeight,
      0.1,
      20
    );
    this.camera.position.set(0, 1.2, 2.5);
    
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.target.set(0, 1.2, 0);
    this.controls.minDistance = 0.5;
    this.controls.maxDistance = 10;
    this.controls.maxPolarAngle = Math.PI * 0.8;
    
    this.followTarget = null;
    this.followOffset = new THREE.Vector3(0, 1.2, 2.5);
    this.smoothness = 0.1;
    
    this._initEventListeners();
  }

  _initEventListeners() {
    window.addEventListener('resize', () => this._onResize());
  }

  _onResize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
  }

  setVRM(vrm) {
    this.vrm = vrm;
    if (vrm?.humanoid) {
      this.followTarget = vrm.humanoid.getNormalizedBone('head');
      if (!this.followTarget) {
        this.followTarget = vrm.humanoid.getNormalizedBone('neck');
      }
    }
  }

  setFollowOffset(x, y, z) {
    this.followOffset.set(x, y, z);
  }

  setSmoothness(value) {
    this.smoothness = THREE.MathUtils.clamp(value, 0, 1);
  }

  update(deltaTime) {
    if (this.followTarget && this.vrm) {
      const targetWorldPosition = new THREE.Vector3();
      this.followTarget.getWorldPosition(targetWorldPosition);
      
      const idealPosition = targetWorldPosition.clone().add(this.followOffset);
      
      this.camera.position.lerp(idealPosition, this.smoothness);
      this.controls.target.lerp(targetWorldPosition, this.smoothness);
    }
    
    this.controls.update();
  }

  getCamera() {
    return this.camera;
  }

  getControls() {
    return this.controls;
  }

  reset() {
    this.camera.position.set(0, 1.2, 2.5);
    this.controls.target.set(0, 1.2, 0);
    this.controls.update();
  }

  dispose() {
    this.controls.dispose();
  }
}

export default FollowCamera;
