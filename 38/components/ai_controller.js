AFRAME.registerSystem('ai-controller', {
  schema: {
    difficulty: {type: 'string', default: 'normal'},
    enablePunishment: {type: 'boolean', default: true},
    punishmentForce: {type: 'number', default: 12},
    reactionTime: {type: 'number', default: 1500},
    dodgeChance: {type: 'number', default: 0.3}
  },

  init: function () {
    this.isActive = false;
    this.punchingBag = null;
    this.particleSystem = null;
    this.scoreSystem = null;
    
    this.comboCount = 0;
    this.maxCombo = 0;
    this.lastHitTime = 0;
    this.comboTimeout = 2000;
    this.comboTimer = null;
    
    this.hitsReceived = 0;
    this.hitsGiven = 0;
    this.isWaitingForPunishment = false;
    
    this.difficultySettings = {
      easy: {
        dodgeChance: 0.1,
        punishmentForce: 8,
        reactionTime: 3000
      },
      normal: {
        dodgeChance: 0.3,
        punishmentForce: 12,
        reactionTime: 1500
      },
      hard: {
        dodgeChance: 0.5,
        punishmentForce: 16,
        reactionTime: 800
      },
      expert: {
        dodgeChance: 0.7,
        punishmentForce: 20,
        reactionTime: 500
      }
    };
    
    var self = this;
    
    setTimeout(function () {
      self.punchingBag = document.querySelector('#punchingBag');
      self.particleSystem = document.querySelector('#particleSystem');
      self.scoreSystem = self.el.systems['score-system'];
      
      if (self.punchingBag) {
        self.punchingBag.addEventListener('dummy-hit', function (evt) {
          self.handlePlayerHit(evt.detail);
        });
      }
      
      self.startAI();
    }, 500);
    
    this.el.addEventListener('ai-command', function (evt) {
      self.handleCommand(evt.detail);
    });
  },

  startAI: function () {
    this.isActive = true;
    this.applyDifficultySettings();
    console.log('AI 陪练已激活 - 难度: ' + this.data.difficulty);
  },

  stopAI: function () {
    this.isActive = false;
    console.log('AI 陪练已停止');
  },

  setDifficulty: function (difficulty) {
    if (this.difficultySettings[difficulty]) {
      this.data.difficulty = difficulty;
      this.applyDifficultySettings();
      console.log('难度已设置为: ' + difficulty);
      
      if (this.particleSystem) {
        var text = '难度: ' + difficulty.toUpperCase();
        this.showFloatingText(text, '#00FF00');
      }
    }
  },

  applyDifficultySettings: function () {
    var settings = this.difficultySettings[this.data.difficulty];
    if (settings) {
      this.data.dodgeChance = settings.dodgeChance;
      this.data.punishmentForce = settings.punishmentForce;
      this.data.reactionTime = settings.reactionTime;
    }
  },

  handleCommand: function (detail) {
    var action = detail.action;
    
    switch (action) {
      case 'start':
        this.startAI();
        break;
      case 'stop':
        this.stopAI();
        break;
      case 'setDifficulty':
        this.setDifficulty(detail.difficulty);
        break;
      case 'triggerPunishment':
        this.triggerPunishment(detail.direction, detail.force);
        break;
      case 'resetCombo':
        this.resetCombo();
        break;
      case 'getStats':
        return this.getStats();
    }
  },

  handlePlayerHit: function (hitDetail) {
    if (!this.isActive) return;
    
    var now = performance.now();
    
    if (now - this.lastHitTime < this.comboTimeout) {
      this.comboCount++;
    } else {
      this.comboCount = 1;
    }
    
    this.lastHitTime = now;
    this.hitsReceived++;
    
    if (this.comboCount > this.maxCombo) {
      this.maxCombo = this.comboCount;
    }
    
    this.updateComboTimer();
    
    if (this.particleSystem) {
      if (this.comboCount >= 3) {
        this.particleSystem.emit('combo-particle', {combo: this.comboCount});
      }
    }
    
    console.log('连击: ' + this.comboCount + ' / 最高: ' + this.maxCombo);
    
    if (this.data.enablePunishment) {
      this.tryToDodgeOrPunish(hitDetail);
    }
    
    if (this.scoreSystem) {
      this.scoreSystem.updateDisplay();
    }
  },

  updateComboTimer: function () {
    var self = this;
    
    if (this.comboTimer) {
      clearTimeout(this.comboTimer);
    }
    
    this.comboTimer = setTimeout(function () {
      if (self.comboCount > 0) {
        console.log('连击结束 - 最终连击: ' + self.comboCount);
        self.comboCount = 0;
      }
    }, this.comboTimeout);
  },

  resetCombo: function () {
    this.comboCount = 0;
    this.maxCombo = 0;
    this.hitsReceived = 0;
    this.hitsGiven = 0;
    console.log('连击已重置');
  },

  tryToDodgeOrPunish: function (hitDetail) {
    var self = this;
    var dodgeChance = this.data.dodgeChance;
    
    if (Math.random() < dodgeChance) {
      console.log('AI 闪躲成功!');
      this.dodge();
    } else {
      var reactionTime = this.data.reactionTime + Math.random() * 1000;
      
      setTimeout(function () {
        if (self.isActive) {
          self.triggerPunishment(hitDetail.direction);
        }
      }, reactionTime);
    }
  },

  dodge: function () {
    if (!this.punchingBag) return;
    
    var dodgeDirection = Math.random() > 0.5 ? 1 : -1;
    var dodgeAmount = 0.3 + Math.random() * 0.3;
    
    var originalPos = this.punchingBag.components['dummy'].getOriginalPosition();
    var currentPos = this.punchingBag.components['dummy'].getCurrentPosition();
    
    var targetX = currentPos.x + dodgeDirection * dodgeAmount;
    var targetZ = currentPos.z + (Math.random() - 0.5) * 0.2;
    
    this.punchingBag.emit('ai-control', {
      action: 'moveTo',
      x: targetX,
      z: targetZ
    });
    
    var self = this;
    setTimeout(function () {
      self.punchingBag.emit('ai-control', {
        action: 'moveTo',
        x: originalPos.x,
        z: originalPos.z
      });
    }, 1000);
    
    if (this.particleSystem) {
      this.showFloatingText('DODGE!', '#00FFFF');
    }
  },

  triggerPunishment: function (direction, force) {
    if (!this.punchingBag) return;
    
    if (!direction) {
      direction = new THREE.Vector3(0, 0, 1);
    } else {
      direction = direction.clone().negate();
    }
    
    force = force || this.data.punishmentForce;
    
    this.punchingBag.emit('ai-control', {
      action: 'punch',
      direction: direction,
      force: force
    });
    
    this.hitsGiven++;
    
    console.log('AI 反击! 力度: ' + force);
    
    if (this.particleSystem) {
      var position = this.punchingBag.object3D.getWorldPosition(new THREE.Vector3());
      this.particleSystem.emit('ai-punch-particle', {
        position: position,
        direction: direction
      });
      
      this.showFloatingText('反击!', '#FF4500');
    }
  },

  showFloatingText: function (text, color) {
    if (!this.particleSystem || !this.punchingBag) return;
    
    var scene = this.el;
    var textEl = document.createElement('a-entity');
    var position = this.punchingBag.object3D.getWorldPosition(new THREE.Vector3());
    
    textEl.setAttribute('text', 
      'value: ' + text + 
      '; color: ' + color + 
      '; align: center; width: 2; height: 0.5; wrapCount: 10; side: double');
    textEl.setAttribute('position', {
      x: position.x,
      y: position.y + 1.2,
      z: position.z
    });
    textEl.setAttribute('scale', {x: 1, y: 1, z: 1});
    
    scene.appendChild(textEl);
    
    var startTime = performance.now();
    var duration = 1000;
    
    function animateText() {
      var elapsed = performance.now() - startTime;
      var progress = elapsed / duration;
      
      if (progress < 1) {
        textEl.object3D.position.y += 0.008;
        textEl.object3D.scale.set(1 + progress * 0.2, 1 + progress * 0.2, 1 + progress * 0.2);
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

  getStats: function () {
    return {
      comboCount: this.comboCount,
      maxCombo: this.maxCombo,
      hitsReceived: this.hitsReceived,
      hitsGiven: this.hitsGiven,
      difficulty: this.data.difficulty,
      isActive: this.isActive
    };
  },

  getComboCount: function () {
    return this.comboCount;
  },

  getMaxCombo: function () {
    return this.maxCombo;
  }
});

AFRAME.registerComponent('ai-controller', {
  schema: {
    autoStart: {type: 'boolean', default: true}
  },
  
  init: function () {
    var self = this;
    var system = this.el.systems['ai-controller'];
    
    setTimeout(function () {
      if (self.data.autoStart && system) {
        system.startAI();
      }
    }, 1000);
  }
});