import { useState, useRef } from 'react';

function MessageList({ messages, currentUser }) {
  const [playingId, setPlayingId] = useState(null);
  const audioRef = useRef(null);

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const renderMessageContent = (msg) => {
    if (msg.type === 'voice') {
      return (
        <div className="voice-message">
          <button 
            className="play-btn"
            onClick={() => togglePlay(msg)}
          >
            {playingId === msg.id ? '⏸' : '▶'}
          </button>
          <div className="voice-wave">
            <div className="wave-bar" style={{ height: `${20 + Math.random() * 60}%` }}></div>
            <div className="wave-bar" style={{ height: `${30 + Math.random() * 50}%` }}></div>
            <div className="wave-bar" style={{ height: `${40 + Math.random() * 40}%` }}></div>
            <div className="wave-bar" style={{ height: `${30 + Math.random() * 50}%` }}></div>
            <div className="wave-bar" style={{ height: `${20 + Math.random() * 60}%` }}></div>
          </div>
          <span className="voice-duration">{formatDuration(msg.duration)}</span>
          {playingId === msg.id && (
            <audio 
              ref={audioRef}
              src={msg.url} 
              autoPlay 
              onEnded={() => setPlayingId(null)}
            />
          )}
        </div>
      );
    }

    let result = msg.content;
    if (msg.mentions && msg.mentions.length > 0) {
      msg.mentions.forEach(username => {
        const regex = new RegExp(`@${username}`, 'g');
        result = result.replace(regex, `<span class="mention">@${username}</span>`);
      });
    }
    return <span dangerouslySetInnerHTML={{ __html: result }} />;
  };

  const togglePlay = (msg) => {
    if (playingId === msg.id) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      setPlayingId(null);
    } else {
      setPlayingId(msg.id);
    }
  };

  const renderReadStatus = (msg) => {
    if (msg.userId !== currentUser.id) return null;
    
    const readCount = msg.readCount || 0;
    const totalUsers = msg.totalUsers || 0;
    
    if (totalUsers <= 1) return null;
    
    return (
      <div className="read-status" title={`已读: ${readCount}/${totalUsers - 1}`}>
        <span className="read-check">✓</span>
        {readCount > 0 && (
          <span className="read-count">{readCount}</span>
        )}
      </div>
    );
  };

  return (
    <div className="message-list">
      {messages.length === 0 ? (
        <div className="no-messages">
          <p>还没有消息，发送第一条消息吧！</p>
        </div>
      ) : (
        messages.map((msg, index) => {
          const isOwn = msg.userId === currentUser.id;
          const isMentioned = msg.mentions?.includes(currentUser.username);
          const showHeader = index === 0 || messages[index - 1].userId !== msg.userId;
          const showFooter = index === messages.length - 1 || messages[index + 1].userId !== msg.userId;

          return (
            <div
              key={msg.id}
              className={`message ${isOwn ? 'own' : ''} ${isMentioned ? 'mentioned' : ''}`}
            >
              {showHeader && (
                <div className="message-header">
                  <div className="avatar">{msg.username.charAt(0).toUpperCase()}</div>
                  <div className="sender-info">
                    <span className="sender-name">{msg.username}</span>
                    <span className="message-time">{formatTime(msg.timestamp)}</span>
                  </div>
                </div>
              )}
              <div className={`message-content ${!showHeader ? 'no-header' : ''} ${msg.type === 'voice' ? 'voice' : ''}`}>
                {renderMessageContent(msg)}
              </div>
              {showFooter && renderReadStatus(msg)}
            </div>
          );
        })
      )}
    </div>
  );
}

export default MessageList;