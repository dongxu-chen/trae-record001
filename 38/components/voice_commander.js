AFRAME.registerComponent('voice-commander', {
  schema: {
    language: {type: 'string', default: 'zh-CN'},
    continuous: {type: 'boolean', default: true},
    interimResults: {type: 'boolean', default: true}
  },

  init: function () {
    var el = this.el;
    var data = this.data;
    var self = this;
    
    this.isListening = false;
    this.recognition = null;
    this.isSupported = false;
    this.lastCommand = '';
    this.commandHistory = [];
    this.maxHistory = 20;
    
    this.commands = {
      '开始': this.cmdStart,
      '启动': this.cmdStart,
      '开始训练': this.cmdStart,
      '停止': this.cmdStop,
      '结束': this.cmdStop,
      '暂停': this.cmdStop,
      '重置': this.cmdReset,
      '重新开始': this.cmdReset,
      '清零': this.cmdReset,
      '难度简单': this.cmdEasy,
      '简单模式': this.cmdEasy,
      '简单': this.cmdEasy,
      '难度普通': this.cmdNormal,
      '普通模式': this.cmdNormal,
      '普通': this.cmdNormal,
      '难度困难': this.cmdHard,
      '困难模式': this.cmdHard,
      '困难': this.cmdHard,
      '难度专家': this.cmdExpert,
      '专家模式': this.cmdExpert,
      '专家': this.cmdExpert,
      '开启AI': this.cmdEnableAI,
      '关闭AI': this.cmdDisableAI,
      '停止AI': this.cmdDisableAI,
      'AI开启': this.cmdEnableAI,
      'AI关闭': this.cmdDisableAI,
      '查看分数': this.cmdShowScore,
      '分数': this.cmdShowScore,
      '查看统计': this.cmdShowStats,
      '统计': this.cmdShowStats,
      '连击': this.cmdShowCombo,
      '我的连击': this.cmdShowCombo
    };
    
    this.aiController = null;
    this.scoreSystem = null;
    
    setTimeout(function () {
      self.aiController = self.el.systems['ai-controller'];
      self.scoreSystem = self.el.systems['score-system'];
    }, 500);
    
    this.initRecognition();
    
    window.addEventListener('keydown', function (evt) {
      if (evt.code === 'Space' && !self.isListening) {
        self.startListening();
      }
    });
    
    this.createStatusIndicator();
  },

  initRecognition: function () {
    var self = this;
    var data = this.data;
    
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.warn('当前浏览器不支持语音识别 API');
      this.isSupported = false;
      this.updateStatus('不支持语音识别');
      return;
    }
    
    this.isSupported = true;
    this.recognition = new SpeechRecognition();
    this.recognition.lang = data.language;
    this.recognition.continuous = data.continuous;
    this.recognition.interimResults = data.interimResults;
    
    this.recognition.onstart = function () {
      console.log('语音识别已开始');
      self.isListening = true;
      self.updateStatus('正在监听...');
    };
    
    this.recognition.onend = function () {
      console.log('语音识别已结束');
      self.isListening = false;
      self.updateStatus('未在监听');
      
      if (data.continuous) {
        setTimeout(function () {
          if (!self.isListening) {
            self.startListening();
          }
        }, 1000);
      }
    };
    
    this.recognition.onerror = function (event) {
      console.error('语音识别错误:', event.error);
      self.updateStatus('错误: ' + event.error);
      self.isListening = false;
      
      if (event.error === 'not-allowed') {
        self.showFloatingText('请允许麦克风权限', '#FF0000');
      }
    };
    
    this.recognition.onresult = function (event) {
      var result = '';
      var isFinal = false;
      
      for (var i = event.resultIndex; i < event.results.length; ++i) {
        result += event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          isFinal = true;
        }
      }
      
      result = result.trim();
      
      if (result && isFinal) {
        console.log('识别到语音:', result);
        self.lastCommand = result;
        self.commandHistory.push(result);
        
        if (self.commandHistory.length > self.maxHistory) {
          self.commandHistory.shift();
        }
        
        self.processCommand(result);
      }
    };
    
    console.log('语音识别已初始化');
    this.updateStatus('准备就绪');
    
    setTimeout(function () {
      self.startListening();
    }, 2000);
  },

  createStatusIndicator: function () {
    var el = this.el;
    var self = this;
    
    this.statusText = document.createElement('a-entity');
    this.statusText.setAttribute('position', {x: 0, y: 2.8, z: -3});
    this.statusText.setAttribute('text', {
      value: '语音控制: 准备就绪',
      color: '#00FF00',
      align: 'center',
      width: 4,
      height: 0.5,
      wrapCount: 20,
      side: 'double'
    });
    this.statusText.setAttribute('scale', {x: 1, y: 1, z: 1});
    
    el.appendChild(this.statusText);
    
    setTimeout(function () {
      self.updateStatus('语音控制: 准备就绪');
    }, 1000);
  },

  updateStatus: function (message) {
    if (this.statusText) {
      this.statusText.setAttribute('text', 'value', '语音控制: ' + message);
    }
  },

  startListening: function () {
    if (!this.isSupported) {
      console.warn('语音识别不受支持');
      return;
    }
    
    if (this.isListening) {
      console.log('已经在监听中');
      return;
    }
    
    try {
      this.recognition.start();
    } catch (e) {
      console.error('启动语音识别失败:', e);
    }
  },

  stopListening: function () {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
    }
  },

  processCommand: function (text) {
    var textLower = text.toLowerCase();
    var matched = false;
    
    for (var command in this.commands) {
      if (textLower.includes(command.toLowerCase())) {
        this.commands[command].call(this);
        matched = true;
        break;
      }
    }
    
    if (!matched) {
      this.showFloatingText('未识别命令: ' + text, '#FFFF00');
      console.log('未识别的语音命令:', text);
    }
  },

  cmdStart: function () {
    console.log('执行命令: 开始训练');
    this.showFloatingText('开始训练!', '#00FF00');
    
    if (this.aiController) {
      this.aiController.startAI();
    }
  },

  cmdStop: function () {
    console.log('执行命令: 停止');
    this.showFloatingText('已停止', '#FF8C00');
    
    if (this.aiController) {
      this.aiController.stopAI();
    }
  },

  cmdReset: function () {
    console.log('执行命令: 重置');
    this.showFloatingText('已重置', '#00FFFF');
    
    if (this.scoreSystem) {
      this.scoreSystem.reset();
    }
    
    if (this.aiController) {
      this.aiController.resetCombo();
    }
  },

  cmdEasy: function () {
    console.log('执行命令: 难度简单');
    this.setDifficulty('easy', '难度: 简单');
  },

  cmdNormal: function () {
    console.log('执行命令: 难度普通');
    this.setDifficulty('normal', '难度: 普通');
  },

  cmdHard: function () {
    console.log('执行命令: 难度困难');
    this.setDifficulty('hard', '难度: 困难');
  },

  cmdExpert: function () {
    console.log('执行命令: 难度专家');
    this.setDifficulty('expert', '难度: 专家');
  },

  setDifficulty: function (difficulty, message) {
    this.showFloatingText(message, '#00FF00');
    
    if (this.aiController) {
      this.aiController.setDifficulty(difficulty);
    }
  },

  cmdEnableAI: function () {
    console.log('执行命令: 开启AI');
    this.showFloatingText('AI已开启', '#00FF00');
    
    if (this.aiController) {
      this.aiController.startAI();
    }
  },

  cmdDisableAI: function () {
    console.log('执行命令: 关闭AI');
    this.showFloatingText('AI已关闭', '#FF8C00');
    
    if (this.aiController) {
      this.aiController.stopAI();
    }
  },

  cmdShowScore: function () {
    console.log('执行命令: 查看分数');
    
    if (this.scoreSystem) {
      var score = this.scoreSystem.getScore();
      var hits = this.scoreSystem.getHits();
      var avgVelocity = this.scoreSystem.getAverageVelocity();
      
      var message = '得分: ' + score + ' | 击中: ' + hits;
      this.showFloatingText(message, '#FFFFFF');
      
      console.log('分数统计:', {
        score: score,
        hits: hits,
        avgVelocity: avgVelocity
      });
    }
  },

  cmdShowStats: function () {
    console.log('执行命令: 查看统计');
    
    if (this.aiController) {
      var stats = this.aiController.getStats();
      var message = '最高连击: ' + stats.maxCombo;
      this.showFloatingText(message, '#FFD700');
      
      console.log('游戏统计:', stats);
    }
  },

  cmdShowCombo: function () {
    console.log('执行命令: 查看连击');
    
    if (this.aiController) {
      var combo = this.aiController.getComboCount();
      var maxCombo = this.aiController.getMaxCombo();
      
      var message = '当前连击: ' + combo + ' / 最高: ' + maxCombo;
      this.showFloatingText(message, '#FFD700');
    }
  },

  showFloatingText: function (text, color) {
    var scene = this.el;
    var textEl = document.createElement('a-entity');
    
    textEl.setAttribute('text', 
      'value: ' + text + 
      '; color: ' + color + 
      '; align: center; width: 3; height: 0.5; wrapCount: 15; side: double');
    textEl.setAttribute('position', {x: 0, y: 1.8, z: -2});
    textEl.setAttribute('scale', {x: 1, y: 1, z: 1});
    
    scene.appendChild(textEl);
    
    var startTime = performance.now();
    var duration = 2000;
    
    function animateText() {
      var elapsed = performance.now() - startTime;
      var progress = elapsed / duration;
      
      if (progress < 1) {
        textEl.object3D.position.y += 0.005;
        textEl.object3D.scale.set(1 + progress * 0.3, 1 + progress * 0.3, 1 + progress * 0.3);
        textEl.setAttribute('text', 'opacity: ' + (1 - progress * 0.8));
        requestAnimationFrame(animateText);
      } else {
        if (textEl.parentNode) {
          textEl.parentNode.removeChild(textEl);
        }
      }
    }
    
    animateText();
  },

  getLastCommand: function () {
    return this.lastCommand;
  },

  getCommandHistory: function () {
    return this.commandHistory;
  },

  isVoiceSupported: function () {
    return this.isSupported;
  }
});