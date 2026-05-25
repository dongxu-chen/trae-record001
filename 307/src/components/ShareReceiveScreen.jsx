import React, { useState, useEffect } from 'react';
import { ShareService } from '../utils/share.js';
import { dbService } from '../utils/database.js';
import { PasswordGenerator } from '../utils/passwordGenerator.js';

export default function ShareReceiveScreen({ token, showNotification }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sharedData, setSharedData] = useState(null);
  const [sharePassword, setSharePassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [requirePassword, setRequirePassword] = useState(false);
  const [copiedField, setCopiedField] = useState(null);
  const [savedToVault, setSavedToVault] = useState(false);

  useEffect(() => {
    checkShare();
  }, [token]);

  const checkShare = async () => {
    try {
      setLoading(true);
      setError(null);

      const sharedPasswords = await dbService.getSharedPasswords();
      const shareRecord = sharedPasswords.find(s => s.token === token);

      if (!shareRecord) {
        setError('分享链接无效或已过期');
        return;
      }

      if (shareRecord.expiresAt < Date.now()) {
        await dbService.deleteSharedPassword(shareRecord.id);
        setError('分享链接已过期');
        return;
      }

      if (shareRecord.accessCount >= shareRecord.maxAccesses) {
        await dbService.deleteSharedPassword(shareRecord.id);
        setError('分享链接已达到最大访问次数');
        return;
      }

      if (shareRecord.requirePassword) {
        setRequirePassword(true);
      } else {
        await loadSharedData(null);
      }
    } catch (err) {
      setError('加载分享数据失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadSharedData = async (password) => {
    try {
      setLoading(true);
      const data = await ShareService.getSharedData(token, password);
      setSharedData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitPassword = (e) => {
    e.preventDefault();
    if (!sharePassword) {
      setError('请输入访问密码');
      return;
    }
    loadSharedData(sharePassword);
  };

  const copyToClipboard = async (text, field) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const handleSaveToVault = async () => {
    try {
      if (!sharedData) return;

      const existing = await dbService.getAllPasswords(false);
      const isDuplicate = existing.some(p => 
        p.title === sharedData.title && 
        p.username === sharedData.username
      );

      if (isDuplicate) {
        if (!confirm('密码库中已存在类似记录，是否仍要保存？')) {
          return;
        }
      }

      const strength = PasswordGenerator.checkStrength(sharedData.password);

      await dbService.addPassword({
        title: sharedData.title,
        username: sharedData.username,
        password: sharedData.password,
        url: sharedData.url || '',
        category: 'general',
        notes: sharedData.notes || `从分享链接导入\n分享时间: ${new Date(sharedData.sharedAt).toLocaleString('zh-CN')}`,
        tags: ['shared'],
        strength: strength.strength,
        entropy: strength.entropy
      });

      setSavedToVault(true);
      showNotification('密码已保存到您的密码库', 'success');
    } catch (err) {
      showNotification('保存失败: ' + err.message, 'error');
    }
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        padding: '20px'
      }}>
        <div className="card" style={{ textAlign: 'center', padding: '60px', maxWidth: '420px', width: '100%' }}>
          <div className="loading" style={{ margin: '0 auto 16px' }}></div>
          <p>正在加载分享数据...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        padding: '20px'
      }}>
        <div className="card" style={{ textAlign: 'center', padding: '60px', maxWidth: '420px', width: '100%' }}>
          <div style={{ fontSize: '64px', marginBottom: '16px' }}>❌</div>
          <h2 style={{ marginBottom: '8px' }}>无法访问分享</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
            {error}
          </p>
          <button 
            className="btn btn-primary"
            onClick={() => window.location.href = window.location.origin + window.location.pathname}
          >
            返回首页
          </button>
        </div>
      </div>
    );
  }

  if (requirePassword && !sharedData) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        padding: '20px'
      }}>
        <div className="card" style={{ padding: '40px', maxWidth: '420px', width: '100%' }}>
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <div style={{ fontSize: '64px', marginBottom: '16px' }}>🔒</div>
            <h2 style={{ marginBottom: '8px' }}>密码保护的分享</h2>
            <p style={{ color: 'var(--text-secondary)' }}>
              此分享链接需要访问密码才能查看
            </p>
          </div>

          <form onSubmit={handleSubmitPassword}>
            <div className="input-group">
              <label>访问密码</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={sharePassword}
                  onChange={(e) => setSharePassword(e.target.value)}
                  placeholder="请输入访问密码"
                  style={{ paddingRight: '40px' }}
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
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
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </button>
              </div>
            </div>

            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ width: '100%' }}
            >
              解锁分享
            </button>
          </form>

          <div style={{ 
            marginTop: '24px', 
            padding: '16px', 
            background: 'var(--bg-tertiary)', 
            borderRadius: '8px',
            fontSize: '13px',
            color: 'var(--text-secondary)'
          }}>
            💡 提示：访问密码应由分享者通过安全渠道单独提供给您。
          </div>
        </div>
      </div>
    );
  }

  if (sharedData) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        padding: '20px'
      }}>
        <div className="card" style={{ maxWidth: '500px', width: '100%' }}>
          <div style={{ textAlign: 'center', marginBottom: '24px' }}>
            <div style={{ fontSize: '64px', marginBottom: '16px' }}>📨</div>
            <h2 style={{ marginBottom: '8px' }}>您收到了密码分享</h2>
            <p style={{ color: 'var(--text-secondary)' }}>
              以下信息已使用端到端加密安全传输
            </p>
          </div>

          <div className="card" style={{ background: 'var(--success-bg)', border: '1px solid var(--success)', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{ fontSize: '32px' }}>🔑</div>
              <div>
                <div style={{ fontSize: '18px', fontWeight: '500' }}>{sharedData.title}</div>
                {sharedData.username && (
                  <div style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                    {sharedData.username}
                  </div>
                )}
              </div>
            </div>

            {sharedData.username && (
              <div className="input-group">
                <label>用户名/邮箱</label>
                <div className="password-display">
                  <span style={{ flex: 1 }}>{sharedData.username}</span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-small"
                    onClick={() => copyToClipboard(sharedData.username, 'username')}
                  >
                    {copiedField === 'username' ? '✓ 已复制' : '📋 复制'}
                  </button>
                </div>
              </div>
            )}

            <div className="input-group">
              <label>密码</label>
              <div className="password-display">
                <span 
                  style={{ flex: 1 }}
                  className={showPassword ? '' : 'password-masked'}
                >
                  {showPassword ? sharedData.password : '•'.repeat(Math.min(sharedData.password.length, 20))}
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
                  onClick={() => copyToClipboard(sharedData.password, 'password')}
                >
                  {copiedField === 'password' ? '✓ 已复制' : '📋 复制'}
                </button>
              </div>
            </div>

            {sharedData.url && (
              <div className="input-group">
                <label>网站/应用</label>
                <div className="password-display">
                  <a 
                    href={sharedData.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ color: 'var(--primary)', flex: 1 }}
                  >
                    {sharedData.url}
                  </a>
                  <button
                    type="button"
                    className="btn btn-secondary btn-small"
                    onClick={() => window.open(sharedData.url, '_blank')}
                  >
                    🔗 打开
                  </button>
                </div>
              </div>
            )}

            {sharedData.notes && (
              <div className="input-group">
                <label>备注</label>
                <div style={{
                  background: 'var(--bg-primary)',
                  padding: '12px',
                  borderRadius: '8px',
                  whiteSpace: 'pre-wrap',
                  fontSize: '14px'
                }}>
                  {sharedData.notes}
                </div>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2" style={{ marginBottom: '20px' }}>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                分享时间
              </div>
              <div style={{ fontSize: '13px' }}>{formatDate(sharedData.sharedAt)}</div>
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                过期时间
              </div>
              <div style={{ fontSize: '13px' }}>{formatDate(sharedData.expiresAt)}</div>
            </div>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                剩余访问次数
              </div>
              <div style={{ fontSize: '13px' }}>
                {sharedData.remainingAccesses > 0 ? sharedData.remainingAccesses + '次' : '无限制'}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1 }}
              onClick={() => window.location.href = window.location.origin + window.location.pathname}
            >
              关闭
            </button>
            {!savedToVault && (
              <button
                type="button"
                className="btn btn-primary"
                style={{ flex: 1 }}
                onClick={handleSaveToVault}
              >
                💾 保存到我的密码库
              </button>
            )}
            {savedToVault && (
              <button
                type="button"
                className="btn btn-success"
                style={{ flex: 1 }}
                onClick={() => window.location.href = window.location.origin + window.location.pathname}
              >
                ✅ 已保存，返回首页
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
