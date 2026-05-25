import React from 'react';
import { PasswordGenerator } from '../utils/passwordGenerator.js';

export default function PasswordList({ 
  passwords, 
  searchQuery, 
  onSearchChange, 
  onAdd, 
  onView, 
  onCopy, 
  onCopyUsername,
  onToggleFavorite,
  onShare,
  stats 
}) {
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

  const formatDate = (timestamp) => {
    if (!timestamp) return '从未';
    const date = new Date(timestamp);
    return date.toLocaleDateString('zh-CN');
  };

  return (
    <div className="fade-in">
      <div className="grid grid-cols-3" style={{ marginBottom: '24px' }}>
        <div className="card">
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔐</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{stats?.total || 0}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>总密码数</div>
        </div>
        <div className="card">
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>⚠️</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--warning)' }}>{stats?.weakCount || 0}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>弱密码</div>
        </div>
        <div className="card">
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔄</div>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--danger)' }}>{stats?.duplicateCount || 0}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>重复密码</div>
        </div>
      </div>

      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '20px',
        gap: '16px',
        flexWrap: 'wrap'
      }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '250px' }}>
          <input
            type="text"
            placeholder="搜索密码..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            style={{ paddingLeft: '40px' }}
          />
          <span style={{ 
            position: 'absolute', 
            left: '12px', 
            top: '50%', 
            transform: 'translateY(-50%)',
            fontSize: '18px'
          }}>🔍</span>
        </div>
        <button className="btn btn-primary" onClick={onAdd}>
          ➕ 添加密码
        </button>
      </div>

      {passwords.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔒</div>
          <h3 style={{ marginBottom: '8px' }}>
            {searchQuery ? '未找到匹配的密码' : '暂无密码记录'}
          </h3>
          <p style={{ marginBottom: '20px' }}>
            {searchQuery ? '尝试使用其他关键词搜索' : '点击上方按钮添加您的第一个密码'}
          </p>
          {!searchQuery && (
            <button className="btn btn-primary" onClick={onAdd}>
              添加第一个密码
            </button>
          )}
        </div>
      ) : (
        <div>
          {passwords.map((pwd) => (
            <div key={pwd.id} className="password-item fade-in">
              <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flex: 1 }}>
                <div style={{ fontSize: '32px' }}>{getCategoryIcon(pwd.category)}</div>
                <div className="password-info">
                  <div className="password-title">
                    {pwd.favorite && <span style={{ marginRight: '8px' }}>⭐</span>}
                    {pwd.title}
                  </div>
                  <div className="password-username">
                    {pwd.username}
                    {pwd.url && (
                      <span style={{ marginLeft: '12px' }}>
                        🌐 {pwd.url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '16px', marginTop: '8px', alignItems: 'center' }}>
                    <div className="strength-bar" style={{ width: '100px', marginTop: 0 }}>
                      <div className={`strength-fill ${PasswordGenerator.getStrengthClass(pwd.strength)}`}></div>
                    </div>
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {PasswordGenerator.getStrengthLabel(pwd.strength)}
                    </span>
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      更新于: {formatDate(pwd.updatedAt)}
                    </span>
                    {pwd.lastUsed && (
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        上次使用: {formatDate(pwd.lastUsed)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="password-actions">
                <button 
                  className="btn btn-secondary btn-small"
                  onClick={() => onToggleFavorite(pwd.id)}
                  title={pwd.favorite ? '取消收藏' : '收藏'}
                >
                  {pwd.favorite ? '⭐' : '☆'}
                </button>
                <button 
                  className="btn btn-secondary btn-small"
                  onClick={() => onCopyUsername(pwd.username)}
                  title="复制用户名"
                >
                  👤
                </button>
                <button 
                  className="btn btn-secondary btn-small"
                  onClick={() => onCopy(pwd.id)}
                  title="复制密码"
                >
                  📋
                </button>
                <button 
                  className="btn btn-secondary btn-small"
                  onClick={() => onShare(pwd.id)}
                  title="分享"
                >
                  📤
                </button>
                <button 
                  className="btn btn-primary btn-small"
                  onClick={() => onView(pwd.id)}
                >
                  查看
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
