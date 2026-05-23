import { useState, useEffect, useRef, useCallback } from 'react';
import EmojiPicker from 'emoji-picker-react';
import MessageList from './MessageList';
import UserList from './UserList';
import MessageInput from './MessageInput';
import VoiceRecorder from './VoiceRecorder';

function ChatRoom({ room, messages, onlineUsers, typingUsers, user, onSendMessage, onSendVoice, onTyping, onLeave, onLoadOlder, onReadReceipt, onOpenSearch }) {
  const [showEmoji, setShowEmoji] = useState(false);
  const [showVoiceRecorder, setShowVoiceRecorder] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const messagesEndRef = useRef(null);
  const messagesAreaRef = useRef(null);
  const typingTimeoutRef = useRef(null);
  const isInitialLoad = useRef(true);
  const lastReadIdRef = useRef(null);

  useEffect(() => {
    if (isInitialLoad.current && messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
      isInitialLoad.current = false;
    }
  }, [messages]);

  const handleScroll = useCallback(async () => {
    if (!messagesAreaRef.current || loadingOlder || !hasMore) return;
    
    const { scrollTop } = messagesAreaRef.current;
    if (scrollTop < 50) {
      setLoadingOlder(true);
      const previousScrollHeight = messagesAreaRef.current.scrollHeight;
      const loaded = await onLoadOlder();
      if (!loaded) {
        setHasMore(false);
      }
      setTimeout(() => {
        if (messagesAreaRef.current) {
          messagesAreaRef.current.scrollTop = messagesAreaRef.current.scrollHeight - previousScrollHeight;
        }
        setLoadingOlder(false);
      }, 100);
    }
  }, [loadingOlder, hasMore, onLoadOlder]);

  const handleEmojiClick = (emojiData) => {
    setInputMessage(prev => prev + emojiData.emoji);
  };

  const handleTyping = (text) => {
    setInputMessage(text);
    
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    if (text) {
      onTyping(room.id, true);
      typingTimeoutRef.current = setTimeout(() => {
        onTyping(room.id, false);
      }, 2000);
    } else {
      onTyping(room.id, false);
    }
  };

  const handleSend = () => {
    if (inputMessage.trim()) {
      const mentionRegex = /@(\w+)/g;
      const mentions = [];
      let match;
      while ((match = mentionRegex.exec(inputMessage)) !== null) {
        mentions.push(match[1]);
      }
      
      onSendMessage(inputMessage.trim(), mentions);
      setInputMessage('');
      onTyping(room.id, false);
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    isInitialLoad.current = true;
    setHasMore(true);
    lastReadIdRef.current = null;
  }, [room.id]);

  useEffect(() => {
    if (messages.length > 0 && onReadReceipt) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.userId !== user.id && lastMessage.id !== lastReadIdRef.current) {
        lastReadIdRef.current = lastMessage.id;
        onReadReceipt(lastMessage.id);
      }
    }
  }, [messages, user.id, onReadReceipt]);

  const handleVoiceRecorded = (blob, duration) => {
    if (onSendVoice) {
      onSendVoice(blob, duration);
    }
    setShowVoiceRecorder(false);
  };

  return (
    <div className="chat-room">
      <div className="chat-header">
        <div className="room-title">
          <span className="room-icon">#</span>
          <h2>{room.name}</h2>
        </div>
        <div className="header-actions">
          <button className="header-btn" onClick={onOpenSearch} title="搜索消息">
            🔍
          </button>
          <button className="leave-btn" onClick={onLeave}>
            退出
          </button>
        </div>
      </div>
      
      <div className="chat-content">
        <div className="messages-area" ref={messagesAreaRef} onScroll={handleScroll}>
          {loadingOlder && (
            <div className="loading-more">
              <span>加载中...</span>
            </div>
          )}
          {!hasMore && messages.length > 0 && (
            <div className="no-more">
              <span>没有更多消息了</span>
            </div>
          )}
          <MessageList messages={messages} currentUser={user} onlineUsers={onlineUsers} />
          {typingUsers.length > 0 && (
            <div className="typing-indicator">
              <span>{typingUsers.map(u => u.username).join(', ')} 正在输入...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <UserList users={onlineUsers} currentUserId={user.id} />
      </div>
      
      <div className="chat-input-area">
        <div className="input-wrapper">
          {showVoiceRecorder ? (
            <VoiceRecorder
              onCancel={() => setShowVoiceRecorder(false)}
              onRecorded={handleVoiceRecorded}
            />
          ) : (
            <MessageInput
              value={inputMessage}
              onChange={handleTyping}
              onKeyPress={handleKeyPress}
              onSend={handleSend}
              showEmoji={showEmoji}
              onToggleEmoji={() => setShowEmoji(!showEmoji)}
              onToggleVoice={() => setShowVoiceRecorder(true)}
            />
          )}
          {showEmoji && (
            <div className="emoji-picker-container">
              <EmojiPicker onEmojiClick={handleEmojiClick} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ChatRoom;