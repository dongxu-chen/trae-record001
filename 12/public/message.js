const MessageTypes = {
  JOIN_ROOM: 'join_room',
  USER_JOINED: 'user_joined',
  USER_JOINED_BROADCAST: 'user_joined_broadcast',
  USER_LEFT: 'user_left',
  DRAW: 'draw',
  CURSOR_MOVE: 'cursor_move',
  CLEAR_CANVAS: 'clear_canvas',
  LEAVE_ROOM: 'leave_room',
  UNDO: 'undo',
  REDO: 'redo',
  HISTORY_SYNC: 'history_sync'
};

const ToolTypes = {
  BRUSH: 'brush',
  ERASER: 'eraser',
  RECTANGLE: 'rectangle',
  TEXT: 'text',
  LINE: 'line',
  CIRCLE: 'circle'
};

const DrawingActions = {
  START: 'start',
  MOVE: 'move',
  END: 'end'
};

const DefaultConfig = {
  brushSize: 3,
  eraserSize: 20,
  color: '#000000',
  fontSize: 16
};

const MessageBuilder = {
  joinRoom(roomId, username) {
    return { roomId, username };
  },

  draw(tool, action, options) {
    return {
      tool,
      action,
      ...options
    };
  },

  brushStart(x, y, color, size) {
    return this.draw(ToolTypes.BRUSH, DrawingActions.START, { x, y, color, size });
  },

  brushMove(x, y, color, size) {
    return this.draw(ToolTypes.BRUSH, DrawingActions.MOVE, { x, y, color, size });
  },

  brushEnd() {
    return this.draw(ToolTypes.BRUSH, DrawingActions.END, {});
  },

  eraserStart(x, y, size) {
    return this.draw(ToolTypes.ERASER, DrawingActions.START, { x, y, size });
  },

  eraserMove(x, y, size) {
    return this.draw(ToolTypes.ERASER, DrawingActions.MOVE, { x, y, size });
  },

  eraserEnd() {
    return this.draw(ToolTypes.ERASER, DrawingActions.END, {});
  },

  rectangle(x1, y1, x2, y2, color, strokeWidth, fill) {
    return this.draw(ToolTypes.RECTANGLE, DrawingActions.END, {
      x1, y1, x2, y2, color, strokeWidth, fill
    });
  },

  line(x1, y1, x2, y2, color, strokeWidth) {
    return this.draw(ToolTypes.LINE, DrawingActions.END, {
      x1, y1, x2, y2, color, strokeWidth
    });
  },

  circle(x1, y1, x2, y2, color, strokeWidth, fill) {
    return this.draw(ToolTypes.CIRCLE, DrawingActions.END, {
      x1, y1, x2, y2, color, strokeWidth, fill
    });
  },

  text(x, y, text, color, fontSize, fontFamily) {
    return this.draw(ToolTypes.TEXT, DrawingActions.END, {
      x, y, text, color, fontSize, fontFamily
    });
  },

  cursorMove(x, y, tool) {
    return { x, y, tool };
  },

  clearCanvas() {
    return {};
  },

  undo(operationId) {
    return { operationId };
  },

  redo(operationId) {
    return { operationId };
  },

  historySync(operations, version) {
    return { operations, version };
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MessageTypes,
    ToolTypes,
    DrawingActions,
    DefaultConfig,
    MessageBuilder
  };
}
