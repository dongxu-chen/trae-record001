AFRAME.registerComponent('hit-detector', {
  schema: {
    radius: {type: 'number', default: 0.5},
    minHitVelocity: {type: 'number', default: 3},
    exitRadius: {type: 'number', default: 0.7}
  },

  init: function () {
    var el = this.el;
    this.targetEl = el.parentNode;
    
    this.targetPosition = new THREE.Vector3();
    this.lastLeftHit = 0;
    this.lastRightHit = 0;
    this.hitCooldown = 500;
    this.minTimeBetweenHits = 300;
    
    this.leftGlove = null;
    this.rightGlove = null;
    
    this.leftGloveInZone = false;
    this.rightGloveInZone = false;
    this.leftCanHit = true;
    this.rightCanHit = true;
    
    var self = this;
    
    setTimeout(function () {
      self.leftGlove = document.querySelector('#leftHand');
      self.rightGlove = document.querySelector('#rightHand');
    }, 100);
  },

  tick: function (time) {
    var el = this.el;
    var targetEl = this.targetEl;
    var data = this.data;
    
    if (!targetEl) return;
    
    targetEl.object3D.getWorldPosition(this.targetPosition);
    
    this.checkGloveHit(time, this.leftGlove, 'left');
    this.checkGloveHit(time, this.rightGlove, 'right');
  },

  isGloveInHitZone: function (glovePosition, radius) {
    var distance = glovePosition.distanceTo(this.targetPosition);
    return distance < radius;
  },

  checkGloveHit: function (time, gloveEl, hand) {
    if (!gloveEl) return;
    
    var data = this.data;
    var boxingGlove = gloveEl.components['boxing-glove'];
    
    if (!boxingGlove || !boxingGlove.isActive()) return;
    
    var glovePosition = boxingGlove.getGlovePosition();
    var isInHitZone = this.isGloveInHitZone(glovePosition, data.radius + 0.15);
    var isInExitZone = this.isGloveInHitZone(glovePosition, data.exitRadius);
    
    var inZone = (hand === 'left') ? this.leftGloveInZone : this.rightGloveInZone;
    var canHit = (hand === 'left') ? this.leftCanHit : this.rightCanHit;
    
    if (!isInExitZone) {
      if (hand === 'left') {
        this.leftGloveInZone = false;
        this.leftCanHit = true;
      } else {
        this.rightGloveInZone = false;
        this.rightCanHit = true;
      }
      return;
    }
    
    if (isInHitZone) {
      if (hand === 'left') {
        this.leftGloveInZone = true;
      } else {
        this.rightGloveInZone = true;
      }
      
      if (!inZone && canHit) {
        var velocity = boxingGlove.getVelocity();
        
        if (velocity > data.minHitVelocity) {
          var lastHitTime = (hand === 'left') ? this.lastLeftHit : this.lastRightHit;
          
          if (time - lastHitTime > this.hitCooldown) {
            this.triggerHit(gloveEl, velocity);
            
            if (hand === 'left') {
              this.lastLeftHit = time;
              this.leftCanHit = false;
            } else {
              this.lastRightHit = time;
              this.rightCanHit = false;
            }
          }
        }
      }
    }
  },

  triggerHit: function (gloveEl, velocity) {
    var targetEl = this.targetEl;
    var boxingGlove = gloveEl.components['boxing-glove'];
    
    var targetPos = this.targetPosition.clone();
    var glovePos = boxingGlove.getGlovePosition().clone();
    
    var direction = new THREE.Vector3().subVectors(targetPos, glovePos).normalize();
    
    targetEl.emit('hit', {
      velocity: velocity,
      direction: direction,
      hand: gloveEl.components['boxing-glove'].data.hand
    });
    
    boxingGlove.startCooldown();
    
    var scene = targetEl.sceneEl;
    if (scene && scene.components['score-system']) {
      scene.components['score-system'].addHit({
        velocity: velocity,
        hand: gloveEl.components['boxing-glove'].data.hand
      });
    }
    
    this.showHitEffect();
  },

  showHitEffect: function () {
    var el = this.el;
    var hitEffect = document.createElement('a-entity');
    hitEffect.setAttribute('position', this.targetPosition);
    hitEffect.setAttribute('scale', '1 1 1');
    
    var ring = document.createElement('a-entity');
    ring.setAttribute('geometry', 'primitive: torus; radius: 0.2; tube: 0.02');
    ring.setAttribute('material', 'color: #FFD700; transparent: true; opacity: 0.8; emissive: #FFD700; emissiveIntensity: 2');
    hitEffect.appendChild(ring);
    
    var glow = document.createElement('a-entity');
    glow.setAttribute('geometry', 'primitive: sphere; radius: 0.1');
    glow.setAttribute('material', 'color: #FFD700; transparent: true; opacity: 0.6');
    hitEffect.appendChild(glow);
    
    el.sceneEl.appendChild(hitEffect);
    
    var startTime = performance.now();
    var duration = 500;
    
    function animateEffect() {
      var elapsed = performance.now() - startTime;
      var progress = elapsed / duration;
      
      if (progress < 1) {
        var scale = 1 + progress * 2;
        hitEffect.setAttribute('scale', {x: scale, y: scale, z: scale});
        
        ring.setAttribute('material', {opacity: 0.8 * (1 - progress)});
        glow.setAttribute('material', {opacity: 0.6 * (1 - progress)});
        
        requestAnimationFrame(animateEffect);
      } else {
        if (hitEffect.parentNode) {
          hitEffect.parentNode.removeChild(hitEffect);
        }
      }
    }
    
    animateEffect();
  }
});