AFRAME.registerComponent('dummy', {
  schema: {
    swingSpeed: {type: 'number', default: 0.5},
    maxAngle: {type: 'number', default: 15},
    damping: {type: 'number', default: 0.95},
    minSwingVelocity: {type: 'number', default: 0.01},
    enableRandomMovement: {type: 'boolean', default: true},
    movementRange: {type: 'number', default: 0.8},
    movementSpeed: {type: 'number', default: 0.3},
    changeDirectionInterval: {type: 'number', default: 3000},
    yawRange: {type: 'number', default: 20}
  },

  init: function () {
    var el = this.el;
    var data = this.data;
    
    this.originalPosition = el.object3D.position.clone();
    this.swingAngle = 0;
    this.swingVelocity = 0;
    this.swingDirection = new THREE.Vector3(0, 0, 0);
    
    this.isSwinging = false;
    this.swingAxis = new THREE.Vector3(0, 1, 0);
    
    this.hangPoint = new THREE.Vector3(
      this.originalPosition.x,
      this.originalPosition.y + 0.6,
      this.originalPosition.z
    );
    
    this.targetPosition = this.originalPosition.clone();
    this.currentYaw = 0;
    this.targetYaw = 0;
    this.movementEnabled = false;
    
    var chain = document.createElement('a-entity');
    chain.setAttribute('geometry', 'primitive: cylinder; height: 0.6; radius: 0.01');
    chain.setAttribute('material', 'color: #888');
    chain.setAttribute('position', '0 0.9 0');
    el.appendChild(chain);
    
    var ring = document.createElement('a-entity');
    ring.setAttribute('geometry', 'primitive: torus; radius: 0.06; tube: 0.01');
    ring.setAttribute('material', 'color: #888');
    ring.setAttribute('position', '0 1.2 0');
    el.appendChild(ring);
    
    var self = this;
    el.addEventListener('hit', function (evt) {
      self.handleHit(evt.detail);
    });
    
    el.addEventListener('ai-control', function (evt) {
      self.handleAIControl(evt.detail);
    });
    
    if (data.enableRandomMovement) {
      this.startRandomMovement();
    }
    
    this.elapsedTime = 0;
  },

  startRandomMovement: function () {
    var self = this;
    this.movementEnabled = true;
    
    this.movementTimer = setInterval(function () {
      self.setNewTarget();
    }, this.data.changeDirectionInterval);
    
    this.setNewTarget();
  },

  stopRandomMovement: function () {
    this.movementEnabled = false;
    if (this.movementTimer) {
      clearInterval(this.movementTimer);
      this.movementTimer = null;
    }
    this.targetPosition.copy(this.originalPosition);
    this.targetYaw = 0;
  },

  setNewTarget: function () {
    var data = this.data;
    var range = data.movementRange;
    
    this.targetPosition.x = this.originalPosition.x + (Math.random() - 0.5) * 2 * range;
    this.targetPosition.z = this.originalPosition.z + (Math.random() - 0.5) * 2 * range;
    this.targetPosition.y = this.originalPosition.y;
    
    this.targetYaw = (Math.random() - 0.5) * 2 * data.yawRange;
    
    this.targetPosition.x = Math.max(
      this.originalPosition.x - range,
      Math.min(this.originalPosition.x + range, this.targetPosition.x)
    );
    this.targetPosition.z = Math.max(
      this.originalPosition.z - range,
      Math.min(this.originalPosition.z + range, this.targetPosition.z)
    );
  },

  handleHit: function (hitDetail) {
    var velocity = hitDetail.velocity || 5;
    var direction = hitDetail.direction || new THREE.Vector3(0, 0, -1);
    
    var force = Math.min(velocity * 0.3, this.data.maxAngle);
    
    this.swingDirection.copy(direction).normalize();
    this.swingVelocity = force;
    this.isSwinging = true;
    
    this.swingAxis.set(
      -this.swingDirection.z,
      0,
      this.swingDirection.x
    ).normalize();
    
    this.animate();
    
    this.el.emit('dummy-hit', {
      velocity: velocity,
      direction: direction
    });
  },

  handleAIControl: function (detail) {
    if (detail.action === 'moveTo') {
      this.targetPosition.set(detail.x, this.originalPosition.y, detail.z);
    } else if (detail.action === 'enableMovement') {
      if (detail.enabled) {
        this.startRandomMovement();
      } else {
        this.stopRandomMovement();
      }
    } else if (detail.action === 'setMovementRange') {
      this.data.movementRange = detail.range;
    } else if (detail.action === 'resetPosition') {
      this.stopRandomMovement();
      this.targetPosition.copy(this.originalPosition);
      this.targetYaw = 0;
    } else if (detail.action === 'punch') {
      this.triggerAIPunch(detail.direction, detail.force);
    }
  },

  triggerAIPunch: function (direction, force) {
    if (!direction) {
      direction = new THREE.Vector3(0, 0, 1);
    }
    
    force = force || 8;
    
    this.swingDirection.copy(direction).normalize();
    this.swingVelocity = Math.min(force * 0.4, this.data.maxAngle);
    this.isSwinging = true;
    
    this.swingAxis.set(
      -this.swingDirection.z,
      0,
      this.swingDirection.x
    ).normalize();
    
    this.animate();
  },

  animate: function () {
    var self = this;
    var data = this.data;
    var el = this.el;
    
    function updateSwing() {
      if (!self.isSwinging) return;
      
      self.swingAngle += self.swingVelocity;
      self.swingVelocity *= data.damping;
      
      if (Math.abs(self.swingAngle) > data.maxAngle) {
        self.swingAngle = data.maxAngle * Math.sign(self.swingAngle);
        self.swingVelocity = -self.swingVelocity * 0.7;
      }
      
      if (Math.abs(self.swingVelocity) < data.minSwingVelocity && 
          Math.abs(self.swingAngle) < 0.5) {
        self.isSwinging = false;
        self.swingAngle = 0;
        self.swingVelocity = 0;
        return;
      }
      
      requestAnimationFrame(updateSwing);
    }
    
    updateSwing();
  },

  tick: function (time, timeDelta) {
    var el = this.el;
    var data = this.data;
    
    if (!this.movementEnabled) {
      if (this.isSwinging) {
        var rotation = new THREE.Quaternion().setFromAxisAngle(
          this.swingAxis,
          this.swingAngle * Math.PI / 180
        );
        el.object3D.setRotationFromQuaternion(rotation);
      }
      return;
    }
    
    this.elapsedTime += timeDelta;
    
    var currentPos = el.object3D.position;
    var lerpFactor = data.movementSpeed * (timeDelta / 1000);
    
    currentPos.lerp(this.targetPosition, lerpFactor);
    
    var yawDiff = this.targetYaw - this.currentYaw;
    this.currentYaw += yawDiff * lerpFactor;
    
    var rotation = new THREE.Quaternion().setFromAxisAngle(
      this.swingAxis,
      this.swingAngle * Math.PI / 180
    );
    
    var yawRotation = new THREE.Quaternion().setFromAxisAngle(
      new THREE.Vector3(0, 1, 0),
      this.currentYaw * Math.PI / 180
    );
    
    var totalRotation = new THREE.Quaternion().multiplyQuaternions(yawRotation, rotation);
    el.object3D.setRotationFromQuaternion(totalRotation);
  },

  getCurrentPosition: function () {
    return this.el.object3D.position.clone();
  },

  getOriginalPosition: function () {
    return this.originalPosition.clone();
  }
});