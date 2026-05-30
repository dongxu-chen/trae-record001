import { useEffect, useRef, useCallback } from 'react';
import { useAlertStore } from '@/stores/alert-store';
import type { WebSocketMessage, MetricData, AlertRecord } from '@/types';

interface UseWebSocketReturn {
  connected: boolean;
  reconnect: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }
    if (wsRef.current) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      useAlertStore.getState().setWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const msg: WebSocketMessage = JSON.parse(event.data);
        const store = useAlertStore.getState();
        switch (msg.type) {
          case 'data': {
            const payload = msg.payload;
            if (Array.isArray(payload)) {
              for (const item of payload) {
                store.addMetricData(item as MetricData);
              }
            } else {
              store.addMetricData(payload as MetricData);
            }
            break;
          }
          case 'alert':
            store.addRealtimeAlert(msg.payload as AlertRecord);
            break;
          case 'config_update':
            store.fetchRules();
            break;
        }
      } catch {
      }
    };

    ws.onclose = () => {
      useAlertStore.getState().setWsConnected(false);
      if (mountedRef.current) {
        reconnectTimerRef.current = setTimeout(() => {
          if (mountedRef.current) connect();
        }, 3000);
      }
    };

    ws.onerror = () => {
      useAlertStore.getState().setWsConnected(false);
    };
  }, []);

  const reconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    connect();
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const connected = useAlertStore(s => s.wsConnected);

  return { connected, reconnect };
}
