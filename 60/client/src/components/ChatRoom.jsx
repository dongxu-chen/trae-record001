import React, { useState, useEffect, useRef, useCallback } from 'react';
import WebRTCChat from '../webrtc.js';
import { generateAnonymousId } from '../crypto.js';

const SIGNALING_SERVER = 'http://localhost:3001';

const styles = {
  container: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '20px',
    fontFamily: 'system-ui, -apple-system, sans-serif'
  },
  header: {
    textAlign: 'center',
    marginBottom: '20px',
    color: '#1a1a1a'
  },
  joinForm: {
    display: 'flex',
    gap: '10px',
    marginBottom: '20px'
  },
  input: {
    flex: 1,
    padding: '10px 15px',
    border: '2px solid #e0e0e0',
    borderRadius: '8px',
    fontSize: '16px',
    outline: 'none',
    transition: 'border-color 0.2s'
  },
  button: {
    padding: '10px 20px',
    border: 'none',
    borderRadius: '8px',
    backgroundColor: '#4f46e5',
    color: 'white',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  },
  buttonSecondary: {
    padding: '10px 20px',
    border: 'none',
    borderRadius: '8px',
    backgroundColor: '#6b7280',
    color: 'white',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  },
  buttonSmall: {
    padding: '6px 12px',
    border: 'none',
    borderRadius: '6px',
    backgroundColor: '#8b5cf6',
    color: 'white',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  },
  status: {
    padding: '10px',
    borderRadius: '8px',
    marginBottom: '20px',
    fontSize: '14px'
  },
  statusConnected: {
    backgroundColor: '#dcfce7',
    color: '#166534'
  },
  statusDisconnected: {
    backgroundColor: '#fee2e2',
    color: '#991b1b'
  },
  chatContainer: {
    border: '2px solid #e0e0e0',
    borderRadius: '12px',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    height: '550px'
  },
  headerBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 15px',
    backgroundColor: '#f3f4f6',
    borderBottom: '1px solid #e0e0e0'
  },
  peerList: {
    fontSize: '13px',
    color: '#6b7280'
  },
  typingIndicator: {
    padding: '8px 15px',
    backgroundColor: '#fef3c7',
    borderBottom: '1px solid #fbbf24',
    fontSize: '13px',
    color: '#92400e'
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
    backgroundColor: '#f9fafb'
  },
  message: {
    marginBottom: '15px',
    padding: '12px 16px',
    borderRadius: '12px',
    maxWidth: '70%',
    wordWrap: 'break-word'
  },
  messageMine: {
    backgroundColor: '#4f46e5',
    color: 'white',
    marginLeft: 'auto'
  },
  messageOther: {
    backgroundColor: 'white',
    color: '#1a1a1a',
    border: '1px solid #e0e0e0',
    marginRight: 'auto'
  },
  messageOffline: {
    backgroundColor: '#fef3c7',
    color: '#92400e',
    border: '1px solid #fbbf24',
    marginRight: 'auto',
    fontStyle: 'italic'
  },
  messageHistory: {
    backgroundColor: '#f3f4f6',
    color: '#6b7280',
    border: '1px dashed #d1d5db',
    marginRight: 'auto'
  },
  messageHeader: {
    fontSize: '12px',
    marginBottom: '5px',
    opacity: 0.8
  },
  messageText: {
    fontSize: '14px',
    lineHeight: '1.5'
  },
  messageTime: {
    fontSize: '11px',
    marginTop: '5px',
    opacity: 0.6,
    textAlign: 'right'
  },
  messageTag: {
    display: 'inline-block',
    fontSize: '10px',
    padding: '2px 6px',
    borderRadius: '4px',
    marginRight: '6px',
    verticalAlign: 'middle'
  },
  tagOffline: {
    backgroundColor: '#f59e0b',
    color: 'white'
  },
  tagHistory: {
    backgroundColor: '#9ca3af',
    color: 'white'
  },
  inputForm: {
    display: 'flex',
    padding: '15px',
    borderTop: '2px solid #e0e0e0',
    backgroundColor: 'white',
    gap: '10px'
  },
  info: {
    textAlign: 'center',
    padding: '20px',
    color: '#6b7280',
    fontSize: '14px'
  },
  loading: {
    display: 'inline-block',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: '#f59e0b',
    marginRight: '8px',
    animation: 'pulse 1.5s ease-in-out infinite'
  },
  typingDots: {
    display: 'inline-flex',
    gap: '3px',
    marginLeft: '5px'
  },
  dot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#92400e',
    animation: 'bounce 1.4s ease-in-out infinite'
  }
};

