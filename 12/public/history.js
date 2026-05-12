const HistoryActionTypes = {
  DRAW: 'draw',
  CLEAR: 'clear',
  UNDO: 'undo',
  REDO: 'redo'
};

class HistoryManager {
  constructor(options = {}) {
    this.maxStackSize = options.maxStackSize || 100;
    this.pageSize = options.pageSize || 20;
    this.undoStack = [];
    this.redoStack = [];
    this.allOperations = [];
    this.currentPage = 0;
    this.listeners = new Map();
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  emit(event, data) {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach(cb => cb(data));
    }
  }

  record(action) {
    const record = {
      id: Date.now() + '_' + Math.random().toString(36).substr(2, 9),
      ...action,
      timestamp: Date.now(),
      version: this.allOperations.length + 1
    };

    this.undoStack.push(record);
    this.allOperations.push(record);
    this.redoStack = [];

    if (this.undoStack.length > this.maxStackSize) {
      this.undoStack.shift();
    }

    this.emit('change', {
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      totalCount: this.allOperations.length
    });

    return record;
  }

  canUndo() {
    return this.undoStack.length > 0;
  }

  canRedo() {
    return this.redoStack.length > 0;
  }

  undo() {
    if (!this.canUndo()) return null;

    const action = this.undoStack.pop();
    this.redoStack.push(action);

    this.emit('change', {
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      totalCount: this.allOperations.length
    });

    this.emit('undo', action);

    return action;
  }

  redo() {
    if (!this.canRedo()) return null;

    const action = this.redoStack.pop();
    this.undoStack.push(action);

    this.emit('change', {
      canUndo: this.canUndo(),
      canRedo: this.canRedo(),
      totalCount: this.allOperations.length
    });

    this.emit('redo', action);

    return action;
  }

  getCurrentVersion() {
    return this.allOperations.length;
  }

  getOperationsByPage(page = 0) {
    const start = page * this.pageSize;
    const end = start + this.pageSize;
    const pageData = this.allOperations.slice(start, end);
    
    return {
      operations: pageData,
      page,
      pageSize: this.pageSize,
      totalPages: Math.ceil(this.allOperations.length / this.pageSize),
      totalCount: this.allOperations.length,
      hasNext: end < this.allOperations.length,
      hasPrev: page > 0
    };
  }

  getLatestPage() {
    const totalPages = Math.ceil(this.allOperations.length / this.pageSize);
    this.currentPage = Math.max(0, totalPages - 1);
    return this.getOperationsByPage(this.currentPage);
  }

  nextPage() {
    const totalPages = Math.ceil(this.allOperations.length / this.pageSize);
    if (this.currentPage < totalPages - 1) {
      this.currentPage++;
      return this.getOperationsByPage(this.currentPage);
    }
    return null;
  }

  prevPage() {
    if (this.currentPage > 0) {
      this.currentPage--;
      return this.getOperationsByPage(this.currentPage);
    }
    return null;
  }

  goToPage(page) {
    const totalPages = Math.ceil(this.allOperations.length / this.pageSize);
    if (page >= 0 && page < totalPages) {
      this.currentPage = page;
      return this.getOperationsByPage(this.currentPage);
    }
    return null;
  }

  getOperationById(id) {
    return this.allOperations.find(op => op.id === id);
  }

  getOperationsSinceVersion(version) {
    return this.allOperations.filter(op => op.version > version);
  }

  clear() {
    this.undoStack = [];
    this.redoStack = [];
    this.allOperations = [];
    this.currentPage = 0;

    this.emit('change', {
      canUndo: false,
      canRedo: false,
      totalCount: 0
    });

    this.emit('clear');
  }

  getStats() {
    return {
      undoStackSize: this.undoStack.length,
      redoStackSize: this.redoStack.length,
      totalOperations: this.allOperations.length,
      currentPage: this.currentPage,
      maxStackSize: this.maxStackSize,
      pageSize: this.pageSize,
      canUndo: this.canUndo(),
      canRedo: this.canRedo()
    };
  }
}

const OperationSerializer = {
  serializeBrushOperation(points, options) {
    return {
      type: HistoryActionTypes.DRAW,
      tool: ToolTypes.BRUSH,
      points: points,
      color: options.color,
      size: options.size
    };
  },

  serializeEraserOperation(points, options) {
    return {
      type: HistoryActionTypes.DRAW,
      tool: ToolTypes.ERASER,
      points: points,
      size: options.size
    };
  },

  serializeRectangleOperation(x1, y1, x2, y2, options) {
    return {
      type: HistoryActionTypes.DRAW,
      tool: ToolTypes.RECTANGLE,
      x1, y1, x2, y2,
      color: options.color,
      strokeWidth: options.strokeWidth,
      fill: options.fill
    };
  },

  serializeLineOperation(x1, y1, x2, y2, options) {
    return {
      type: HistoryActionTypes.DRAW,
      tool: ToolTypes.LINE,
      x1, y1, x2, y2,
      color: options.color,
      strokeWidth: options.strokeWidth
    };
  },

  serializeCircleOperation(x1, y1, x2, y2, options) {
    return {
      type: HistoryActionTypes.DRAW,
      tool: ToolTypes.CIRCLE,
      x1, y1, x2, y2,
      color: options.color,
      strokeWidth: options.strokeWidth,
      fill: options.fill
    };
  },

  serializeTextOperation(x, y, text, options) {
    return {
      type: HistoryActionTypes.DRAW,
      tool: ToolTypes.TEXT,
      x, y, text,
      color: options.color,
      fontSize: options.fontSize,
      fontFamily: options.fontFamily
    };
  },

  serializeClearOperation() {
    return {
      type: HistoryActionTypes.CLEAR,
      tool: null
    };
  },

  getOperationDescription(operation) {
    if (!operation) return '';
    
    const toolNames = {
      [ToolTypes.BRUSH]: '画笔',
      [ToolTypes.ERASER]: '橡皮擦',
      [ToolTypes.RECTANGLE]: '矩形',
      [ToolTypes.LINE]: '直线',
      [ToolTypes.CIRCLE]: '圆形',
      [ToolTypes.TEXT]: '文本'
    };

    if (operation.type === HistoryActionTypes.CLEAR) {
      return '清空画布';
    }

    const toolName = toolNames[operation.tool] || operation.tool;
    const time = new Date(operation.timestamp).toLocaleTimeString();

    if (operation.tool === ToolTypes.TEXT) {
      const preview = operation.text.length > 10 
        ? operation.text.substring(0, 10) + '...' 
        : operation.text;
      return `${toolName}: "${preview}" (${time})`;
    }

    if (operation.tool === ToolTypes.BRUSH || operation.tool === ToolTypes.ERASER) {
      const pointCount = operation.points ? operation.points.length : 0;
      return `${toolName}: ${pointCount} 个点 (${time})`;
    }

    return `${toolName} (${time})`;
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    HistoryActionTypes,
    HistoryManager,
    OperationSerializer
  };
}
