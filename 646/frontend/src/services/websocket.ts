import SockJS from 'sockjs-client';
import Stomp from 'stompjs';

class WebSocketService {
  private client: Stomp.Client | null = null;
  private subscriptions: Map<string, Stomp.Subscription> = new Map();

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const socket = new SockJS('http://localhost:8080/api/ws');
      this.client = Stomp.over(socket);
      this.client.debug = () => {};

      this.client.connect(
        {},
        () => resolve(),
        (error: any) => reject(error)
      );
    });
  }

  subscribe(topic: string, callback: (message: any) => void): void {
    if (!this.client?.connected) return;

    const subscription = this.client.subscribe(topic, (message) => {
      try {
        const body = JSON.parse(message.body);
        callback(body);
      } catch (e) {
        callback(message.body);
      }
    });

    this.subscriptions.set(topic, subscription);
  }

  unsubscribe(topic: string): void {
    const subscription = this.subscriptions.get(topic);
    if (subscription) {
      subscription.unsubscribe();
      this.subscriptions.delete(topic);
    }
  }

  disconnect(): void {
    this.subscriptions.forEach((sub) => sub.unsubscribe());
    this.subscriptions.clear();
    this.client?.disconnect(() => {});
    this.client = null;
  }

  isConnected(): boolean {
    return this.client?.connected ?? false;
  }
}

export const wsService = new WebSocketService();