function ChatRoom() {
  const [roomId, setRoomId] = useState('');
  const [joined, setJoined] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [connectedPeers, setConnectedPeers] = useState(0);
  const [anonymousId, setAnonymousId] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [typingPeers, setTypingPeers] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [hasHistory, setHasHistory] = useState(false);
  
  const chatRef = useRef(null);
  const messagesEndRef = useRef(null);
  const chatInstanceRef = useRef(null);
  const typingTimerRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleJoin = async () => {
    if (!roomId.trim()) return;

    const anonId = generateAnonymousId();
    setAnonymousId(anonId);
    setMessages([]);
    setHasHistory(false);

    const chat = new WebRTCChat(SIGNALING_SERVER);
    await chat.initialize();

    chat.onMessage = (msg) => {
      setMessages(prev => [...prev, {
        ...msg,
        isMine: false
      }]);
    };

    chat.onPeerConnected = () => {
      setConnectedPeers(prev => prev + 1);
    };

    chat.onPeerDisconnected = () => {
      setConnectedPeers(prev => Math.max(0, prev - 1));
    };

    chat.onTyping = (peers) => {
      setTypingPeers(peers);
    };

    chat.onOfflineMessages = (offlineMsgs) => {
      if (offlineMsgs && offlineMsgs.length > 0) {
        const formatted = offlineMsgs.map(msg => ({
          ...msg,
          isMine: false,
          fromOffline: true
        }));
        setMessages(prev => [...formatted, ...prev]);
      }
    };

    chatInstanceRef.current = chat;
    chat.joinRoom(roomId.trim());
    setJoined(true);
    setIsConnected(true);
  };

  const handleLeave = () => {
    if (typingTimerRef.current) {
      clearTimeout(typingTimerRef.current);
    }
    
    if (chatInstanceRef.current) {
      chatInstanceRef.current.disconnect();
      chatInstanceRef.current = null;
    }
    setJoined(false);
    setIsConnected(false);
    setMessages([]);
    setConnectedPeers(0);
    setTypingPeers([]);
    setHasHistory(false);
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!message.trim() || !chatInstanceRef.current) return;

    const messageText = message.trim();
    const timestamp = Date.now();
    
    setMessages(prev => [...prev, {
      anonymousId,
      text: messageText,
      timestamp,
      isMine: true
    }]);

    await chatInstanceRef.current.sendMessage(messageText, anonymousId);
    setMessage('');
    
    chatInstanceRef.current.sendTyping(false);
    
    if (connectedPeers > 0 && chatInstanceRef.current) {
      const messageData = {
        anonymousId,
        text: messageText,
        timestamp
      };
      await chatInstanceRef.current.saveMessageToHistory(messageData, SIGNALING_SERVER);
    }
  };

  const handleTyping = (e) => {
    const value = e.target.value;
    setMessage(value);
    
    if (!chatInstanceRef.current) return;
    
    if (typingTimerRef.current) {
      clearTimeout(typingTimerRef.current);
    }
    
    if (value.trim().length > 0) {
      chatInstanceRef.current.sendTyping(true);
      
      typingTimerRef.current = setTimeout(() => {
        chatInstanceRef.current?.sendTyping(false);
      }, 2000);
    } else {
      chatInstanceRef.current.sendTyping(false);
    }
  };

  const handleLoadHistory = async () => {
    if (!chatInstanceRef.current || loadingHistory) return;
    
    setLoadingHistory(true);
    
    try {
      const history = await chatInstanceRef.current.loadHistory(SIGNALING_SERVER);
      
      if (history && history.length > 0) {
        const formatted = history.map(msg => ({
          ...msg,
          isMine: msg.anonymousId === anonymousId,
          fromHistory: true
        }));
        
        setMessages(prev => {
          const merged = [...formatted, ...prev];
          const unique = [];
          const seen = new Set();
          
          for (const msg of merged) {
            const key = `${msg.anonymousId}-${msg.timestamp}`;
            if (!seen.has(key)) {
              seen.add(key);
              unique.push(msg);
            }
          }
          
          return unique.sort((a, b) => a.timestamp - b.timestamp);
        });
        
        setHasHistory(true);
      }
    } catch (error) {
      console.error('Error loading history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const shortId = (id) => {
    return id?.substring(0, 8) || '未知';
  };

  const getTypingText = () => {
    if (typingPeers.length === 0) return null;
    if (typingPeers.length === 1) return `有人正在输入`;
    if (typingPeers.length === 2) return `${typingPeers.length} 人正在输入`;
    return `${typingPeers.length} 人正在输入`;
  };

  const getMessageStyle = (msg) => {
    if (msg.fromOffline && !msg.isMine) {
      return { ...styles.message, ...styles.messageOffline };
    }
    if (msg.fromHistory && !msg.isMine) {
      return { ...styles.message, ...styles.messageHistory };
    }
    if (msg.isMine) {
      return { ...styles.message, ...styles.messageMine };
    }
    return { ...styles.message, ...styles.messageOther };
  };

  return (
    <div style={styles.container}>
      <style>
        {`
          @keyframes pulse {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 1; }
          }
          @keyframes bounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-4px); }
          }
          .dot:nth-child(2) { animation-delay: 0.2s; }
          .dot:nth-child(3) { animation-delay: 0.4s; }
        `}
      </style>
      
      <h1 style={styles.header}>🔒 匿名聊天室 - 端到端加密</h1>

      {!joined ? (
        <>
          <div style={styles.info}>
            <p>欢迎使用端到端加密的匿名聊天室</p>
            <p>输入房间号并加入，只有在同一房间内的人才能通信</p>
            <p style={{ marginTop: '10px', fontSize: '12px' }}>
              💡 提示：消息使用 ECDH + AES-GCM 加密，只有通信双方能解密
            </p>
          </div>
          <div style={styles.joinForm}>
            <input
              type="text"
              placeholder="输入房间号 (如: secret-room-123)"
              value={roomId}
              onChange={(e) => setRoomId(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleJoin()}
              style={styles.input}
            />
            <button
              onClick={handleJoin}
              disabled={!roomId.trim()}
              style={{
                ...styles.button,
                opacity: roomId.trim() ? 1 : 0.5,
                cursor: roomId.trim() ? 'pointer' : 'not-allowed'
              }}
            >
              加入房间
            </button>
          </div>
        </>
      ) : (
        <>
          <div
            style={{
              ...styles.status,
              ...(isConnected ? styles.statusConnected : styles.statusDisconnected)
            }}
          >
            <strong>房间：</strong>{roomId} | 
            <strong> 你的匿名ID：</strong>{shortId(anonymousId)} | 
            <strong> 在线人数：</strong>{connectedPeers + 1}
          </div>

          <div style={styles.chatContainer}>
            <div style={styles.headerBar}>
              <span style={styles.peerList}>
                🔗 已连接 {connectedPeers} 位用户
              </span>
              <button
                onClick={handleLoadHistory}
                disabled={loadingHistory || connectedPeers === 0}
                style={{
                  ...styles.buttonSmall,
                  opacity: (connectedPeers > 0 && !loadingHistory) ? 1 : 0.5,
                  cursor: (connectedPeers > 0 && !loadingHistory) ? 'pointer' : 'not-allowed'
                }}
              >
                {loadingHistory ? '加载中...' : (hasHistory ? '已加载历史' : '加载历史消息')}
              </button>
            </div>

            {typingPeers.length > 0 && (
              <div style={styles.typingIndicator}>
                <span style={styles.loading}></span>
                {getTypingText()}
                <span style={styles.typingDots}>
                  <span className="dot" style={styles.dot}></span>
                  <span className="dot" style={styles.dot}></span>
                  <span className="dot" style={styles.dot}></span>
                </span>
              </div>
            )}

            <div style={styles.messages} ref={messagesEndRef}>
              {messages.length === 0 ? (
                <div style={styles.info}>
                  {connectedPeers > 0 
                    ? '开始聊天吧！你的消息会被端到端加密'
                    : '等待其他用户加入房间...'}
                </div>
              ) : (
                messages.map((msg, index) => (
                  <div
                    key={index}
                    style={getMessageStyle(msg)}
                  >
                    <div style={styles.messageHeader}>
                      {(msg.fromOffline || msg.fromHistory) && (
                        <span style={{
                          ...styles.messageTag,
                          ...(msg.fromOffline ? styles.tagOffline : styles.tagHistory)
                        }}>
                          {msg.fromOffline ? '离线' : '历史'}
                        </span>
                      )}
                      {msg.isMine ? '我' : shortId(msg.anonymousId)}
                    </div>
                    <div style={styles.messageText}>{msg.text}</div>
                    <div style={styles.messageTime}>
                      {formatTime(msg.timestamp)}
                    </div>
                  </div>
                ))
              )}
            </div>

            <form style={styles.inputForm} onSubmit={handleSend}>
              <input
                type="text"
                placeholder="输入消息..."
                value={message}
                onChange={handleTyping}
                style={styles.input}
                disabled={connectedPeers === 0}
              />
              <button
                type="submit"
                disabled={!message.trim() || connectedPeers === 0}
                style={{
                  ...styles.button,
                  opacity: (message.trim() && connectedPeers > 0) ? 1 : 0.5,
                  cursor: (message.trim() && connectedPeers > 0) ? 'pointer' : 'not-allowed'
                }}
              >
                发送
              </button>
              <button
                type="button"
                onClick={handleLeave}
                style={styles.buttonSecondary}
              >
                离开
              </button>
            </form>
          </div>
        </>
      )}
    </div>
  );
}

export default ChatRoom;
