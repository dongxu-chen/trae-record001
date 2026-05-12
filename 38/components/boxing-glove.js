AFRAME.registerComponent('boxing-glove', {
  schema: {
    color: {type: 'color', default: '#FF0000'},
    hand: {type: 'string', default: 'right'}
  },

  init: function () {
    var el = this.el;
    var data = this.data;
    var self = this;
    
    this.previousPosition = new THREE.Vector3();
    this.currentVelocity = 0;
    this.lastPosition = null;
    this.hitCooldown = false;
    this.isTracking = false;
    this.validPosition = new THREE.Vector3();
    this.invalidFrameCount = 0;
    this.maxInvalidFrames = 10;
    this.maxValidDistance = 5;
    this.maxPositionChange = 0.5;
    
    this.glove = document.createElement('a-entity');
    this.glove.setAttribute('gltf-model', '');
    this.glove.setAttribute('visible', false);
    
    var gloveGeometry = document.createElement('a-entity');
    gloveGeometry.setAttribute('geometry', 'primitive: sphere; radius: 0.12');
    gloveGeometry.setAttribute('material', 'color: ' + data.color + '; roughness: 0.5; metalness: 0.1');
    gloveGeometry.setAttribute('position', '0 0 -0.08');
    
    var palmGeometry = document.createElement('a-entity');
    palmGeometry.setAttribute('geometry', 'primitive: box; width: 0.16; height: 0.08; depth: 0.2');
    palmGeometry.setAttribute('material', 'color: ' + data.color + '; roughness: 0.5');
    palmGeometry.setAttribute('position', '0 0.02 0.02');
    
    var thumbGeometry = document.createElement('a-entity');
    thumbGeometry.setAttribute('geometry', 'primitive: sphere; radius: 0.05');
    thumbGeometry.setAttribute('material', 'color: ' + data.color + '; roughness: 0.5');
    if (data.hand === 'left') {
      thumbGeometry.setAttribute('position', '-0.1 0.02 0');
    } else {
      thumbGeometry.setAttribute('position', '0.1 0.02 0');
    }
    
    this.glove.appendChild(gloveGeometry);
    this.glove.appendChild(palmGeometry);
    this.glove.appendChild(thumbGeometry);
    
    var hitZone = document.createElement('a-entity');
    hitZone.setAttribute('id', data.hand + '-glove-hit-zone');
    hitZone.setAttribute('class', 'glove');
    hitZone.setAttribute('position', '0 0 -0.12');
    hitZone.setAttribute('scale', '0.15 0.15 0.15');
    hitZone.setAttribute('visible', 'false');
    
    var hitSphere = document.createElement('a-entity');
    hitSphere.setAttribute('geometry', 'primitive: sphere; radius: 1');
    hitSphere.setAttribute('material', 'transparent: true; opacity: 0; wireframe: false');
    hitZone.appendChild(hitSphere);
    
    this.glove.appendChild(hitZone);
    el.appendChild(this.glove);
    
    this.hitZone = hitZone;
    this.glovePosition = new THREE.Vector3();
    
    el.addEventListener('trackedcontrolsconnected', function () {
      console.log('手柄已连接: ' + data.hand);
      self.isTracking = true;
      self.glove.setAttribute('visible', true);
      self.invalidFrameCount = 0;
    });
    
    el.addEventListener('model-loaded', function () {
      console.log('手套模型已加载: ' + data.hand);
    });
    
    var checkConnection = function () {
      var trackedControls = el.components['vive-controls'] || 
                           el.components['oculus-touch-controls'] ||
                           el.components['tracked-controls'];
      if (trackedControls && trackedControls.trackedController) {
        self.isTracking = true;
        self.glove.setAttribute('visible', true);
      }
    };
    
    setTimeout(checkConnection, 500);
    setTimeout(checkConnection, 2000);
  },

  isValidPosition: function (position) {
    if (!position) return false;
    
    if (isNaN(position.x) || isNaN(position.y) || isNaN(position.z)) {
      return false;
    }
    
    if (!isFinite(position.x) || !isFinite(position.y) || !isFinite(position.z)) {
      return false;
    }
    
    var distance = Math.sqrt(
      position.x * position.x + 
      position.y * position.y + 
      position.z * position.z
    );
    if (distance > this.maxValidDistance) {
      return false;
    }
    
    return true;
  },

  isValidPositionChange: function (currentPos, lastPos, timeDelta) {
    if (!lastPos) return true;
    
    var delta = new THREE.Vector3().subVectors(currentPos, lastPos);
    var distance = delta.length();
    var maxAllowed = this.maxPositionChange;
    
    if (timeDelta && timeDelta > 0) {
      var velocity = distance / (timeDelta / 1000);
      return velocity < 100;
    }
    
    return distance < maxAllowed;
  },

  tick: function (time, timeDelta) {
    var el = this.el;
    var object3D = el.object3D;
    var currentPosition = object3D.position.clone();
    
    if (!this.isValidPosition(currentPosition)) {
      this.invalidFrameCount++;
      if (this.invalidFrameCount > this.maxInvalidFrames) {
        this.isTracking = false;
        this.glove.setAttribute('visible', false);
      }
      return;
    }
    
    if (this.lastPosition && 
        !this.isValidPositionChange(currentPosition, this.lastPosition, timeDelta)) {
      this.invalidFrameCount++;
      return;
    }
    
    this.invalidFrameCount = 0;
    this.isTracking = true;
    this.glove.setAttribute('visible', true);
    
    if (!this.lastPosition) {
      this.lastPosition = currentPosition.clone();
      this.validPosition.copy(currentPosition);
      return;
    }
    
    var deltaPosition = new THREE.Vector3().subVectors(currentPosition, this.lastPosition);
    if (timeDelta && timeDelta > 0) {
      this.currentVelocity = deltaPosition.length() / (timeDelta / 1000);
    } else {
      this.currentVelocity = 0;
    }
    
    this.lastPosition.copy(currentPosition);
    this.validPosition.copy(currentPosition);
    
    if (this.hitZone) {
      this.glovePosition.copy(this.hitZone.object3D.getWorldPosition(new THREE.Vector3()));
    }
  },

  getVelocity: function () {
    return this.isTracking ? this.currentVelocity : 0;
  },

  getGlovePosition: function () {
    return this.isTracking ? this.glovePosition : new THREE.Vector3(9999, 9999, 9999);
  },

  isActive: function () {
    return this.isTracking && this.invalidFrameCount <= this.maxInvalidFrames;
  },

  startCooldown: function () {
    this.hitCooldown = true;
    var self = this;
    setTimeout(function () {
      self.hitCooldown = false;
    }, 300);
  }
});