import { useEffect, useRef, useState, useCallback } from 'react';

export function useWebSocket(user, currentRoom) {
  const wsRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [typingUsers, setTypingUsers] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const reconnectTimeoutRef = useRef(null);
  const currentRoomRef = useRef(null);

  const showNotification = useCallback((title, content) => {
    if (Notification.permission === 'granted') {
      new Notification(title, { body: content });
    }
    setNotifications(prev => [...prev, { id: Date.now(), title, content }]);
    setTimeout(() => {
      setNotifications(prev => prev.slice(1));
    }, 5000);
  }, []);

  const connect = useCallback((roomId) => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    currentRoomRef.current = roomId;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:3001`;
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      setIsConnected(true);
      if (user && roomId) {
        wsRef.current.send(JSON.stringify({
          type: 'join',
          payload: { user, roomId }
        }));
      }
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'joined':
          setMessages(data.payload.messages || []);
          setOnlineUsers(data.payload.room?.users || []);
          break;
        case 'message':
          setMessages(prev => {
            const existingIndex = prev.findIndex(m => m.id === data.payload.id);
            if (existingIndex >= 0) {
              const updated = [...prev];
              updated[existingIndex] = data.payload;
              return updated;
            }
            return [...prev, data.payload];
          });
          if (user && data.payload.mentions?.includes(user.username)) {
            showNotification('有人@你', `${data.payload.username}: ${data.payload.content}`);
          }
          break;
        case 'read_status':
          setMessages(prev => prev.map(msg => {
            if (msg.id === data.payload.messageId) {
              return { ...msg, readCount: data.payload.readCount, readBy: data.payload.readBy };
            }
            return msg;
          }));
          break;
        case 'user_joined':
          setOnlineUsers(data.payload.room?.users || []);
          break;
        case 'user_left':
          setOnlineUsers(prev => prev.filter(u => u.id !== data.payload.user.id));
          break;
        case 'typing':
          setTypingUsers(data.payload.users);
          break;
      }
    };

    wsRef.current.onclose = () => {
      setIsConnected(false);
      reconnectTimeoutRef.current = setTimeout(() => {
        if (currentRoomRef.current) {
          connect(currentRoomRef.current);
        }
      }, 3000);
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, [user, showNotification]);

  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  const prependMessages = useCallback((olderMessages) => {
    setMessages(prev => {
      const existingIds = new Set(prev.map(m => m.id));
      const newMessages = olderMessages.filter(m => !existingIds.has(m.id));
      return [...newMessages, ...prev];
    });
  }, []);

  const sendMessage = useCallback((roomId, content, mentions = []) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'message',
        payload: { roomId, content, mentions }
      }));
    }
  }, []);

  const sendTyping = useCallback((roomId, isTyping) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'typing',
        payload: { roomId, isTyping }
      }));
    }
  }, []);

  const markRead = useCallback((roomId, userId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'mark_read',
        payload: { roomId, userId }
      }));
    }
  }, []);

  const sendVoice = useCallback((roomId, url, duration) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'voice',
        payload: { 
          roomId, 
          content: '[语音消息]', 
          url, 
          duration,
          type: 'voice',
          mentions: []
        }
      }));
    }
  }, []);

  const sendReadReceipt = useCallback((roomId, messageId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'read_receipt',
        payload: { roomId, messageId }
      }));
    }
  }, []);

  const uploadVoice = useCallback(async (blob, duration) => {
    const formData = new FormData();
    formData.append('voice', blob, 'voice.webm');
    formData.append('duration', duration);
    
    try {
      const res = await fetch('/api/upload/voice', {
        method: 'POST',
        body: formData
      });
      return await res.json();
    } catch (error) {
      console.error('Upload voice failed:', error);
      throw error;
    }
  }, []);

  return {
    connect,
    sendMessage,
    sendVoice,
    sendTyping,
    markRead,
    sendReadReceipt,
    uploadVoice,
    messages,
    onlineUsers,
    typingUsers,
    isConnected,
    notifications,
    prependMessages
  };
}