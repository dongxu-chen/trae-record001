import React, { useState, useRef, useEffect } from 'react';
import useMeetingStore from '../store/useMeetingStore';
import { EmojiIcon, SendIcon } from './icons';

const EMOJIS = [
  '😀', '😂', '🥰', '😎', '🤔', '👍', '👎', '👏',
  '🎉', '❤️', '🔥', '💯', '✨', '😢', '😡', '🤯',
  '👋', '🙏', '✌️', '🤝', '💪', '🦾', '👀', '💡'
];

const ChatPanel = ({ onSendMessage, roomId }) => {
  const { messages, user } = useMeetingStore();
  const [inputValue, setInputValue] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setShowEmojiPicker(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onSendMessage?.(roomId, inputValue.trim(), 'text');
      setInputValue('');
    }
  };

  const handleEmojiClick = (emoji) => {
    setInputValue(prev => prev + emoji);
  };

  const handleEmojiSend = (emoji) => {
    onSendMessage?.(roomId, emoji, 'emoji');
    setShowEmojiPicker(false);
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="w-80 h-full bg-slate-800 border-l border-slate-700 flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <h3 className="text-lg font-semibold text-white">聊天</h3>
        <p className="text-sm text-slate-400">{messages.length} 条消息</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <p className="text-sm">暂无消息</p>
            <p className="text-xs mt-1">发送第一条消息开始聊天</p>
          </div>
        ) : (
          messages.map((message) => {
            const isOwn = message.userId === user?.id;
            return (
              <div
                key={message.id}
                className={`chat-message flex ${isOwn ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%] ${isOwn ? 'order-2' : 'order-1'}`}>
                  {!isOwn && (
                    <p className="text-xs text-slate-400 mb-1 px-1">
                      {message.userName}
                    </p>
                  )}
                  <div
                    className={`rounded-2xl px-4 py-2 ${
                      isOwn
                        ? 'bg-primary-500 text-white rounded-br-md'
                        : 'bg-slate-700 text-white rounded-bl-md'
                    }`}
                  >
                    {message.type === 'emoji' ? (
                      <span className="text-3xl">{message.content}</span>
                    ) : (
                      <p className="text-sm break-words">{message.content}</p>
                    )}
                  </div>
                  <p className={`text-xs text-slate-500 mt-1 px-1 ${
                    isOwn ? 'text-right' : 'text-left'
                  }`}>
                    {formatTime(message.timestamp)}
                  </p>
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      <div ref={containerRef} className="p-4 border-t border-slate-700 relative">
        {showEmojiPicker && (
          <div className="absolute bottom-full right-4 mb-2 bg-slate-700 rounded-xl p-3 shadow-xl border border-slate-600 z-50 w-64">
            <p className="text-xs text-slate-400 mb-2">常用表情</p>
            <div className="grid grid-cols-8 gap-1">
              {EMOJIS.map((emoji, index) => (
                <button
                  key={index}
                  onClick={() => handleEmojiClick(emoji)}
                  onDoubleClick={() => handleEmojiSend(emoji)}
                  className="text-xl hover:bg-slate-600 rounded p-1 transition-colors"
                  title={emoji}
                >
                  {emoji}
                </button>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowEmojiPicker(!showEmojiPicker)}
            className={`p-2 rounded-lg transition-colors ${
              showEmojiPicker
                ? 'bg-primary-500 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            <EmojiIcon className="w-5 h-5" />
          </button>

          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="输入消息..."
            className="flex-1 bg-slate-700 text-white placeholder-slate-400 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />

          <button
            type="submit"
            disabled={!inputValue.trim()}
            className="p-2 rounded-lg bg-primary-500 text-white hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <SendIcon className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;
