class DrawingTool {
  constructor(ctx) {
    this.ctx = ctx;
    this.isDrawing = false;
  }

  setContext(ctx) {
    this.ctx = ctx;
  }

  start(x, y, options) {}
  move(x, y, options) {}
  end(x, y, options) {}
  drawRemote(data) {}
}

class BrushTool extends DrawingTool {
  constructor(ctx) {
    super(ctx);
    this.lastX = 0;
    this.lastY = 0;
  }

  start(x, y, options) {
    this.isDrawing = true;
    this.lastX = x;
    this.lastY = y;
    
    this.ctx.beginPath();
    this.ctx.arc(x, y, options.size / 2, 0, Math.PI * 2);
    this.ctx.fillStyle = options.color;
    this.ctx.fill();
  }

  move(x, y, options) {
    if (!this.isDrawing) return;
    
    this.ctx.beginPath();
    this.ctx.moveTo(this.lastX, this.lastY);
    this.ctx.lineTo(x, y);
    this.ctx.strokeStyle = options.color;
    this.ctx.lineWidth = options.size;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';
    this.ctx.stroke();
    
    this.lastX = x;
    this.lastY = y;
  }

  end() {
    this.isDrawing = false;
  }

  drawRemote(data) {
    if (data.action === DrawingActions.START) {
      this.ctx.beginPath();
      this.ctx.arc(data.x, data.y, data.size / 2, 0, Math.PI * 2);
      this.ctx.fillStyle = data.color;
      this.ctx.fill();
    } else if (data.action === DrawingActions.MOVE) {
      if (this.lastX && this.lastY) {
        this.ctx.beginPath();
        this.ctx.moveTo(this.lastX, this.lastY);
        this.ctx.lineTo(data.x, data.y);
        this.ctx.strokeStyle = data.color;
        this.ctx.lineWidth = data.size;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
        this.ctx.stroke();
      }
      this.lastX = data.x;
      this.lastY = data.y;
    } else if (data.action === DrawingActions.END) {
      this.lastX = null;
      this.lastY = null;
    }
  }
}

class EraserTool extends DrawingTool {
  constructor(ctx) {
    super(ctx);
  }

  start(x, y, options) {
    this.isDrawing = true;
    this.ctx.clearRect(
      x - options.size / 2,
      y - options.size / 2,
      options.size,
      options.size
    );
  }

  move(x, y, options) {
    if (!this.isDrawing) return;
    this.ctx.clearRect(
      x - options.size / 2,
      y - options.size / 2,
      options.size,
      options.size
    );
  }

  end() {
    this.isDrawing = false;
  }

  drawRemote(data) {
    if (data.action === DrawingActions.START || data.action === DrawingActions.MOVE) {
      this.ctx.clearRect(
        data.x - data.size / 2,
        data.y - data.size / 2,
        data.size,
        data.size
      );
    }
  }
}

class RectangleTool extends DrawingTool {
  constructor(ctx) {
    super(ctx);
    this.startX = 0;
    this.startY = 0;
  }

  start(x, y, options) {
    this.isDrawing = true;
    this.startX = x;
    this.startY = y;
  }

  move(x, y, options) {
    if (!this.isDrawing) return { x1: this.startX, y1: this.startY, x2: x, y2: y };
    return null;
  }

  end(x, y, options) {
    this.isDrawing = false;
    return this.drawRectangle(this.startX, this.startY, x, y, options);
  }

  drawRectangle(x1, y1, x2, y2, options) {
    const width = x2 - x1;
    const height = y2 - y1;
    
    this.ctx.beginPath();
    this.ctx.rect(x1, y1, width, height);
    
    if (options.fill) {
      this.ctx.fillStyle = options.color;
      this.ctx.fill();
    }
    
    this.ctx.strokeStyle = options.color;
    this.ctx.lineWidth = options.strokeWidth || 2;
    this.ctx.stroke();
    
    return {
      x1, y1, x2, y2,
      color: options.color,
      strokeWidth: options.strokeWidth || 2,
      fill: options.fill || false
    };
  }

  drawRemote(data) {
    this.drawRectangle(
      data.x1, data.y1, data.x2, data.y2,
      { color: data.color, strokeWidth: data.strokeWidth, fill: data.fill }
    );
  }
}

class LineTool extends DrawingTool {
  constructor(ctx) {
    super(ctx);
    this.startX = 0;
    this.startY = 0;
  }

  start(x, y, options) {
    this.isDrawing = true;
    this.startX = x;
    this.startY = y;
  }

