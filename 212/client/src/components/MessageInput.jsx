function MessageInput({ value, onChange, onKeyPress, onSend, showEmoji, onToggleEmoji, onToggleVoice }) {
  return (
    <div className="message-input-container">
      <button
        className="emoji-btn"
        onClick={onToggleEmoji}
        title="表情"
      >
        😊
      </button>
      <button
        className="emoji-btn"
        onClick={onToggleVoice}
        title="语音消息"
      >
        🎤
      </button>
      <input
        type="text"
        className="message-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyPress={onKeyPress}
        placeholder="输入消息... (@用户名 可以提醒用户)"
      />
      <button
        className="send-btn"
        onClick={onSend}
        disabled={!value.trim()}
      >
        发送
      </button>
    </div>
  );
}

export default MessageInput;