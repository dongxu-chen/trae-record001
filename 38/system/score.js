AFRAME.registerSystem('score-system', {
  schema: {
    pointsPerHit: {type: 'number', default: 10},
    velocityMultiplier: {type: 'number', default: 2},
    localStorageKey: {type: 'string', default: 'webvr-boxing-score'}
  },

  init: function () {
    this.score = 0;
    this.hits = 0;
    this.totalVelocity = 0;
    this.scoreDisplay = null;
    this.comboDisplay = null;
    this.isLoaded = false;
    this.aiController = null;
    
    this.loadFromLocalStorage();
    
    var self = this;
    setTimeout(function () {
      self.scoreDisplay = document.querySelector('[score-display]');
      self.comboDisplay = document.querySelector('#comboDisplay');
      self.aiController = self.el.systems['ai-controller'];
      self.updateDisplay();
    }, 100);
    
    window.addEventListener('beforeunload', function () {
      self.saveToLocalStorage();
    });
    
    setInterval(function () {
      self.saveToLocalStorage();
    }, 5000);
  },

  loadFromLocalStorage: function () {
    try {
      if (typeof localStorage === 'undefined') {
        console.warn('localStorage 不可用');
        return;
      }
      
      var key = this.data.localStorageKey;
      var savedData = localStorage.getItem(key);
      
      if (savedData) {
        var data = JSON.parse(savedData);
        this.score = data.score || 0;
        this.hits = data.hits || 0;
        this.totalVelocity = data.totalVelocity || 0;
        this.isLoaded = true;
        console.log('分数已从 localStorage 恢复:', {
          score: this.score,
          hits: this.hits,
          avgVelocity: this.hits > 0 ? (this.totalVelocity / this.hits).toFixed(2) : 0
        });
      } else {
        console.log('没有找到保存的分数数据');
        this.isLoaded = true;
      }
    } catch (e) {
      console.error('从 localStorage 加载失败:', e);
      this.isLoaded = true;
    }
  },

  saveToLocalStorage: function () {
    try {
      if (typeof localStorage === 'undefined') {
        return;
      }
      
      if (!this.isLoaded) {
        return;
      }
      
      var key = this.data.localStorageKey;
      var dataToSave = {
        score: this.score,
        hits: this.hits,
        totalVelocity: this.totalVelocity,
        savedAt: Date.now()
      };
      
      localStorage.setItem(key, JSON.stringify(dataToSave));
    } catch (e) {
      console.error('保存到 localStorage 失败:', e);
    }
  },

  addHit: function (hitData) {
    var data = this.data;
    var velocity = hitData.velocity || 5;
    
    var basePoints = data.pointsPerHit;
    var velocityBonus = Math.floor(velocity * data.velocityMultiplier);
    var totalPoints = basePoints + velocityBonus;
    
    this.score += totalPoints;
    this.hits++;
    this.totalVelocity += velocity;
    
    console.log('击中! +' + totalPoints + ' 分' + ' (速度: ' + velocity.toFixed(2) + ' m/s)');
    
    this.updateDisplay();
    this.playHitSound();
    this.saveToLocalStorage();
  },

  updateDisplay: function () {
    var self = this;
    
    if (this.scoreDisplay) {
      var comboText = '';
      var difficulty = '普通';
      
      if (this.aiController) {
        var combo = this.aiController.getComboCount();
        var maxCombo = this.aiController.getMaxCombo();
        var stats = this.aiController.getStats();
        
        if (stats.difficulty === 'easy') difficulty = '简单';
        else if (stats.difficulty === 'hard') difficulty = '困难';
        else if (stats.difficulty === 'expert') difficulty = '专家';
        
        if (combo > 0) {
          comboText = '\n连击: ' + combo + ' (最高: ' + maxCombo + ')';
        }
      }
      
      var text = '得分: ' + this.score + 
                '\n击中: ' + this.hits + 
                comboText +
                '\n难度: ' + difficulty +
                (this.hits > 0 ? '\n平均速度: ' + (this.totalVelocity / this.hits).toFixed(2) + ' m/s' : '');
      
      this.scoreDisplay.setAttribute('text', 'value', text);
      
      this.scoreDisplay.object3D.scale.set(1.1, 1.1, 1.1);
      setTimeout(function () {
        if (self.scoreDisplay) {
          self.scoreDisplay.object3D.scale.set(1, 1, 1);
        }
      }, 100);
    }
    
    this.updateComboDisplay();
  },

  updateComboDisplay: function () {
    if (this.comboDisplay) {
      var combo = 0;
      var maxCombo = 0;
      
      if (this.aiController) {
        combo = this.aiController.getComboCount();
        maxCombo = this.aiController.getMaxCombo();
      }
      
      var color = '#FFFFFF';
      var text = '连击: ' + combo;
      
      if (combo >= 10) {
        color = '#FF0000';
        text = '★ LEGENDARY ★\n' + combo + ' HIT COMBO!';
      } else if (combo >= 7) {
        color = '#FF4500';
        text = '★ AMAZING ★\n' + combo + ' HIT COMBO!';
      } else if (combo >= 5) {
        color = '#FF8C00';
        text = '★ GREAT ★\n' + combo + ' HIT COMBO!';
      } else if (combo >= 3) {
        color = '#FFD700';
        text = '★ COMBO ★\n' + combo + ' HITS!';
      }
      
      this.comboDisplay.setAttribute('text', {
        value: text,
        color: color
      });
    }
  },

  getScore: function () {
    return this.score;
  },

  getHits: function () {
    return this.hits;
  },

  getAverageVelocity: function () {
    if (this.hits === 0) return 0;
    return this.totalVelocity / this.hits;
  },

  reset: function () {
    this.score = 0;
    this.hits = 0;
    this.totalVelocity = 0;
    
    if (this.aiController) {
      this.aiController.resetCombo();
    }
    
    this.updateDisplay();
    this.saveToLocalStorage();
    console.log('分数已重置并保存');
  },

  clearSavedData: function () {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(this.data.localStorageKey);
        console.log('localStorage 中的分数数据已清除');
      }
    } catch (e) {
      console.error('清除 localStorage 数据失败:', e);
    }
  },

  playHitSound: function () {
    try {
      var audioContext = new (window.AudioContext || window.webkitAudioContext)();
      var oscillator = audioContext.createOscillator();
      var gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.value = 440 + (Math.random() * 200 - 100);
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.1);
    } catch (e) {
      console.warn('播放音效失败:', e);
    }
  }
});

AFRAME.registerComponent('score-display', {
  schema: {},
  
  init: function () {
    var system = this.el.sceneEl.systems['score-system'];
    if (system && system.scoreDisplay === null) {
      system.scoreDisplay = this.el;
    }
  }
});