import { useState, useEffect, useCallback } from 'react';
import { Client } from '@stomp/stompjs';
import SockJS from 'sockjs-client';

const WS_URL = 'http://localhost:8080/api/ws';

let stompClient = null;

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [waterLevelData, setWaterLevelData] = useState(null);
  const [coordinationEvents, setCoordinationEvents] = useState([]);
  const [alerts, setAlerts] = useState([]);

  const connect = useCallback(() => {
    if (stompClient?.active) return;

    stompClient = new Client({
      webSocketFactory: () => new SockJS(WS_URL),
      reconnectDelay: 5000,
      heartbeatIncoming: 4000,
      heartbeatOutgoing: 4000,
      onConnect: () => {
        setConnected(true);
        console.log('WebSocket connected');

        stompClient.subscribe('/topic/water-levels', (message) => {
          try {
            const data = JSON.parse(message.body);
            setWaterLevelData(data);
          } catch (e) {
            console.error('Failed to parse water level message:', e);
          }
        });

        stompClient.subscribe('/topic/coordination-events', (message) => {
          try {
            const data = JSON.parse(message.body);
            setCoordinationEvents(prev => [data, ...prev].slice(0, 10));
          } catch (e) {
            console.error('Failed to parse coordination message:', e);
          }
        });

        stompClient.subscribe('/topic/alerts', (message) => {
          try {
            const data = JSON.parse(message.body);
            setAlerts(prev => [data, ...prev].slice(0, 20));
          } catch (e) {
            console.error('Failed to parse alert message:', e);
          }
        });
      },
      onDisconnect: () => {
        setConnected(false);
        console.log('WebSocket disconnected');
      },
      onStompError: (frame) => {
        console.error('Broker error: ' + frame.headers['message']);
      },
    });

    stompClient.activate();
  }, []);

  const disconnect = useCallback(() => {
    if (stompClient) {
      stompClient.deactivate();
      stompClient = null;
      setConnected(false);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    connected,
    waterLevelData,
    coordinationEvents,
    alerts,
    connect,
    disconnect,
  };
}

export default useWebSocket;
