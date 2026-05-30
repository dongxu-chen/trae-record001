import { useEffect, useRef, useCallback, useState } from 'react';
import { useLEDStore } from '../store/ledStore';

const WS_URL = 'ws://localhost:3001';
const RECONNECT_DELAY = 3000;
const HEARTBEAT_INTERVAL = 30000;

export interface WSSubtitlePayload {
  lines: { text: string; color: string }[];
  font?: Record<string, unknown>;
  scroll?: Record<string, unknown>;
  background?: Record<string, unknown>;
}

export interface WSSyncPayload {
  scrollOffset: number;
  isPlaying: boolean;
  timestamp: number;
}

export type WSConnectionStatus = 'disconnected' | 'connecting' | 'connected';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clientIdRef = useRef<string>('');
  
  const [status, setStatus] = useState<WSConnectionStatus>('disconnected');
  const [peerCount, setPeerCount] = useState(0);

  const { applyPreset, setScroll, togglePlaying, lines, font, scroll, background } = useLEDStore();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');

    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        setStatus('connected');
        console.log('[WS] Connected to server');

        heartbeatRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'heartbeat' }));
          }
        }, HEARTBEAT_INTERVAL);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          switch (message.type) {
            case 'client_join':
              if (message.clientId) {
                clientIdRef.current = message.clientId;
              }
              if (message.payload?.totalClients !== undefined) {
                setPeerCount(message.payload.totalClients - 1);
              }
              break;

            case 'client_leave':
              if (message.payload?.totalClients !== undefined) {
                setPeerCount(Math.max(0, message.payload.totalClients - 1));
              }
              break;

            case 'subtitle_update':
              if (message.payload) {
                const payload = message.payload as WSSubtitlePayload;
                applyPreset({
                  name: '远程推送',
                  lines: payload.lines,
                  font: payload.font,
                  scroll: payload.scroll,
                  background: payload.background
                });
              }
              break;

            case 'scroll_sync':
              if (message.payload) {
                const sync = message.payload as WSSyncPayload;
                if (sync.isPlaying !== undefined) {
                  const currentPlaying = useLEDStore.getState().isPlaying;
                  if (currentPlaying !== sync.isPlaying) {
                    togglePlaying();
                  }
                }
                if (sync.scrollOffset !== undefined) {
                  setScroll({ direction: sync.scrollOffset as any });
                }
              }
              break;
          }
        } catch (e) {
          console.error('[WS] Parse error:', e);
        }
      };

      ws.onclose = () => {
        setStatus('disconnected');
        console.log('[WS] Disconnected');
        
        if (heartbeatRef.current) {
          clearInterval(heartbeatRef.current);
        }

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, RECONNECT_DELAY);
      };

      ws.onerror = () => {
        console.error('[WS] Connection error');
      };

      wsRef.current = ws;
    } catch (e) {
      setStatus('disconnected');
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, RECONNECT_DELAY);
    }
  }, [applyPreset, setScroll, togglePlaying]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
    setPeerCount(0);
  }, []);

  const pushSubtitle = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;

    const payload: WSSubtitlePayload = {
      lines: lines.map((l) => ({ text: l.text, color: l.color })),
      font,
      scroll,
      background
    };

    wsRef.current.send(JSON.stringify({
      type: 'push_subtitle',
      payload
    }));
  }, [lines, font, scroll, background]);

  const syncScroll = useCallback((scrollOffset: number, playing: boolean) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;

    const payload: WSSyncPayload = {
      scrollOffset,
      isPlaying: playing,
      timestamp: Date.now()
    };

    wsRef.current.send(JSON.stringify({
      type: 'sync_state',
      payload
    }));
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    status,
    peerCount,
    clientId: clientIdRef.current,
    connect,
    disconnect,
    pushSubtitle,
    syncScroll
  };
}
