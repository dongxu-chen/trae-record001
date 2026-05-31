import { useState, useEffect, useRef } from 'react';
import { LiveData } from '../types';

const WS_URL = 'ws://localhost:8765';

export function useWebSocket() {
  const [data, setData] = useState<LiveData | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('WebSocket连接成功');
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data);
          setData(parsedData);
        } catch (error) {
          console.error('解析数据失败:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
        setConnected(false);
      };

      ws.onclose = () => {
        console.log('WebSocket连接关闭，5秒后重试...');
        setConnected(false);
        setTimeout(connect, 5000);
      };

      wsRef.current = ws;
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { data, connected };
}
