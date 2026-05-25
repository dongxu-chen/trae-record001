import { WebSocketMessage, Device, Link } from '../types';

const WS_URL = 'ws://localhost:3001';
const HEARTBEAT_INTERVAL = 15000;
const PONG_TIMEOUT = 30000;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 3000;
  private messageHandlers: Set<(message: WebSocketMessage) => void> = new Set();
  private connectionHandlers: Set<(connected: boolean) => void> = new Set();
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private pongTimeout: ReturnType<typeof setTimeout> | null = null;
  private lastPongTime: number = 0;
  private isReconnecting: boolean = false;

  connect() {
    if (this.isReconnecting) return;
    
    try {
      this.ws = new WebSocket(WS_URL);
      this.isReconnecting = true;

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.isReconnecting = false;
        this.notifyConnection(true);
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          if (message.type === 'PING') {
            this.lastPongTime = Date.now();
            this.sendPong();
            return;
          }
          
          if (message.type === 'PONG') {
            this.lastPongTime = message.timestamp;
            this.clearPongTimeout();
            return;
          }
          
          this.notifyMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (event) => {
        console.error('WebSocket error event:', event);
        console.error('WebSocket readyState:', this.ws?.readyState);
        console.error('WebSocket url:', this.ws?.url);
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected. Code:', event.code, 'Reason:', event.reason);
        this.stopHeartbeat();
        this.clearPongTimeout();
        this.notifyConnection(false);
        this.isReconnecting = false;
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('Error connecting WebSocket:', error);
      this.isReconnecting = false;
      this.attemptReconnect();
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.lastPongTime = Date.now();
    
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.sendPing();
        this.setPongTimeout();
      }
    }, HEARTBEAT_INTERVAL);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private sendPing() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify({ type: 'PING', timestamp: Date.now() }));
      } catch (e) {
        console.error('Error sending PING:', e);
      }
    }
  }

  private sendPong() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify({ type: 'PONG', timestamp: Date.now() }));
      } catch (e) {
        console.error('Error sending PONG:', e);
      }
    }
  }

  private setPongTimeout() {
    this.clearPongTimeout();
    
    this.pongTimeout = setTimeout(() => {
      const timeSinceLastPong = Date.now() - this.lastPongTime;
      if (timeSinceLastPong > PONG_TIMEOUT) {
        console.log(`PONG timeout (${timeSinceLastPong}ms), closing connection`);
        this.ws?.close(1008, 'PONG timeout');
      }
    }, PONG_TIMEOUT);
  }

  private clearPongTimeout() {
    if (this.pongTimeout) {
      clearTimeout(this.pongTimeout);
      this.pongTimeout = null;
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 30000);
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms...`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.error('Max reconnect attempts reached');
      this.isReconnecting = false;
    }
  }

  requestSync() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('Requesting full state sync from server');
      try {
        this.ws.send(JSON.stringify({ type: 'SYNC_REQUEST' }));
      } catch (e) {
        console.error('Error sending sync request:', e);
      }
    }
  }

  disconnect() {
    this.stopHeartbeat();
    this.clearPongTimeout();
    this.isReconnecting = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(type: string, data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    }
  }

  addDevice(device: Omit<Device, 'id'>) {
    this.send('ADD_DEVICE', device);
  }

  removeDevice(deviceId: string) {
    this.send('REMOVE_DEVICE', { deviceId });
  }

  addLink(link: Omit<Link, 'id'>) {
    this.send('ADD_LINK', link);
  }

  removeLink(linkId: string) {
    this.send('REMOVE_LINK', { linkId });
  }

  onMessage(handler: (message: WebSocketMessage) => void) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onConnectionChange(handler: (connected: boolean) => void) {
    this.connectionHandlers.add(handler);
    return () => this.connectionHandlers.delete(handler);
  }

  private notifyMessage(message: WebSocketMessage) {
    this.messageHandlers.forEach((handler) => handler(message));
  }

  private notifyConnection(connected: boolean) {
    this.connectionHandlers.forEach((handler) => handler(connected));
  }

  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsClient = new WebSocketClient();
