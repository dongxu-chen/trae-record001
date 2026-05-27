import { useEffect, useRef, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';

interface TemplateStats {
  viewCount?: number;
  downloadCount?: number;
  rating?: number;
  ratingCount?: number;
}

interface UseWebSocketOptions {
  templateId?: string;
  onTemplateStatsUpdate?: (stats: TemplateStats) => void;
  onGlobalStatsUpdate?: (stats: any) => void;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const socketRef = useRef<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [templateStats, setTemplateStats] = useState<TemplateStats | null>(null);

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return;

    const socket = io('http://localhost:5000', {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    });

    socket.on('connect', () => {
      console.log('WebSocket 连接成功');
      setIsConnected(true);
      
      if (options.templateId) {
        socket.emit('joinTemplate', options.templateId);
      }
    });

    socket.on('disconnect', () => {
      console.log('WebSocket 断开连接');
      setIsConnected(false);
    });

    socket.on('templateStatsUpdate', (stats: TemplateStats) => {
      console.log('收到模板统计更新:', stats);
      setTemplateStats(stats);
      options.onTemplateStatsUpdate?.(stats);
    });

    socket.on('globalStatsUpdate', (stats: any) => {
      console.log('收到全局统计更新:', stats);
      options.onGlobalStatsUpdate?.(stats);
    });

    socketRef.current = socket;
  }, [options.templateId, options.onTemplateStatsUpdate, options.onGlobalStatsUpdate]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      if (options.templateId) {
        socketRef.current.emit('leaveTemplate', options.templateId);
      }
      socketRef.current.disconnect();
      socketRef.current = null;
      setIsConnected(false);
    }
  }, [options.templateId]);

  const joinTemplate = useCallback((templateId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('joinTemplate', templateId);
    }
  }, []);

  const leaveTemplate = useCallback((templateId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('leaveTemplate', templateId);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  useEffect(() => {
    if (options.templateId && socketRef.current?.connected) {
      socketRef.current.emit('joinTemplate', options.templateId);
    }
  }, [options.templateId]);

  return {
    isConnected,
    templateStats,
    connect,
    disconnect,
    joinTemplate,
    leaveTemplate,
  };
};

export default useWebSocket;
