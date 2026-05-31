import { useRef, useCallback, useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import type { RecognitionResult, TemporalResult, StatusUpdate } from '@/types';

type ServerMessage = RecognitionResult | TemporalResult | StatusUpdate;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const heartbeatIntervalRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const urlRef = useRef<string>('');
  const maxReconnectAttempts = 5;
  const heartbeatInterval = 30000;

  const setConnection = useAppStore((state) => state.setConnection);
  const setTopActions = useAppStore((state) => state.setTopActions);
  const setCurrentFps = useAppStore((state) => state.setCurrentFps);
  const setLatency = useAppStore((state) => state.setLatency);
  const setCurrentTimestamp = useAppStore((state) => state.setCurrentTimestamp);
  const addTemporalAction = useAppStore((state) => state.addTemporalAction);
  const setRecognitionStatus = useAppStore((state) => state.setRecognitionStatus);
  const setConnectionStatus = useAppStore((state) => state.setConnectionStatus);

  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback((url: string) => {
    urlRef.current = url;
    reconnectAttemptsRef.current = 0;

    const attemptConnect = () => {
      try {
        wsRef.current = new WebSocket(url);

        wsRef.current.onopen = () => {
          reconnectAttemptsRef.current = 0;
          setConnection({
            isConnected: true,
            isReconnecting: false,
            reconnectAttempts: 0,
            lastError: null,
          });
          setConnectionStatus('connecting');

          heartbeatIntervalRef.current = window.setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ type: 'ping' }));
            }
          }, heartbeatInterval);
        };

        wsRef.current.onmessage = (event) => {
          try {
            const message: ServerMessage = JSON.parse(event.data);

            if (message.type === 'pong') {
              return;
            }

            if (message.type === 'result') {
              const result = message as RecognitionResult;
              setTopActions(result.predictions);
              setCurrentFps(result.fps);
              setLatency(result.latency);
              setCurrentTimestamp(result.timestamp);
            }

            if (message.type === 'temporal') {
              const result = message as TemporalResult;
              addTemporalAction(result);
            }

            if (message.type === 'status') {
              const status = message as StatusUpdate;
              setRecognitionStatus(status.status);
              if (status.status === 'running' || status.status === 'paused') {
                setConnectionStatus(status.status);
              }
            }
          } catch {
            // ignore parse errors
          }
        };

        wsRef.current.onerror = () => {
          setConnection({ lastError: 'WebSocket connection error' });
          setConnectionStatus('error');
        };

        wsRef.current.onclose = () => {
          clearTimers();
          setConnection({ isConnected: false });
          setConnectionStatus('idle');

          if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            const delay = Math.pow(2, reconnectAttemptsRef.current) * 1000;
            reconnectAttemptsRef.current++;
            setConnection({
              isReconnecting: true,
              reconnectAttempts: reconnectAttemptsRef.current,
            });
            reconnectTimeoutRef.current = window.setTimeout(attemptConnect, delay);
          } else {
            setConnection({
              isReconnecting: false,
              lastError: 'Max reconnect attempts reached',
            });
          }
        };
      } catch {
        setConnection({ lastError: 'Failed to create WebSocket connection' });
        setConnectionStatus('error');
      }
    };

    attemptConnect();
  }, [clearTimers, setConnection, setTopActions, setCurrentFps, setLatency, setCurrentTimestamp, addTemporalAction, setRecognitionStatus, setConnectionStatus]);

  const disconnect = useCallback(() => {
    clearTimers();
    reconnectAttemptsRef.current = maxReconnectAttempts;

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, [clearTimers]);

  const reconnect = useCallback(() => {
    if (urlRef.current) {
      disconnect();
      reconnectAttemptsRef.current = 0;
      connect(urlRef.current);
    }
  }, [connect, disconnect]);

  const sendMessage = useCallback((message: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    connect,
    disconnect,
    reconnect,
    sendMessage,
  };
}
