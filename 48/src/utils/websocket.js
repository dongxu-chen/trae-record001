class WebSocketService {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.baseReconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
    this.listeners = new Map();
    this.isConnected = false;
    this.reconnectTimeout = null;
    this.shouldReconnect = true;
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket 连接成功');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.shouldReconnect = true;
        this.emit('open');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit('message', data);
        } catch (error) {
          console.error('解析 WebSocket 消息失败:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket 连接关闭:', event.code, event.reason);
        this.isConnected = false;
        this.emit('close');
        if (this.shouldReconnect) {
          this.attemptReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
        this.emit('error', error);
      };
    } catch (error) {
      console.error('创建 WebSocket 连接失败:', error);
      if (this.shouldReconnect) {
        this.attemptReconnect();
      }
    }
  }

  calculateReconnectDelay() {
    const exponentialDelay = this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts);
    const jitter = Math.random() * 1000;
    return Math.min(exponentialDelay + jitter, this.maxReconnectDelay);
  }

  attemptReconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.calculateReconnectDelay();
      console.log(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})，延迟 ${delay}ms...`);
      
      this.reconnectTimeout = setTimeout(() => {
        this.reconnectTimeout = null;
        this.connect();
      }, delay);
    } else {
      console.log('达到最大重连次数，停止尝试');
      this.shouldReconnect = false;
    }
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event).filter(cb => cb !== callback);
      this.listeners.set(event, callbacks);
    }
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => callback(data));
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket 未连接，无法发送消息');
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
    this.listeners.clear();
  }
}

const wsService = new WebSocketService('ws://localhost:8080/ws');

export default wsService;
