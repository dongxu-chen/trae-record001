import { io, Socket } from 'socket.io-client';
import type { AlertNotification } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8000/ws';
const MOCK_USER_ID = 'user-001';

class WebSocketService {
  private socket: Socket | null = null;
  private alertListeners: Set<(alert: AlertNotification) => void> = new Set();
  private priceUpdateListeners: Map<string, Set<(data: any) => void>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(): void {
    if (this.socket?.connected) return;

    this.socket = io(WS_URL, {
      transports: ['websocket', 'polling'],
      path: '/ws/socket.io',
      extraHeaders: {
        'X-User-Id': MOCK_USER_ID,
      },
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.warn('Max reconnection attempts reached');
      }
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
    });

    this.socket.on('connected', (data) => {
      console.log('Server confirmed connection:', data);
    });

    this.socket.on(`price_alert_${MOCK_USER_ID}`, (alert: AlertNotification) => {
      this.notifyAlertListeners(alert);
    });

    this.socket.on('price_drop', (alert: AlertNotification) => {
      this.notifyAlertListeners(alert);
    });

    this.socket.on('price_update', (data) => {
      this.notifyPriceUpdateListeners(data.product_id, data);
    });

    this.socket.on('subscribed', (data) => {
      console.log('Subscribed to product:', data.product_id);
    });

    this.socket.on('unsubscribed', (data) => {
      console.log('Unsubscribed from product:', data.product_id);
    });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  subscribeToProduct(productId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('subscribe_product', { product_id: productId });
    }
  }

  unsubscribeFromProduct(productId: string): void {
    if (this.socket?.connected) {
      this.socket.emit('unsubscribe_product', { product_id: productId });
    }
    this.priceUpdateListeners.delete(productId);
  }

  onPriceAlert(listener: (alert: AlertNotification) => void): () => void {
    this.alertListeners.add(listener);
    return () => this.alertListeners.delete(listener);
  }

  onPriceUpdate(productId: string, listener: (data: any) => void): () => void {
    if (!this.priceUpdateListeners.has(productId)) {
      this.priceUpdateListeners.set(productId, new Set());
    }
    this.priceUpdateListeners.get(productId)!.add(listener);
    this.subscribeToProduct(productId);

    return () => {
      const listeners = this.priceUpdateListeners.get(productId);
      if (listeners) {
        listeners.delete(listener);
        if (listeners.size === 0) {
          this.unsubscribeFromProduct(productId);
        }
      }
    };
  }

  private notifyAlertListeners(alert: AlertNotification): void {
    this.alertListeners.forEach((listener) => {
      try {
        listener(alert);
      } catch (error) {
        console.error('Error in alert listener:', error);
      }
    });
  }

  private notifyPriceUpdateListeners(productId: string, data: any): void {
    const listeners = this.priceUpdateListeners.get(productId);
    if (listeners) {
      listeners.forEach((listener) => {
        try {
          listener(data);
        } catch (error) {
          console.error('Error in price update listener:', error);
        }
      });
    }
  }
}

export const wsService = new WebSocketService();
