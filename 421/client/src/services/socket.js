import { io } from 'socket.io-client';

class SocketService {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
  }

  connect() {
    if (this.socket?.connected) return;
    
    this.socket = io('http://localhost:5000', {
      transports: ['websocket', 'polling'],
    });

    this.socket.on('connect', () => {
      console.log('Connected to server');
    });

    this.socket.on('disconnect', () => {
      console.log('Disconnected from server');
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  joinDocument(docId, userId, username) {
    this.connect();
    this.socket.emit('join-document', { docId, userId, username });
  }

  leaveDocument(docId) {
    if (this.socket) {
      this.socket.leave(docId);
    }
  }

  sendOperation(docId, op, userId) {
    this.socket.emit('operation', { docId, op, userId });
  }

  saveRevision(data) {
    this.socket.emit('save-revision', data);
  }

  sendCursorPosition(docId, userId, username, position) {
    this.socket.emit('cursor-position', { docId, userId, username, position });
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    this.socket?.on(event, callback);
  }

  off(event, callback) {
    this.socket?.off(event, callback);
    this.listeners.get(event)?.delete(callback);
  }
}

export default new SocketService();
