import * as THREE from 'three';

export class CutAnimator {
  constructor(scene, camera, renderer) {
    this.scene = scene;
    this.camera = camera;
    this.renderer = renderer;
    this.isAnimating = false;
    this.animationProgress = 0;
    this.animationDuration = 2.0;
    this.animationSpeed = 1.0;
    this.animationId = null;
    this.onComplete = null;
    this.onProgress = null;

    this.originalModel = null;
    this.cutPieces = [];
    this.pieceInitialPositions = [];
    this.pieceFinalPositions = [];
    this.cutPlane = null;
    this.cutPlaneMesh = null;

    this.glowMeshes = [];
    this.particleSystem = null;
  }

  startAnimation(originalModel, cutPieces, cutPlane, options = {}) {
    if (this.isAnimating) {
      this.stopAnimation();
    }

    const {
      duration = 2.0,
      speed = 1.0,
      separationDistance = 1.5,
      onComplete = null,
      onProgress = null,
      showGlow = true,
      showParticles = true
    } = options;

    this.originalModel = originalModel;
    this.cutPieces = cutPieces;
    this.cutPlane = cutPlane;
    this.animationDuration = duration;
    this.animationSpeed = speed;
    this.onComplete = onComplete;
    this.onProgress = onProgress;
    this.animationProgress = 0;
    this.isAnimating = true;

    this._calculateFinalPositions(separationDistance);

    if (showGlow && cutPlane) {
      this._createGlowEffect();
    }

    if (showParticles && cutPlane) {
      this._createParticleSystem();
    }

    this._createCutPlaneVisual();

    if (this.originalModel) {
      this.originalModel.visible = true;
    }
    this.cutPieces.forEach(p => { p.visible = false; });

    this._animateLoop();

    return this;
  }

  _calculateFinalPositions(separationDistance) {
    this.pieceInitialPositions = [];
    this.pieceFinalPositions = [];

    if (!this.cutPlane) {
      this.cutPieces.forEach(piece => {
        this.pieceInitialPositions.push(piece.position.clone());
        this.pieceFinalPositions.push(piece.position.clone().add(new THREE.Vector3(separationDistance, 0, 0)));
      });
      return;
    }

    const normal = this.cutPlane.normal.clone().normalize();

    this.cutPieces.forEach((piece, index) => {
      this.pieceInitialPositions.push(piece.position.clone());

      const bbox = new THREE.Box3().setFromObject(piece);
      const center = bbox.getCenter(new THREE.Vector3());
      
      const planeDistance = this.cutPlane.distanceToPoint(center);
      const direction = planeDistance >= 0 ? 1 : -1;
      
      const offset = normal.clone().multiplyScalar(direction * separationDistance);
      this.pieceFinalPositions.push(piece.position.clone().add(offset));
    });
  }

  _createCutPlaneVisual() {
    if (!this.cutPlane || this.cutPlaneMesh) return;

    const size = 8;
    const geometry = new THREE.PlaneGeometry(size, size);
    const material = new THREE.MeshBasicMaterial({
      color: 0xe94560,
      transparent: true,
      opacity: 0.0,
      side: THREE.DoubleSide,
      depthWrite: false
    });

    this.cutPlaneMesh = new THREE.Mesh(geometry, material);
    
    const normal = this.cutPlane.normal.clone();
    const targetNormal = new THREE.Vector3(0, 0, 1);
    const quaternion = new THREE.Quaternion().setFromUnitVectors(targetNormal, normal);
    this.cutPlaneMesh.quaternion.copy(quaternion);
    this.cutPlaneMesh.position.copy(normal.clone().multiplyScalar(-this.cutPlane.constant));

    this.scene.add(this.cutPlaneMesh);
  }

