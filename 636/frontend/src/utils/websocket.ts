import SockJS from 'sockjs-client';
import { Client, IMessage } from '@stomp/stompjs';
import { RealtimeMetrics, TestReport } from '../types';

export interface WebSocketHandlers {
  onMetrics?: (metrics: RealtimeMetrics) => void;
  onComplete?: (report: TestReport) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export class TestWebSocketClient {
  private client: Client | null = null;
  private testId: string | null = null;
  private handlers: WebSocketHandlers;

  constructor(handlers: WebSocketHandlers = {}) {
    this.handlers = handlers;
  }

  connect(testId: string): void {
    this.testId = testId;

    const socket = new SockJS('/ws');
    this.client = new Client({
      webSocketFactory: () => socket,
      connectHeaders: {},
      debug: () => {},
      reconnectDelay: 5000,
      heartbeatIncoming: 4000,
      heartbeatOutgoing: 4000,
    });

    this.client.onConnect = () => {
      this.handlers.onConnect?.();

      if (this.client && this.testId) {
        this.client.subscribe(`/topic/test/${this.testId}/metrics`, (message: IMessage) => {
          const metrics = JSON.parse(message.body) as RealtimeMetrics;
          this.handlers.onMetrics?.(metrics);
        });

        this.client.subscribe(`/topic/test/${this.testId}/complete`, (message: IMessage) => {
          const report = JSON.parse(message.body) as TestReport;
          this.handlers.onComplete?.(report);
        });
      }
    };

    this.client.onDisconnect = () => {
      this.handlers.onDisconnect?.();
    };

    this.client.activate();
  }

  disconnect(): void {
    if (this.client) {
      this.client.deactivate();
      this.client = null;
    }
  }
}
