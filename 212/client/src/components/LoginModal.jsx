import { useState } from 'react';

function LoginModal({ onLogin }) {
  const [username, setUsername] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (username.trim()) {
      onLogin(username.trim());
    }
  };

  return (
    <div className="login-modal">
      <div className="login-box">
        <h1>实时聊天室</h1>
        <p>请输入您的昵称开始聊天</p>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="输入昵称..."
            maxLength={20}
            autoFocus
          />
          <button type="submit" disabled={!username.trim()}>
            进入聊天室
          </button>
        </form>
      </div>
    </div>
  );
}

export default LoginModal;