  _createGlowEffect() {
    if (!this.cutPlane) return;

    const normal = this.cutPlane.normal.clone().normalize();
    const size = 6;

    for (let i = 0; i < 3; i++) {
      const geometry = new THREE.PlaneGeometry(size * (1 + i * 0.3), size * (1 + i * 0.3));
      const material = new THREE.MeshBasicMaterial({
        color: 0xe94560,
        transparent: true,
        opacity: 0,
        side: THREE.DoubleSide,
        depthWrite: false,
        blending: THREE.AdditiveBlending
      });

      const glow = new THREE.Mesh(geometry, material);
      const targetNormal = new THREE.Vector3(0, 0, 1);
      const quaternion = new THREE.Quaternion().setFromUnitVectors(targetNormal, normal);
      glow.quaternion.copy(quaternion);
      glow.position.copy(normal.clone().multiplyScalar(-this.cutPlane.constant));
      glow.renderOrder = 1000 + i;

      this.scene.add(glow);
      this.glowMeshes.push(glow);
    }
  }

  _createParticleSystem() {
    if (!this.cutPlane) return;

    const particleCount = 200;
    const positions = new Float32Array(particleCount * 3);
    const velocities = [];

    const normal = this.cutPlane.normal.clone();
    const planePoint = normal.clone().multiplyScalar(-this.cutPlane.constant);
    const size = 3;

    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = planePoint.x + (Math.random() - 0.5) * size;
      positions[i * 3 + 1] = planePoint.y + (Math.random() - 0.5) * size;
      positions[i * 3 + 2] = planePoint.z + (Math.random() - 0.5) * size;

      velocities.push({
        x: (Math.random() - 0.5) * 0.02 + normal.x * 0.01,
        y: (Math.random() - 0.5) * 0.02 + normal.y * 0.01,
        z: (Math.random() - 0.5) * 0.02 + normal.z * 0.01
      });
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));

    const material = new THREE.PointsMaterial({
      color: 0xffd54f,
      size: 0.05,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    this.particleSystem = new THREE.Points(geometry, material);
    this.particleSystem.renderOrder = 1001;
    this.particleSystem.userData.velocities = velocities;
    this.scene.add(this.particleSystem);
  }

  _animateLoop() {
    if (!this.isAnimating) return;

    const deltaTime = 1 / 60;
    this.animationProgress += (deltaTime * this.animationSpeed) / this.animationDuration;

    if (this.animationProgress >= 1.0) {
      this.animationProgress = 1.0;
      this._updateVisuals(1.0);
      this.isAnimating = false;

      if (this.onProgress) this.onProgress(1.0);
      if (this.onComplete) this.onComplete();

      setTimeout(() => this._cleanup(), 500);
      return;
    }

    this._updateVisuals(this.animationProgress);

    if (this.onProgress) this.onProgress(this.animationProgress);

    requestAnimationFrame(() => this._animateLoop());
  }

  _updateVisuals(progress) {
    const sliceStart = 0.0;
    const sliceEnd = 0.4;
    const separateStart = 0.3;
    const separateEnd = 0.8;
    const fadeStart = 0.7;
    const fadeEnd = 1.0;

    if (this.originalModel && this.cutPlane) {
      this.originalModel.visible = progress < separateEnd;
      
      if (progress >= sliceStart && progress < separateEnd) {
        const sliceProgress = Math.min(1, (progress - sliceStart) / (sliceEnd - sliceStart));
        
        const clippingPlanes = [this.cutPlane.clone()];
        this.originalModel.traverse(child => {
          if (child.isMesh && child.material) {
            child.material.clippingPlanes = clippingPlanes;
            child.material.clipShadows = true;
            child.material.needsUpdate = true;
          }
        });
      }
    }

    if (this.cutPlaneMesh) {
      if (progress < separateEnd) {
        const planeOpacity = progress < sliceEnd 
          ? Math.min(0.6, progress * 2) 
          : Math.max(0, 0.6 - (progress - sliceEnd) * 2);
        this.cutPlaneMesh.material.opacity = planeOpacity;
      } else {
        this.cutPlaneMesh.material.opacity = 0;
      }
    }

    this.glowMeshes.forEach((glow, i) => {
      const glowProgress = Math.max(0, progress - i * 0.05);
      if (glowProgress < separateEnd) {
        const intensity = Math.sin(glowProgress * Math.PI) * 0.3 / (i + 1);
        glow.material.opacity = intensity;
      } else {
        glow.material.opacity = Math.max(0, glow.material.opacity - 0.05);
      }
    });

    if (progress >= separateStart) {
      const sepProgress = Math.min(1, (progress - separateStart) / (separateEnd - separateStart));
      const easedProgress = this._easeOutCubic(sepProgress);

      if (this.originalModel && sepProgress > 0.1) {
        this.originalModel.visible = false;
      }

      this.cutPieces.forEach((piece, i) => {
        piece.visible = true;
        const initial = this.pieceInitialPositions[i];
        const final = this.pieceFinalPositions[i];
        piece.position.lerpVectors(initial, final, easedProgress);

        const fadeOpacity = progress > fadeStart
          ? 1 - (progress - fadeStart) / (fadeEnd - fadeStart) * 0.3
          : 1;
        if (piece.material) {
          piece.material.transparent = true;
          piece.material.opacity = fadeOpacity;
        }
      });
    }

    if (this.particleSystem) {
      if (progress >= sliceStart && progress < separateEnd) {
        this.particleSystem.material.opacity = Math.sin(progress * Math.PI) * 0.8;
        
        const positions = this.particleSystem.geometry.getAttribute('position');
        const velocities = this.particleSystem.userData.velocities;
        
        for (let i = 0; i < velocities.length; i++) {
          positions.setX(i, positions.getX(i) + velocities[i].x);
          positions.setY(i, positions.getY(i) + velocities[i].y);
          positions.setZ(i, positions.getZ(i) + velocities[i].z);
        }
        positions.needsUpdate = true;
      } else {
        this.particleSystem.material.opacity = 0;
      }
    }
  }

  _easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  _easeInOutCubic(t) {
    return t < 0.5
      ? 4 * t * t * t
      : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  _cleanup() {
    if (this.cutPlaneMesh) {
      this.scene.remove(this.cutPlaneMesh);
      this.cutPlaneMesh.geometry.dispose();
      this.cutPlaneMesh.material.dispose();
      this.cutPlaneMesh = null;
    }

    this.glowMeshes.forEach(glow => {
      this.scene.remove(glow);
      glow.geometry.dispose();
      glow.material.dispose();
    });
    this.glowMeshes = [];

    if (this.particleSystem) {
      this.scene.remove(this.particleSystem);
      this.particleSystem.geometry.dispose();
      this.particleSystem.material.dispose();
      this.particleSystem = null;
    }

    if (this.originalModel) {
      this.originalModel.traverse(child => {
        if (child.isMesh && child.material) {
          child.material.clippingPlanes = [];
          child.material.clipShadows = false;
          child.material.needsUpdate = true;
        }
      });
    }

    this.cutPieces.forEach(piece => {
      if (piece.material) {
        piece.material.transparent = false;
        piece.material.opacity = 1;
      }
    });
  }

  stopAnimation() {
    this.isAnimating = false;
    this._cleanup();
    this.animationProgress = 0;
  }

  pauseAnimation() {
    this.isAnimating = false;
  }

  resumeAnimation() {
    if (this.animationProgress < 1.0) {
      this.isAnimating = true;
      this._animateLoop();
    }
  }

  setProgress(progress) {
    this.animationProgress = Math.max(0, Math.min(1, progress));
    this._updateVisuals(this.animationProgress);
    if (this.onProgress) this.onProgress(this.animationProgress);
  }

  getProgress() {
    return this.animationProgress;
  }

  isRunning() {
    return this.isAnimating;
  }

  dispose() {
    this.stopAnimation();
    this.scene = null;
    this.camera = null;
    this.renderer = null;
  }
}
