const WhiteboardClient = {
  socket: null,
  canvas: null,
  ctx: null,
  overlayCanvas: null,
  overlayCtx: null,
  currentUser: null,
  roomUsers: [],
  cursorPositions: {},
  cursorElements: {},
  historyManager: null,
  localDrawings: [],
  allDrawings: [],
  
  config: {
    color: DefaultConfig.color,
    brushSize: DefaultConfig.brushSize,
    eraserSize: DefaultConfig.eraserSize,
    fontSize: DefaultConfig.fontSize,
    fillShapes: false
  },
  
  isDrawing: false,
  waitingForText: false,
  textPosition: null,
  shapeStartPos: null,
  currentBrushPoints: [],
  currentEraserPoints: [],
  lastCursorSendTime: 0,
  cursorSendInterval: 50,

  init() {
    this.setupCanvases();
    this.setupEventListeners();
    this.setupHistoryManager();
    ToolManager.init(this.ctx);
  },

  setupCanvases() {
    this.canvas = document.getElementById('whiteboard');
    this.ctx = this.canvas.getContext('2d');
    this.overlayCanvas = document.getElementById('overlay');
    this.overlayCtx = this.overlayCanvas.getContext('2d');
    
    this.resizeCanvases();
    window.addEventListener('resize', () => this.resizeCanvases());
  },

  resizeCanvases() {
    const container = document.querySelector('.canvas-container');
    const oldWidth = this.canvas.width;
    const oldHeight = this.canvas.height;
    
    const imageData = oldWidth > 0 ? this.ctx.getImageData(0, 0, oldWidth, oldHeight) : null;
    
    this.canvas.width = container.clientWidth;
    this.canvas.height = container.clientHeight;
    this.overlayCanvas.width = container.clientWidth;
    this.overlayCanvas.height = container.clientHeight;
    
    ToolManager.updateContext(this.ctx);
    
    if (imageData) {
      this.ctx.putImageData(imageData, 0, 0);
    }
  },

  setupHistoryManager() {
    this.historyManager = new HistoryManager({
      maxStackSize: 100,
      pageSize: 20
    });
    
    this.historyManager.on('change', (data) => {
      this.updateUndoRedoButtons(data);
    });
    
    this.historyManager.on('undo', (operation) => {
      this.handleLocalUndo(operation);
    });
    
    this.historyManager.on('redo', (operation) => {
      this.handleLocalRedo(operation);
    });
  },

  setupEventListeners() {
    this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
    this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    this.canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
    this.canvas.addEventListener('mouseleave', (e) => this.handleMouseUp(e));
    
    this.canvas.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
    this.canvas.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
    this.canvas.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: false });
    this.canvas.addEventListener('touchcancel', (e) => this.handleTouchEnd(e), { passive: false });
    
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        this.undo();
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        this.redo();
      }
      if (this.waitingForText && e.key === 'Enter') {
        this.confirmText();
      }
      if (this.waitingForText && e.key === 'Escape') {
        this.cancelText();
      }
    });
  },

  getCanvasCoords(e) {
    const rect = this.canvas.getBoundingClientRect();
    let clientX, clientY;
    
    if (e.touches && e.touches.length > 0) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else if (e.changedTouches && e.changedTouches.length > 0) {
      clientX = e.changedTouches[0].clientX;
      clientY = e.changedTouches[0].clientY;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }
    
    return {
      x: clientX - rect.left,
      y: clientY - rect.top
    };
  },

  handleTouchStart(e) {
    e.preventDefault();
    this.handleMouseDown(e);
  },

  handleTouchMove(e) {
    e.preventDefault();
    this.handleMouseMove(e);
  },

  handleTouchEnd(e) {
    e.preventDefault();
    this.handleMouseUp(e);
  },

  handleMouseDown(e) {
    if (this.waitingForText) {
      this.confirmText();
    }

    const { x, y } = this.getCanvasCoords(e);
    this.isDrawing = true;
    
    const currentTool = ToolManager.currentToolName;
    
    if (currentTool === ToolTypes.TEXT) {
      this.textPosition = { x, y };
      this.showTextInput(x, y);
      return;
    }
    
    if (currentTool === ToolTypes.RECTANGLE || 
        currentTool === ToolTypes.LINE || 
        currentTool === ToolTypes.CIRCLE) {
      this.shapeStartPos = { x, y };
    }
    
    if (currentTool === ToolTypes.BRUSH) {
      this.currentBrushPoints = [{ x, y }];
      const msg = MessageBuilder.brushStart(x, y, this.config.color, this.config.brushSize);
      this.socket.emit('draw', msg);
      ToolManager.getCurrentTool().start(x, y, { color: this.config.color, size: this.config.brushSize });
    } else if (currentTool === ToolTypes.ERASER) {
      this.currentEraserPoints = [{ x, y }];
      const msg = MessageBuilder.eraserStart(x, y, this.config.eraserSize);
      this.socket.emit('draw', msg);
      ToolManager.getCurrentTool().start(x, y, { size: this.config.eraserSize });
    } else {
      ToolManager.getCurrentTool().start(x, y, {});
    }
  },

  handleMouseMove(e) {
    const { x, y } = this.getCanvasCoords(e);
    const now = Date.now();
    
    if (this.socket && this.socket.connected && now - this.lastCursorSendTime > this.cursorSendInterval) {
      this.socket.emit('cursor_move', MessageBuilder.cursorMove(x, y, ToolManager.currentToolName));
      this.lastCursorSendTime = now;
    }

    if (!this.isDrawing) return;
    
    const currentTool = ToolManager.currentToolName;
    
    if (currentTool === ToolTypes.BRUSH) {
      this.currentBrushPoints.push({ x, y });
      const msg = MessageBuilder.brushMove(x, y, this.config.color, this.config.brushSize);
      this.socket.emit('draw', msg);
      ToolManager.getCurrentTool().move(x, y, { color: this.config.color, size: this.config.brushSize });
    } else if (currentTool === ToolTypes.ERASER) {
      this.currentEraserPoints.push({ x, y });
      const msg = MessageBuilder.eraserMove(x, y, this.config.eraserSize);
      this.socket.emit('draw', msg);
      ToolManager.getCurrentTool().move(x, y, { size: this.config.eraserSize });
    } else if (currentTool === ToolTypes.RECTANGLE || 
               currentTool === ToolTypes.LINE || 
               currentTool === ToolTypes.CIRCLE) {
      this.drawPreviewShape(this.shapeStartPos, { x, y });
    }
  },

  handleMouseUp(e) {
    if (!this.isDrawing) return;
    
    const { x, y } = this.getCanvasCoords(e);
    const currentTool = ToolManager.currentToolName;
    
    if (currentTool === ToolTypes.BRUSH) {
      const msg = MessageBuilder.brushEnd();
      this.socket.emit('draw', msg);
      ToolManager.getCurrentTool().end();
      
      if (this.currentBrushPoints.length > 0) {
        const operation = OperationSerializer.serializeBrushOperation(
          [...this.currentBrushPoints],
          { color: this.config.color, size: this.config.brushSize }
        );
        this.historyManager.record(operation);
        this.currentBrushPoints = [];
      }
    } else if (currentTool === ToolTypes.ERASER) {
      const msg = MessageBuilder.eraserEnd();
      this.socket.emit('draw', msg);
      ToolManager.getCurrentTool().end();
      
      if (this.currentEraserPoints.length > 0) {
        const operation = OperationSerializer.serializeEraserOperation(
          [...this.currentEraserPoints],
          { size: this.config.eraserSize }
        );
        this.historyManager.record(operation);
        this.currentEraserPoints = [];
      }
    } else if (currentTool === ToolTypes.RECTANGLE || 
               currentTool === ToolTypes.LINE || 
               currentTool === ToolTypes.CIRCLE) {
      this.clearOverlay();
      
      const options = {
        color: this.config.color,
        strokeWidth: this.config.brushSize,
        fill: this.config.fillShapes
      };
      
      const result = ToolManager.getCurrentTool().end(x, y, options);
      
      if (result && this.socket) {
        let msg;
        let operation;
        
        if (currentTool === ToolTypes.RECTANGLE) {
          msg = MessageBuilder.rectangle(result.x1, result.y1, result.x2, result.y2, result.color, result.strokeWidth, result.fill);
          operation = OperationSerializer.serializeRectangleOperation(result.x1, result.y1, result.x2, result.y2, options);
        } else if (currentTool === ToolTypes.LINE) {
          msg = MessageBuilder.line(result.x1, result.y1, result.x2, result.y2, result.color, result.strokeWidth);
          operation = OperationSerializer.serializeLineOperation(result.x1, result.y1, result.x2, result.y2, options);
        } else if (currentTool === ToolTypes.CIRCLE) {
          msg = MessageBuilder.circle(result.x1, result.y1, result.x2, result.y2, result.color, result.strokeWidth, result.fill);
          operation = OperationSerializer.serializeCircleOperation(result.x1, result.y1, result.x2, result.y2, options);
        }
        
        if (msg) {
          this.socket.emit('draw', msg);
        }
        if (operation) {
          this.historyManager.record(operation);
        }
      }
      
      this.shapeStartPos = null;
    }
    
    this.isDrawing = false;
  },

  drawPreviewShape(start, end) {
    this.clearOverlay();
    const currentTool = ToolManager.currentToolName;
    
    this.overlayCtx.strokeStyle = this.config.color;
    this.overlayCtx.lineWidth = this.config.brushSize;
    this.overlayCtx.setLineDash([5, 5]);
    
    if (currentTool === ToolTypes.RECTANGLE) {
      this.overlayCtx.beginPath();
      this.overlayCtx.rect(start.x, start.y, end.x - start.x, end.y - start.y);
      this.overlayCtx.stroke();
    } else if (currentTool === ToolTypes.LINE) {
      this.overlayCtx.beginPath();
      this.overlayCtx.moveTo(start.x, start.y);
      this.overlayCtx.lineTo(end.x, end.y);
      this.overlayCtx.stroke();
    } else if (currentTool === ToolTypes.CIRCLE) {
      const centerX = (start.x + end.x) / 2;
      const centerY = (start.y + end.y) / 2;
      const radiusX = Math.abs(end.x - start.x) / 2;
      const radiusY = Math.abs(end.y - start.y) / 2;
      
      this.overlayCtx.beginPath();
      this.overlayCtx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, Math.PI * 2);
      this.overlayCtx.stroke();
    }
  },

  clearOverlay() {
    this.overlayCtx.clearRect(0, 0, this.overlayCanvas.width, this.overlayCanvas.height);
  },

  showTextInput(x, y) {
    this.waitingForText = true;
    
    let input = document.getElementById('text-input');
    if (!input) {
      input = document.createElement('input');
      input.id = 'text-input';
      input.type = 'text';
      input.className = 'text-input';
      input.placeholder = 'Enter text...';
      document.body.appendChild(input);
      
      input.addEventListener('blur', () => this.confirmText());
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') this.confirmText();
        if (e.key === 'Escape') this.cancelText();
      });
    }
    
    const rect = this.canvas.getBoundingClientRect();
    input.style.left = (rect.left + x) + 'px';
    input.style.top = (rect.top + y) + 'px';
    input.style.color = this.config.color;
    input.style.fontSize = this.config.fontSize + 'px';
    input.value = '';
    input.style.display = 'block';
    input.focus();
  },

  confirmText() {
    const input = document.getElementById('text-input');
    if (!input) return;
    
    const text = input.value.trim();
    if (text && this.textPosition) {
      const textTool = ToolManager.getTool(ToolTypes.TEXT);
      const options = {
        color: this.config.color,
        fontSize: this.config.fontSize,
        fontFamily: 'Arial'
      };
      
      const result = textTool.drawText(this.textPosition.x, this.textPosition.y, text, options);
      
      if (this.socket && result) {
        const msg = MessageBuilder.text(result.x, result.y, result.text, result.color, result.fontSize, result.fontFamily);
        this.socket.emit('draw', msg);
        
        const operation = OperationSerializer.serializeTextOperation(
          result.x, result.y, result.text,
          { color: result.color, fontSize: result.fontSize, fontFamily: result.fontFamily }
        );
        this.historyManager.record(operation);
      }
    }
    
    this.hideTextInput();
  },

  cancelText() {
    this.hideTextInput();
  },

  hideTextInput() {
    this.waitingForText = false;
    this.textPosition = null;
    const input = document.getElementById('text-input');
    if (input) {
      input.style.display = 'none';
    }
  },

  connect() {
    this.socket = io();
    this.setupSocketListeners();
  },

  setupSocketListeners() {
    this.socket.on('connect', () => {
      console.log('Connected to server');
    });

    this.socket.on('user_joined', (data) => {
      this.currentUser = data.user;
      this.roomUsers = data.users;
      this.allDrawings = data.drawings || [];
      this.updateUserList();
      this.redrawAll(this.allDrawings);
      this.rebuildHistoryFromDrawings(this.allDrawings);
      console.log('Joined room as', data.user.username);
    });

    this.socket.on('user_joined_broadcast', (data) => {
      this.roomUsers = data.users;
      this.updateUserList();
      this.showNotification(`${data.user.username} 加入了房间`, 'join');
    });

    this.socket.on('user_left', (data) => {
      this.roomUsers = data.users;
      this.removeCursor(data.user.id);
      this.updateUserList();
      this.showNotification(`${data.user.username} 离开了房间`, 'leave');
    });

    this.socket.on('draw', (data) => {
      if (data.userId === this.socket.id) return;
      ToolManager.drawRemote(data);
      this.allDrawings.push(data);
    });

    this.socket.on('cursor_move', (data) => {
      if (data.userId === this.socket.id) return;
      this.updateRemoteCursor(data.userId, data.x, data.y, data.tool);
    });

    this.socket.on('undo', (data) => {
      if (data.userId === this.socket.id) return;
      console.log('Remote undo from', data.userId);
      this.redrawAll(this.allDrawings);
    });

    this.socket.on('redo', (data) => {
      if (data.userId === this.socket.id) return;
      console.log('Remote redo from', data.userId);
    });

    this.socket.on('clear_canvas', (data) => {
      if (data.userId !== this.socket.id) {
        this.clearCanvasLocal();
        this.allDrawings = [];
        this.historyManager.clear();
      }
    });

    this.socket.on('disconnect', () => {
      console.log('Disconnected from server');
    });
  },

  joinRoom(roomId, username) {
    if (!this.socket) {
      this.connect();
    }
    this.socket.emit('join_room', MessageBuilder.joinRoom(roomId, username));
  },

  leaveRoom() {
    if (this.socket) {
      this.socket.emit('leave_room');
    }
    this.historyManager.clear();
    this.allDrawings = [];
  },

  updateRemoteCursor(userId, x, y, tool) {
    let cursorEl = this.cursorElements[userId];
    const user = this.roomUsers.find(u => u.id === userId);
    const userColor = user ? user.color : '#FF6B6B';
    const userName = user ? user.username : 'User';
    const toolIcon = this.getToolIcon(tool);
    
    if (!cursorEl) {
      cursorEl = document.createElement('div');
      cursorEl.className = 'remote-cursor';
      document.body.appendChild(cursorEl);
      this.cursorElements[userId] = cursorEl;
    }
    
    cursorEl.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24">
        <path d="M0 0 L12 12 L6 12 L8 20 L12 14 L16 20 L14 12 L20 12 Z" fill="${userColor}"/>
      </svg>
      <span class="cursor-label" style="background-color: ${userColor}">
        ${toolIcon} ${userName}
      </span>
    `;
    
    const rect = this.canvas.getBoundingClientRect();
    cursorEl.style.left = (rect.left + x) + 'px';
    cursorEl.style.top = (rect.top + y) + 'px';
  },

  getToolIcon(tool) {
    const icons = {
      [ToolTypes.BRUSH]: '🖌️',
      [ToolTypes.ERASER]: '🧹',
      [ToolTypes.RECTANGLE]: '⬜',
      [ToolTypes.LINE]: '📏',
      [ToolTypes.CIRCLE]: '⭕',
      [ToolTypes.TEXT]: '📝'
    };
    return icons[tool] || '✏️';
  },

  removeCursor(userId) {
    const cursorEl = this.cursorElements[userId];
    if (cursorEl) {
      cursorEl.remove();
      delete this.cursorElements[userId];
    }
  },

  updateUserList() {
    const userList = document.getElementById('user-list');
    if (!userList) return;
    
    userList.innerHTML = this.roomUsers.map(user => `
      <div class="user-item" ${user.id === this.socket.id ? 'title="You"' : ''}>
        <span class="user-color" style="background-color: ${user.color}"></span>
        <span class="user-name">${user.username}${user.id === this.socket.id ? ' (你)' : ''}</span>
      </div>
    `).join('');
  },

  redrawAll(drawings) {
    this.clearCanvasLocal();
    drawings.forEach(drawing => {
      ToolManager.drawRemote(drawing);
    });
  },

  rebuildHistoryFromDrawings(drawings) {
  },

  clearCanvasLocal() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  },

  clearCanvas() {
    this.clearCanvasLocal();
    if (this.socket) {
      this.socket.emit('clear_canvas');
    }
    this.historyManager.record(OperationSerializer.serializeClearOperation());
    this.allDrawings = [];
  },

  undo() {
    if (!this.historyManager.canUndo()) return;
    
    const operation = this.historyManager.undo();
    if (operation) {
      if (this.socket) {
        this.socket.emit('undo', MessageBuilder.undo(operation.id));
      }
      this.redrawAllFromHistory();
    }
  },

  redo() {
    if (!this.historyManager.canRedo()) return;
    
    const operation = this.historyManager.redo();
    if (operation) {
      if (this.socket) {
        this.socket.emit('redo', MessageBuilder.redo(operation.id));
      }
      this.redrawAllFromHistory();
    }
  },

  handleLocalUndo(operation) {
    this.redrawAllFromHistory();
  },

  handleLocalRedo(operation) {
    this.redrawAllFromHistory();
  },

  redrawAllFromHistory() {
    this.clearCanvasLocal();
    const allOps = this.historyManager.undoStack;
    
    allOps.forEach(operation => {
      this.executeOperation(operation);
    });
  },

  executeOperation(operation) {
    if (!operation) return;
    
    if (operation.type === HistoryActionTypes.CLEAR) {
      this.clearCanvasLocal();
      return;
    }
    
    switch (operation.tool) {
      case ToolTypes.BRUSH:
        this.replayBrushOperation(operation);
        break;
      case ToolTypes.ERASER:
        this.replayEraserOperation(operation);
        break;
      case ToolTypes.RECTANGLE:
        ToolManager.getTool(ToolTypes.RECTANGLE).drawRemote(operation);
        break;
      case ToolTypes.LINE:
        ToolManager.getTool(ToolTypes.LINE).drawRemote(operation);
        break;
      case ToolTypes.CIRCLE:
        ToolManager.getTool(ToolTypes.CIRCLE).drawRemote(operation);
        break;
      case ToolTypes.TEXT:
        ToolManager.getTool(ToolTypes.TEXT).drawRemote(operation);
        break;
    }
  },

  replayBrushOperation(operation) {
    if (!operation.points || operation.points.length === 0) return;
    
    const tool = ToolManager.getTool(ToolTypes.BRUSH);
    const options = { color: operation.color, size: operation.size };
    
    operation.points.forEach((point, index) => {
      if (index === 0) {
        tool.drawRemote({
          tool: ToolTypes.BRUSH,
          action: DrawingActions.START,
          x: point.x,
          y: point.y,
          color: operation.color,
          size: operation.size
        });
      } else {
        tool.drawRemote({
          tool: ToolTypes.BRUSH,
          action: DrawingActions.MOVE,
          x: point.x,
          y: point.y,
          color: operation.color,
          size: operation.size
        });
      }
    });
    
    tool.drawRemote({
      tool: ToolTypes.BRUSH,
      action: DrawingActions.END
    });
  },

  replayEraserOperation(operation) {
    if (!operation.points || operation.points.length === 0) return;
    
    operation.points.forEach(point => {
      this.ctx.clearRect(
        point.x - operation.size / 2,
        point.y - operation.size / 2,
        operation.size,
        operation.size
      );
    });
  },

  updateUndoRedoButtons(data) {
    const undoBtn = document.getElementById('undo-btn');
    const redoBtn = document.getElementById('redo-btn');
    
    if (undoBtn) {
      undoBtn.disabled = !data.canUndo;
      undoBtn.style.opacity = data.canUndo ? '1' : '0.5';
    }
    if (redoBtn) {
      redoBtn.disabled = !data.canRedo;
      redoBtn.style.opacity = data.canRedo ? '1' : '0.5';
    }
    
    this.updateHistoryPanel();
  },

  updateHistoryPanel() {
    const panel = document.getElementById('history-list');
    if (!panel) return;
    
    const pageData = this.historyManager.getLatestPage();
    if (!pageData) {
      panel.innerHTML = '<div class="history-empty">暂无历史记录</div>';
      return;
    }
    
    const html = pageData.operations
      .slice()
      .reverse()
      .map((op, index) => {
        const isLatest = index === 0 && pageData.page === Math.ceil(pageData.totalCount / pageData.pageSize) - 1;
        return `
          <div class="history-item ${isLatest ? 'latest' : ''}">
            <span class="history-desc">${OperationSerializer.getOperationDescription(op)}</span>
            <span class="history-version">v${op.version}</span>
          </div>
        `;
      })
      .join('');
    
    panel.innerHTML = html || '<div class="history-empty">暂无历史记录</div>';
    
    const pageInfo = document.getElementById('history-page-info');
    if (pageInfo) {
      pageInfo.textContent = `第 ${pageData.page + 1}/${pageData.totalPages || 1} 页 (共 ${pageData.totalCount} 条记录)`;
    }
  },

  showNotification(message, type) {
    const container = document.getElementById('notifications');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    container.appendChild(notification);
    
    setTimeout(() => {
      notification.classList.add('fade-out');
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  },

  setTool(toolName) {
    if (this.waitingForText) {
      this.confirmText();
    }
    ToolManager.setTool(toolName);
    
    document.querySelectorAll('.tool-btn').forEach(btn => {
      btn.classList.remove('active');
      if (btn.dataset.tool === toolName) {
        btn.classList.add('active');
      }
    });
  },

  setColor(color) {
    this.config.color = color;
  },

  setBrushSize(size) {
    this.config.brushSize = parseInt(size);
  },

  setEraserSize(size) {
    this.config.eraserSize = parseInt(size);
  },

  setFontSize(size) {
    this.config.fontSize = parseInt(size);
  },

  setFillShapes(fill) {
    this.config.fillShapes = fill;
  }
};

document.addEventListener('DOMContentLoaded', () => {
  WhiteboardClient.init();
  
  const joinModal = document.getElementById('join-modal');
  const whiteboardApp = document.getElementById('whiteboard-app');
  
  document.getElementById('join-btn').addEventListener('click', () => {
    const roomId = document.getElementById('room-id').value.trim();
    const username = document.getElementById('username').value.trim();
    
    if (!roomId) {
      alert('请输入房间 ID');
      return;
    }
    
    joinModal.style.display = 'none';
    whiteboardApp.style.display = 'flex';
    
    WhiteboardClient.connect();
    setTimeout(() => {
      WhiteboardClient.joinRoom(roomId, username);
    }, 100);
  });
  
  document.querySelectorAll('.tool-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      WhiteboardClient.setTool(btn.dataset.tool);
    });
  });
  
  document.getElementById('color-picker').addEventListener('input', (e) => {
    WhiteboardClient.setColor(e.target.value);
  });
  
  document.getElementById('brush-size').addEventListener('input', (e) => {
    WhiteboardClient.setBrushSize(e.target.value);
    document.getElementById('brush-size-value').textContent = e.target.value;
  });
  
  document.getElementById('eraser-size').addEventListener('input', (e) => {
    WhiteboardClient.setEraserSize(e.target.value);
    document.getElementById('eraser-size-value').textContent = e.target.value;
  });
  
  document.getElementById('font-size').addEventListener('input', (e) => {
    WhiteboardClient.setFontSize(e.target.value);
    document.getElementById('font-size-value').textContent = e.target.value;
  });
  
  document.getElementById('fill-shapes').addEventListener('change', (e) => {
    WhiteboardClient.setFillShapes(e.target.checked);
  });
  
  document.getElementById('undo-btn').addEventListener('click', () => {
    WhiteboardClient.undo();
  });
  
  document.getElementById('redo-btn').addEventListener('click', () => {
    WhiteboardClient.redo();
  });
  
  document.getElementById('history-prev-page').addEventListener('click', () => {
    WhiteboardClient.historyManager.prevPage();
    WhiteboardClient.updateHistoryPanel();
  });
  
  document.getElementById('history-next-page').addEventListener('click', () => {
    WhiteboardClient.historyManager.nextPage();
    WhiteboardClient.updateHistoryPanel();
  });
  
  document.getElementById('clear-btn').addEventListener('click', () => {
    if (confirm('确定要清空画布吗？')) {
      WhiteboardClient.clearCanvas();
    }
  });
  
  document.getElementById('leave-btn').addEventListener('click', () => {
    WhiteboardClient.leaveRoom();
    whiteboardApp.style.display = 'none';
    joinModal.style.display = 'flex';
  });
});
