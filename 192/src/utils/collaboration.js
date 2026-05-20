import ReconnectingWebSocket from 'reconnecting-websocket';

class CollaborationClient {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
    this.clientId = null;
    this.isConnected = false;
  }

  connect(url = 'ws://localhost:8080') {
    this.ws = new ReconnectingWebSocket(url);
    
    this.ws.onopen = () => {
      this.isConnected = true;
      this.emit('connected');
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.emit(data.type, data);
      } catch (e) {
        console.error('Error parsing message:', e);
      }
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      this.emit('disconnected');
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnect() {
    if (this.ws && this.ws.close) {
      this.ws.close();
    }
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback);
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => callback(data));
    }
  }

  submitOp(op) {
    this.send({ type: 'op', op });
  }

  submitPresence(range) {
    this.send({ type: 'presence', range });
  }

  submitComment(comment) {
    this.send({ type: 'comment', comment });
  }

  resolveComment(commentId) {
    this.send({ type: 'resolveComment', commentId });
  }

  getOplog(fromVersion, toVersion) {
    this.send({ type: 'getOplog', fromVersion, toVersion });
  }

  getSnapshot(version) {
    this.send({ type: 'getSnapshot', version });
  }

  revertToVersion(version) {
    this.send({ type: 'revertToVersion', version });
  }

  createCheckpoint() {
    this.send({ type: 'createCheckpoint' });
  }
}

export const collaborationClient = new CollaborationClient();
export default collaborationClient;
