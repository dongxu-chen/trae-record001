import React, { useState, useEffect } from 'react';
import { dbService } from '../utils/database.js';
import { PasswordGenerator } from '../utils/passwordGenerator.js';
import AddPasswordModal from './AddPasswordModal.jsx';

export default function ViewPasswordModal({ 
  passwordId, 
  onClose, 
  onUpdate, 
  onDelete, 
  onCopy,
  onCopyUsername,
  onShare 
}) {
  const [password, setPassword] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showEditModal, setShowEditModal] = useState(false);
  const [copiedField, setCopiedField] = useState(null);

  useEffect(() => {
    loadPassword();
  }, [passwordId]);

  const loadPassword = async () => {
    try {
      setLoading(true);
      const data = await dbService.getDecryptedPassword(passwordId);
      setPassword(data);
    } catch (error) {
      console.error('加载密码失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyPassword = async () => {
    try {
      await navigator.clipboard.writeText(password.password);
      await dbService.markAsUsed(passwordId);
      setCopiedField('password');
      setTimeout(() => setCopiedField(null), 2000);
    } catch (error) {
      console.error('复制失败:', error);
    }
  };

  const handleCopyUsername = async () => {
    try {
      await navigator.clipboard.writeText(password.username);
      setCopiedField('username');
      setTimeout(() => setCopiedField(null), 2000);
    } catch (error) {
      console.error('复制失败:', error);
    }
  };

  const handleUpdate = async (data) => {
    await onUpdate(passwordId, data);
    setShowEditModal(false);
    loadPassword();
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return '从未';
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  const getCategoryIcon = (category) => {
    const icons = {
      'social': '🌐',
      'work': '💼',
      'finance': '💰',
      'personal': '👤',
      'shopping': '🛒',
      'email': '📧',
      'entertainment': '🎮',
      'general': '🔑'
    };
    return icons[category] || '🔑';
  };

  const getCategoryLabel = (category) => {
    const labels = {
      'social': '社交媒体',
      'work': '工作',
      'finance': '金融',
      'personal': '个人',
      'shopping': '购物',
      'email': '邮箱',
      'entertainment': '娱乐',
      'general': '通用'
    };
    return labels[category] || '通用';
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

  if (!password) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p>密码记录不存在</p>
            <button className="btn btn-primary" style={{ marginTop: '16px' }} onClick={onClose}>
              关闭
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (showEditModal) {
    return (
      <AddPasswordModal
        initialData={password}
        onClose={() => setShowEditModal(false)}
        onSave={handleUpdate}
      />
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '32px' }}>{getCategoryIcon(password.category)}</span>
            <h2 className="modal-title">{password.title}</h2>
            {password.favorite && <span>⭐</span>}
          </div>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <div className="strength-bar" style={{ marginTop: 0 }}>
            <div className={`strength-fill ${PasswordGenerator.getStrengthClass(password.strength)}`}></div>
          </div>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            fontSize: '12px',
            marginTop: '8px'
          }}>
            <span style={{ color: PasswordGenerator.getStrengthColor(password.strength) }}>
              密码强度: {PasswordGenerator.getStrengthLabel(password.strength)}
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
              熵值: {password.entropy} bits
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2" style={{ marginBottom: '20px' }}>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              分类
            </div>
            <div>
              {getCategoryIcon(password.category)} {getCategoryLabel(password.category)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              上次使用
            </div>
            <div>{formatDate(password.lastUsed)}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              创建时间
            </div>
            <div>{formatDate(password.createdAt)}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              更新时间
            </div>
            <div>{formatDate(password.updatedAt)}</div>
          </div>
        </div>

        <div className="input-group">
          <label>用户名/邮箱</label>
          <div className="password-display">
            <span style={{ flex: 1 }}>{password.username || '-'}</span>
            <button
              type="button"
              className="btn btn-secondary btn-small"
              onClick={handleCopyUsername}
              disabled={!password.username}
            >
              {copiedField === 'username' ? '✓ 已复制' : '📋 复制'}
            </button>
          </div>
        </div>

        <div className="input-group">
          <label>密码</label>
          <div className="password-display">
            <span 
              style={{ flex: 1 }}
              className={showPassword ? '' : 'password-masked'}
            >
              {showPassword ? password.password : '•'.repeat(Math.min(password.password.length, 20))}
            </span>
            <button
              type="button"
              className="btn btn-secondary btn-small"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? '🙈' : '👁️'}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-small"
              onClick={handleCopyPassword}
            >
              {copiedField === 'password' ? '✓ 已复制' : '📋 复制'}
            </button>
          </div>
        </div>

        {password.url && (
          <div className="input-group">
            <label>网站/应用</label>
            <div className="password-display">
              <a 
                href={password.url} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ color: 'var(--primary)', flex: 1 }}
              >
                {password.url}
              </a>
              <button
                type="button"
                className="btn btn-secondary btn-small"
                onClick={() => window.open(password.url, '_blank')}
              >
                🔗 打开
              </button>
            </div>
          </div>
        )}

        {password.tags && password.tags.length > 0 && (
          <div className="input-group">
            <label>标签</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {password.tags.map((tag, i) => (
                <span 
                  key={i}
                  style={{
                    background: 'var(--bg-tertiary)',
                    padding: '4px 12px',
                    borderRadius: '20px',
                    fontSize: '12px'
                  }}
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {password.notes && (
          <div className="input-group">
            <label>备注</label>
            <div style={{
              background: 'var(--bg-primary)',
              padding: '12px',
              borderRadius: '8px',
              whiteSpace: 'pre-wrap',
              fontSize: '14px'
            }}>
              {password.notes}
            </div>
          </div>
        )}

        <div style={{ 
          display: 'flex', 
          gap: '12px', 
          justifyContent: 'flex-end',
          marginTop: '24px'
        }}>
          <button 
            type="button" 
            className="btn btn-secondary"
            onClick={() => onShare(passwordId)}
          >
            📤 分享
          </button>
          <button 
            type="button" 
            className="btn btn-secondary"
            onClick={() => setShowEditModal(true)}
          >
            ✏️ 编辑
          </button>
          <button 
            type="button" 
            className="btn btn-danger"
            onClick={() => onDelete(passwordId)}
          >
            🗑️ 删除
          </button>
        </div>
      </div>
    </div>
  );
}
