import React, { useState, useEffect } from 'react';
import { dbService } from '../utils/database.js';
import { ShareService } from '../utils/share.js';

const EXPIRE_OPTIONS = [
  { value: 15 * 60 * 1000, label: '15分钟' },
  { value: 60 * 60 * 1000, label: '1小时' },
  { value: 24 * 60 * 60 * 1000, label: '24小时' },
  { value: 7 * 24 * 60 * 60 * 1000, label: '7天' },
  { value: 30 * 24 * 60 * 60 * 1000, label: '30天' }
];

const ACCESS_OPTIONS = [
  { value: 1, label: '1次' },
  { value: 5, label: '5次' },
  { value: 10, label: '10次' },
  { value: 100, label: '无限制' }
];

export default function ShareModal({ passwordId, onClose, onShare }) {
  const [password, setPassword] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expiresIn, setExpiresIn] = useState(24 * 60 * 60 * 1000);
  const [maxAccesses, setMaxAccesses] = useState(1);
  const [requirePassword, setRequirePassword] = useState(false);
  const [sharePassword, setSharePassword] = useState('');
  const [showSharePassword, setShowSharePassword] = useState(false);
  const [shareResult, setShareResult] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadPassword();
  }, [passwordId]);

  const loadPassword = async () => {
    try {
      setLoading(true);
      const data = await dbService.getPassword(passwordId);
      setPassword(data);
    } catch (error) {
      console.error('加载密码失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateShare = async () => {
    try {
      if (requirePassword && !sharePassword) {
        alert('请输入分享密码');
        return;
      }

      const result = await onShare(passwordId, {
        expiresIn,
        maxAccesses,
        requirePassword,
        sharePassword: requirePassword ? sharePassword : null
      });

      setShareResult(result);
    } catch (error) {
      console.error('创建分享失败:', error);
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('复制失败:', error);
    }
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div className="loading"></div>
            <p style={{ marginTop: '16px' }}>加载中...</p>
          </div>
        </div>
      </div>
    );
  }

  if (shareResult) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2 className="modal-title">✅ 分享链接已生成</h2>
            <button className="close-btn" onClick={onClose}>×</button>
          </div>

          <div className="card" style={{ background: 'var(--success-bg)', border: '1px solid var(--success)' }}>
            <div style={{ fontSize: '48px', textAlign: 'center', marginBottom: '16px' }}>🎉</div>
            <p style={{ textAlign: 'center', marginBottom: '20px' }}>
              分享链接已创建成功，请安全地发送给接收者。
            </p>

            <div className="input-group">
              <label>分享链接</label>
              <div className="password-display">
                <span style={{ flex: 1, fontFamily: 'monospace', fontSize: '12px', wordBreak: 'break-all' }}>
                  {shareResult.shareUrl}
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-small"
                  onClick={() => copyToClipboard(shareResult.shareUrl)}
                >
                  {copied ? '✓ 已复制' : '📋 复制'}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2" style={{ marginTop: '20px' }}>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  过期时间
                </div>
                <div>{formatDate(shareResult.expiresAt)}</div>
              </div>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  最大访问次数
                </div>
                <div>{shareResult.maxAccesses >= 100 ? '无限制' : shareResult.maxAccesses + '次'}</div>
              </div>
            </div>

            {requirePassword && (
              <div className="alert alert-warning" style={{ marginTop: '20px' }}>
                ⚠️ 此分享链接需要额外的访问密码，请通过安全渠道单独告知接收者。
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ flex: 1 }}
                onClick={() => setShareResult(null)}
              >
                创建新链接
              </button>
              <button
                type="button"
                className="btn btn-primary"
                style={{ flex: 1 }}
                onClick={onClose}
              >
                完成
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">📤 分享密码</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="card" style={{ background: 'var(--bg-tertiary)', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ fontSize: '32px' }}>🔑</div>
            <div>
              <div style={{ fontWeight: '500' }}>{password?.title}</div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                {password?.username}
              </div>
            </div>
          </div>
        </div>

        <div className="input-group">
          <label>链接有效期</label>
          <select
            value={expiresIn}
            onChange={(e) => setExpiresIn(Number(e.target.value))}
          >
            {EXPIRE_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="input-group">
          <label>最大访问次数</label>
          <select
            value={maxAccesses}
            onChange={(e) => setMaxAccesses(Number(e.target.value))}
          >
            {ACCESS_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="input-group">
          <label className="checkbox-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="checkbox"
              checked={requirePassword}
              onChange={(e) => setRequirePassword(e.target.checked)}
            />
            <span>设置额外的访问密码</span>
          </label>
        </div>

        {requirePassword && (
          <div className="input-group">
            <label>访问密码</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showSharePassword ? 'text' : 'password'}
                value={sharePassword}
                onChange={(e) => setSharePassword(e.target.value)}
                placeholder="请输入访问密码"
                style={{ paddingRight: '40px' }}
              />
              <button
                type="button"
                onClick={() => setShowSharePassword(!showSharePassword)}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '16px'
                }}
              >
                {showSharePassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>
        )}

        <div className="alert alert-warning" style={{ marginTop: '20px' }}>
          <strong>⚠️ 安全提示：</strong>
          <ul style={{ marginTop: '8px', paddingLeft: '20px', fontSize: '13px' }}>
            <li>分享链接包含加密的密码信息，请通过安全渠道发送</li>
            <li>设置较短的有效期和访问次数以降低风险</li>
            <li>避免在公共网络或不安全的渠道发送分享链接</li>
          </ul>
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px' }}>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            取消
          </button>
          <button type="button" className="btn btn-primary" onClick={handleCreateShare}>
            创建分享链接
          </button>
        </div>
      </div>
    </div>
  );
}