  move(x, y, options) {
    if (!this.isDrawing) return { x1: this.startX, y1: this.startY, x2: x, y2: y };
    return null;
  }

  end(x, y, options) {
    this.isDrawing = false;
    return this.drawLine(this.startX, this.startY, x, y, options);
  }

  drawLine(x1, y1, x2, y2, options) {
    this.ctx.beginPath();
    this.ctx.moveTo(x1, y1);
    this.ctx.lineTo(x2, y2);
    this.ctx.strokeStyle = options.color;
    this.ctx.lineWidth = options.strokeWidth || 2;
    this.ctx.lineCap = 'round';
    this.ctx.stroke();
    
    return {
      x1, y1, x2, y2,
      color: options.color,
      strokeWidth: options.strokeWidth || 2
    };
  }

  drawRemote(data) {
    this.drawLine(
      data.x1, data.y1, data.x2, data.y2,
      { color: data.color, strokeWidth: data.strokeWidth }
    );
  }
}

class CircleTool extends DrawingTool {
  constructor(ctx) {
    super(ctx);
    this.startX = 0;
    this.startY = 0;
  }

  start(x, y, options) {
    this.isDrawing = true;
    this.startX = x;
    this.startY = y;
  }

  move(x, y, options) {
    if (!this.isDrawing) return { x1: this.startX, y1: this.startY, x2: x, y2: y };
    return null;
  }

  end(x, y, options) {
    this.isDrawing = false;
    return this.drawCircle(this.startX, this.startY, x, y, options);
  }

  drawCircle(x1, y1, x2, y2, options) {
    const centerX = (x1 + x2) / 2;
    const centerY = (y1 + y2) / 2;
    const radiusX = Math.abs(x2 - x1) / 2;
    const radiusY = Math.abs(y2 - y1) / 2;
    
    this.ctx.beginPath();
    this.ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, Math.PI * 2);
    
    if (options.fill) {
      this.ctx.fillStyle = options.color;
      this.ctx.fill();
    }
    
    this.ctx.strokeStyle = options.color;
    this.ctx.lineWidth = options.strokeWidth || 2;
    this.ctx.stroke();
    
    return {
      x1, y1, x2, y2,
      color: options.color,
      strokeWidth: options.strokeWidth || 2,
      fill: options.fill || false
    };
  }

  drawRemote(data) {
    this.drawCircle(
      data.x1, data.y1, data.x2, data.y2,
      { color: data.color, strokeWidth: data.strokeWidth, fill: data.fill }
    );
  }
}

class TextTool extends DrawingTool {
  constructor(ctx) {
    super(ctx);
  }

  start(x, y, options) {
    return { x, y, waiting: true };
  }

  drawText(x, y, text, options) {
    this.ctx.font = `${options.fontSize || 16}px ${options.fontFamily || 'Arial'}`;
    this.ctx.fillStyle = options.color;
    this.ctx.textBaseline = 'top';
    this.ctx.fillText(text, x, y);
    
    return {
      x, y, text,
      color: options.color,
      fontSize: options.fontSize || 16,
      fontFamily: options.fontFamily || 'Arial'
    };
  }

  drawRemote(data) {
    this.ctx.font = `${data.fontSize || 16}px ${data.fontFamily || 'Arial'}`;
    this.ctx.fillStyle = data.color;
    this.ctx.textBaseline = 'top';
    this.ctx.fillText(data.text, data.x, data.y);
  }
}

const ToolManager = {
  tools: {},
  currentTool: null,
  currentToolName: null,

  init(ctx) {
    this.tools[ToolTypes.BRUSH] = new BrushTool(ctx);
    this.tools[ToolTypes.ERASER] = new EraserTool(ctx);
    this.tools[ToolTypes.RECTANGLE] = new RectangleTool(ctx);
    this.tools[ToolTypes.LINE] = new LineTool(ctx);
    this.tools[ToolTypes.CIRCLE] = new CircleTool(ctx);
    this.tools[ToolTypes.TEXT] = new TextTool(ctx);
    
    this.setTool(ToolTypes.BRUSH);
  },

  setTool(toolName) {
    if (this.tools[toolName]) {
      this.currentTool = this.tools[toolName];
      this.currentToolName = toolName;
    }
  },

  getCurrentTool() {
    return this.currentTool;
  },

  getTool(toolName) {
    return this.tools[toolName];
  },

  updateContext(ctx) {
    Object.values(this.tools).forEach(tool => tool.setContext(ctx));
  },

  drawRemote(drawing) {
    const tool = this.tools[drawing.tool];
    if (tool) {
      tool.drawRemote(drawing);
    }
  }
};
