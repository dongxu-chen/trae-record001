import React, { useState } from 'react';

function ShareModal({ url, onClose }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      const textArea = document.createElement('textarea');
      textArea.value = url;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        <h2 className="modal-title">
          📤 分享路线
        </h2>
        <p style={{ marginBottom: '16px', color: '#666', fontSize: '14px' }}>
          将以下链接复制给好友，他们即可查看您规划的路线：
        </p>
        <div className="modal-url-box">
          <div className="modal-url">{url}</div>
        </div>
        <div className="modal-actions">
          <button className="modal-btn secondary" onClick={onClose}>
            关闭
          </button>
          <button className="modal-btn primary" onClick={handleCopy}>
            {copied ? '✅ 已复制' : '📋 复制链接'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ShareModal;
