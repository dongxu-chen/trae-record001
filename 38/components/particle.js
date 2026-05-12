AFRAME.registerComponent('particle-effect', {
  schema: {
    type: {type: 'string', default: 'hit'},
    color: {type: 'color', default: '#FFD700'},
    particleCount: {type: 'number', default: 20},
    size: {type: 'number', default: 0.05},
    duration: {type: 'number', default: 800},
    speed: {type: 'number', default: 2},
    gravity: {type: 'number', default: 5}
  },

  init: function () {
    var el = this.el;
    var data = this.data;
    
    this.particles = [];
    this.particleEntities = [];
    this.isPlaying = false;
    this.startTime = 0;
    
    var self = this;
    el.addEventListener('trigger-particle', function (evt) {
      if (evt.detail.type) {
        data.type = evt.detail.type;
      }
      if (evt.detail.position) {
        self.trigger(evt.detail.position);
      } else {
        self.trigger();
      }
    });
    
    el.addEventListener('combo-particle', function (evt) {
      self.triggerComboEffect(evt.detail.combo);
    });
    
    el.addEventListener('ai-punch-particle', function (evt) {
      self.triggerAIPunch(evt.detail.position, evt.detail.direction);
    });
  },

  createParticleGeometry: function (type) {
    var data = this.data;
    
    switch (type) {
      case 'spark':
        return 'primitive: box; width: ' + data.size + 
               '; height: ' + (data.size * 3) + 
               '; depth: ' + data.size;
      case 'ring':
        return 'primitive: torus; radius: ' + (data.size * 2) + 
               '; tube: ' + (data.size * 0.3);
      case 'star':
      default:
        return 'primitive: sphere; radius: ' + data.size;
    }
  },

  trigger: function (position) {
    var el = this.el;
    var data = this.data;
    var scene = el.sceneEl;
    
    if (!position) {
      position = el.object3D.getWorldPosition(new THREE.Vector3());
    }
    
    this.isPlaying = true;
    this.startTime = performance.now();
    this.particles = [];
    this.particleEntities = [];
    
    for (var i = 0; i < data.particleCount; i++) {
      var particle = {
        position: position.clone(),
        velocity: new THREE.Vector3(
          (Math.random() - 0.5) * 2 * data.speed,
          Math.random() * data.speed + 0.5,
          (Math.random() - 0.5) * 2 * data.speed
        ),
        rotation: new THREE.Vector3(
          Math.random() * Math.PI * 2,
          Math.random() * Math.PI * 2,
          Math.random() * Math.PI * 2
        ),
        rotationSpeed: new THREE.Vector3(
          (Math.random() - 0.5) * 10,
          (Math.random() - 0.5) * 10,
          (Math.random() - 0.5) * 10
        ),
        scale: data.size,
        opacity: 1.0,
        color: this.getParticleColor(data.type, i)
      };
      
      this.particles.push(particle);
      
      var particleEl = document.createElement('a-entity');
      particleEl.setAttribute('geometry', this.createParticleGeometry(data.type));
      particleEl.setAttribute('material', 
        'color: ' + particle.color + '; transparent: true; opacity: 1; emissive: ' + particle.color + '; emissiveIntensity: 2');
      particleEl.setAttribute('position', particle.position);
      
      scene.appendChild(particleEl);
      this.particleEntities.push(particleEl);
    }
    
    this.animate();
  },

  triggerComboEffect: function (comboCount) {
    var el = this.el;
    var scene = el.sceneEl;
    var position = el.object3D.getWorldPosition(new THREE.Vector3());
    
    var intensity = Math.min(comboCount, 10);
    var particleCount = 10 + intensity * 5;
    var size = 0.05 + intensity * 0.01;
    var speed = 2 + intensity * 0.5;
    var duration = 800 + intensity * 100;
    
    this.isPlaying = true;
    this.startTime = performance.now();
    this.particles = [];
    this.particleEntities = [];
    
    var comboColor;
    if (comboCount >= 10) {
      comboColor = '#FF0000';
    } else if (comboCount >= 7) {
      comboColor = '#FF4500';
    } else if (comboCount >= 5) {
      comboColor = '#FF8C00';
    } else if (comboCount >= 3) {
      comboColor = '#FFD700';
    } else {
      comboColor = '#FFFFFF';
    }
    
    for (var i = 0; i < particleCount; i++) {
      var angle = (i / particleCount) * Math.PI * 2;
      var ringRadius = 0.1 + Math.random() * 0.2;
      
      var particle = {
        position: position.clone(),
        velocity: new THREE.Vector3(
          Math.cos(angle) * ringRadius * speed * 2 + (Math.random() - 0.5),
          Math.random() * speed + 1,
          Math.sin(angle) * ringRadius * speed * 2 + (Math.random() - 0.5)
        ),
        rotation: new THREE.Vector3(
          Math.random() * Math.PI * 2,
          Math.random() * Math.PI * 2,
          Math.random() * Math.PI * 2
        ),
        rotationSpeed: new THREE.Vector3(
          (Math.random() - 0.5) * 15,
          (Math.random() - 0.5) * 15,
          (Math.random() - 0.5) * 15
        ),
        scale: size,
        opacity: 1.0,
        color: comboColor
      };
      
      this.particles.push(particle);
      
      var particleEl = document.createElement('a-entity');
      particleEl.setAttribute('geometry', 'primitive: sphere; radius: ' + size);
      particleEl.setAttribute('material', 
        'color: ' + particle.color + '; transparent: true; opacity: 1; emissive: ' + particle.color + '; emissiveIntensity: 3');
      particleEl.setAttribute('position', particle.position);
      
      scene.appendChild(particleEl);
      this.particleEntities.push(particleEl);
    }
    
    this.showComboText(comboCount, position);
    this.animateCustom(duration);
  },

  showComboText: function (comboCount, position) {
    var scene = this.el.sceneEl;
    var textEl = document.createElement('a-entity');
    
    var comboText;
    if (comboCount >= 10) {
      comboText = 'LEGENDARY!';
    } else if (comboCount >= 7) {
      comboText = 'AMAZING!';
    } else if (comboCount >= 5) {
      comboText = 'GREAT!';
    } else if (comboCount >= 3) {
      comboText = 'COMBO x' + comboCount;
    } else {
      return;
    }
    
    var textColor;
    if (comboCount >= 10) {
      textColor = '#FF0000';
    } else if (comboCount >= 7) {
      textColor = '#FF4500';
    } else if (comboCount >= 5) {
      textColor = '#FF8C00';
    } else {
      textColor = '#FFD700';
    }
    
    textEl.setAttribute('text', 
      'value: ' + comboText + 
      '; color: ' + textColor + 
      '; align: center; width: 3; height: 1; wrapCount: 15; side: double');
    textEl.setAttribute('position', {
      x: position.x,
      y: position.y + 0.8,
      z: position.z
    });
    textEl.setAttribute('scale', {x: 1, y: 1, z: 1});
    
    scene.appendChild(textEl);
    
    var startTime = performance.now();
    var duration = 1500;
    
    function animateText() {
      var elapsed = performance.now() - startTime;
      var progress = elapsed / duration;
      
      if (progress < 1) {
        textEl.object3D.position.y += 0.005;
        textEl.object3D.scale.set(1 + progress * 0.3, 1 + progress * 0.3, 1 + progress * 0.3);
        textEl.setAttribute('text', 'opacity: ' + (1 - progress));
        requestAnimationFrame(animateText);
      } else {
        if (textEl.parentNode) {
          textEl.parentNode.removeChild(textEl);
        }
      }
    }
    
    animateText();
  },

  triggerAIPunch: function (position, direction) {
    var el = this.el;
    var scene = el.sceneEl;
    var data = this.data;
    
    if (!position) {
      position = el.object3D.getWorldPosition(new THREE.Vector3());
    }
    
    if (!direction) {
      direction = new THREE.Vector3(0, 0, 1);
    }
    
    this.isPlaying = true;
    this.startTime = performance.now();
    this.particles = [];
    this.particleEntities = [];
    
    for (var i = 0; i < 15; i++) {
      var angle = (Math.random() - 0.5) * 0.5;
      var dir = direction.clone().normalize();
      
      var particle = {
        position: position.clone(),
        velocity: new THREE.Vector3(
          dir.x * data.speed + (Math.random() - 0.5),
          dir.y * data.speed + (Math.random() - 0.5) + 1,
          dir.z * data.speed + (Math.random() - 0.5)
        ),
        rotation: new THREE.Vector3(
          Math.random() * Math.PI * 2,
          Math.random() * Math.PI * 2,
          Math.random() * Math.PI * 2
        ),
        rotationSpeed: new THREE.Vector3(
          (Math.random() - 0.5) * 10,
          (Math.random() - 0.5) * 10,
          (Math.random() - 0.5) * 10
        ),
        scale: data.size,
        opacity: 1.0,
        color: '#FF4500'
      };
      
      this.particles.push(particle);
      
      var particleEl = document.createElement('a-entity');
      particleEl.setAttribute('geometry', 'primitive: sphere; radius: ' + data.size);
      particleEl.setAttribute('material', 
        'color: ' + particle.color + '; transparent: true; opacity: 1; emissive: ' + particle.color + '; emissiveIntensity: 2');
      particleEl.setAttribute('position', particle.position);
      
      scene.appendChild(particleEl);
      this.particleEntities.push(particleEl);
    }
    
    this.animate();
  },

  getParticleColor: function (type, index) {
    var data = this.data;
    
    if (type === 'hit') {
      var colors = ['#FFD700', '#FFA500', '#FF8C00', '#FFFF00', '#FF6347'];
      return colors[index % colors.length];
    } else if (type === 'spark') {
      var whiteColors = ['#FFFFFF', '#FFFACD', '#FFFFE0', '#FFF8DC'];
      return whiteColors[index % whiteColors.length];
    } else {
      return data.color;
    }
  },

  animate: function () {
    var self = this;
    var data = this.data;
    
    function update() {
      if (!self.isPlaying) return;
      
      var elapsed = performance.now() - self.startTime;
      var progress = elapsed / data.duration;
      
      if (progress >= 1) {
        self.cleanup();
        return;
      }
      
      var dt = 1 / 60;
      
      for (var i = 0; i < self.particles.length; i++) {
        var p = self.particles[i];
        var el = self.particleEntities[i];
        
        p.velocity.y -= data.gravity * dt;
        p.position.add(p.velocity.clone().multiplyScalar(dt));
        
        p.rotation.add(p.rotationSpeed.clone().multiplyScalar(dt));
        
        p.opacity = 1 - progress;
        var currentScale = p.scale * (1 + progress * 0.5);
        
        el.setAttribute('position', p.position);
        el.setAttribute('rotation', {
          x: p.rotation.x * 180 / Math.PI,
          y: p.rotation.y * 180 / Math.PI,
          z: p.rotation.z * 180 / Math.PI
        });
        el.setAttribute('material', 'opacity: ' + p.opacity);
        el.setAttribute('scale', {x: currentScale, y: currentScale, z: currentScale});
      }
      
      requestAnimationFrame(update);
    }
    
    update();
  },

  animateCustom: function (duration) {
    var self = this;
    var data = this.data;
    
    function update() {
      if (!self.isPlaying) return;
      
      var elapsed = performance.now() - self.startTime;
      var progress = elapsed / duration;
      
      if (progress >= 1) {
        self.cleanup();
        return;
      }
      
      var dt = 1 / 60;
      
      for (var i = 0; i < self.particles.length; i++) {
        var p = self.particles[i];
        var el = self.particleEntities[i];
        
        p.velocity.y -= data.gravity * dt * 0.5;
        p.position.add(p.velocity.clone().multiplyScalar(dt));
        
        p.rotation.add(p.rotationSpeed.clone().multiplyScalar(dt));
        
        p.opacity = 1 - progress;
        var currentScale = p.scale * (1 + progress * 0.8);
        
        el.setAttribute('position', p.position);
        el.setAttribute('rotation', {
          x: p.rotation.x * 180 / Math.PI,
          y: p.rotation.y * 180 / Math.PI,
          z: p.rotation.z * 180 / Math.PI
        });
        el.setAttribute('material', 'opacity: ' + p.opacity);
        el.setAttribute('scale', {x: currentScale, y: currentScale, z: currentScale});
      }
      
      requestAnimationFrame(update);
    }
    
    update();
  },

  cleanup: function () {
    this.isPlaying = false;
    
    for (var i = 0; i < this.particleEntities.length; i++) {
      var el = this.particleEntities[i];
      if (el && el.parentNode) {
        el.parentNode.removeChild(el);
      }
    }
    
    this.particles = [];
    this.particleEntities = [];
  }
});