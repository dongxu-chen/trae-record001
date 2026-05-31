import SockJS from 'sockjs-client';
import Stomp from 'stompjs';

class WebSocketService {
  constructor() {
    this.stompClient = null;
    this.connected = false;
    this.subscriptions = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 3000;
  }

  connect() {
    return new Promise((resolve, reject) => {
      if (this.connected) {
        resolve();
        return;
      }

      try {
        const socket = new SockJS('/ws');
        this.stompClient = Stomp.over(socket);
        this.stompClient.debug = () => {};

        this.stompClient.connect(
          {},
          () => {
            this.connected = true;
            this.reconnectAttempts = 0;
            console.log('WebSocket connected');
            this.reconnectSubscriptions();
            resolve();
          },
          (error) => {
            console.error('WebSocket connection error:', error);
            this.connected = false;
            this.handleReconnect();
            reject(error);
          }
        );
      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        reject(error);
      }
    });
  }

  disconnect() {
    if (this.stompClient) {
      this.stompClient.disconnect();
      this.stompClient = null;
      this.connected = false;
      this.subscriptions.clear();
      console.log('WebSocket disconnected');
    }
  }

  subscribe(destination, callback) {
    if (!this.connected) {
      this.connect().then(() => {
        this.doSubscribe(destination, callback);
      });
    } else {
      this.doSubscribe(destination, callback);
    }
  }

  doSubscribe(destination, callback) {
    if (this.subscriptions.has(destination)) {
      return;
    }

    const subscription = this.stompClient.subscribe(destination, (message) => {
      try {
        const data = JSON.parse(message.body);
        callback(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    });

    this.subscriptions.set(destination, subscription);
    console.log(`Subscribed to: ${destination}`);
  }

  unsubscribe(destination) {
    const subscription = this.subscriptions.get(destination);
    if (subscription) {
      subscription.unsubscribe();
      this.subscriptions.delete(destination);
      console.log(`Unsubscribed from: ${destination}`);
    }
  }

  reconnectSubscriptions() {
    this.subscriptions.forEach((callback, destination) => {
      if (typeof callback === 'function') {
        this.doSubscribe(destination, callback);
      }
    });
  }

  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      setTimeout(() => {
        this.connect().catch(() => {
          this.handleReconnect();
        });
      }, this.reconnectInterval);
    } else {
      console.error('Max reconnect attempts reached');
    }
  }

  isConnected() {
    return this.connected;
  }
}

export const wsService = new WebSocketService();
export default wsService;
