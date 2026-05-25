interface WebSocketMessage {
  type: string;
  action?: string;
  data?: any;
  timestamp?: number;
  message?: string;
}

interface WebSocketHandlers {
  onDynamicCodeCreated?: (data: any) => void;
  onDynamicCodeUpdated?: (data: any) => void;
  onDynamicCodeDeleted?: (data: any) => void;
  onScanUpdated?: (data: any) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: string) => void;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private userId: string | null = null;
  private handlers: WebSocketHandlers = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private shouldReconnect = true;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  connect(userId: string, handlers?: WebSocketHandlers) {
    this.userId = userId;
    if (handlers) {
      this.handlers = handlers;
    }

    this.shouldReconnect = true;
    this.createConnection();
  }

  private createConnection() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:3001/ws?userId=${this.userId}`;

    try {
      this.ws = new WebSocket(wsUrl);
      this.setupEventListeners();
    } catch (error) {
      console.error('WebSocket连接创建失败:', error);
      this.handlers.onError?.(error instanceof Error ? error.message : '连接失败');
      this.scheduleReconnect();
    }
  }

  private setupEventListeners() {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('WebSocket连接已建立');
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      this.startHeartbeat();
      this.handlers.onConnected?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('WebSocket消息解析错误:', error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket连接已关闭');
      this.stopHeartbeat();
      this.handlers.onDisconnected?.();
      this.scheduleReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
      this.handlers.onError?.('连接错误');
    };
  }

  private handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'connected':
        console.log(message.message);
        break;
      case 'dynamic_code_created':
        this.handlers.onDynamicCodeCreated?.(message.data);
        break;
      case 'dynamic_code_updated':
        this.handlers.onDynamicCodeUpdated?.(message.data);
        break;
      case 'dynamic_code_deleted':
        this.handlers.onDynamicCodeDeleted?.(message.data);
        break;
      case 'scan_updated':
        this.handlers.onScanUpdated?.(message.data);
        break;
      case 'pong':
        break;
      default:
        console.log('未知消息类型:', message.type);
    }
  }

  private scheduleReconnect() {
    if (!this.shouldReconnect || this.reconnectAttempts >= this.maxReconnectAttempts) {
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.log('达到最大重连次数，停止重连');
        this.handlers.onError?.('连接失败，请刷新页面重试');
      }
      return;
    }

    this.reconnectAttempts++;
    console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

    setTimeout(() => {
      this.createConnection();
    }, this.reconnectDelay);

    this.reconnectDelay = Math.min(this.reconnectDelay * 2, 10000);
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  setHandlers(handlers: WebSocketHandlers) {
    this.handlers = { ...this.handlers, ...handlers };
  }
}

export const wsClient = new WebSocketClient();
export default wsClient;
