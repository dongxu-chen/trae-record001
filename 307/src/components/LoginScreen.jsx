import React, { useState } from 'react';
import { PasswordGenerator, PasswordStrength } from '../utils/passwordGenerator.js';

export default function LoginScreen({ onCreateVault, onUnlock, hasVault }) {
  const [mode, setMode] = useState(hasVault ? 'login' : 'create');
  const [masterPassword, setMasterPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [strength, setStrength] = useState(null);

  const handlePasswordChange = (e) => {
    const password = e.target.value;
    setMasterPassword(password);
    if (mode === 'create') {
      setStrength(PasswordGenerator.checkStrength(password));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (mode === 'create') {
      if (masterPassword.length < 8) {
        alert('主密码长度至少8位');
        return;
      }
      if (masterPassword !== confirmPassword) {
        alert('两次输入的密码不一致');
        return;
      }
      onCreateVault(masterPassword);
    } else {
      onUnlock(masterPassword);
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      padding: '20px'
    }}>
      <div className="card" style={{ maxWidth: '420px', width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔐</div>
          <h1 style={{ fontSize: '24px', marginBottom: '8px' }}>安全密码管理器</h1>
          <p style={{ color: 'var(--text-secondary)' }}>
            {mode === 'create' ? '创建您的密码库' : '解锁您的密码库'}
          </p>
        </div>

        <div className="tabs" style={{ marginBottom: '24px' }}>
          <button 
            className={`tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => setMode('login')}
          >
            登录
          </button>
          <button 
            className={`tab ${mode === 'create' ? 'active' : ''}`}
            onClick={() => setMode('create')}
          >
            创建账户
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label>主密码</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                value={masterPassword}
                onChange={handlePasswordChange}
                placeholder="请输入主密码"
                autoComplete="current-password"
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

          {mode === 'create' && (
            <>
              {strength && (
                <div className="input-group">
                  <div className="strength-bar">
                    <div className={`strength-fill ${PasswordGenerator.getStrengthClass(strength.strength)}`}></div>
                  </div>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    fontSize: '12px',
                    marginTop: '8px'
                  }}>
                    <span>密码强度: {PasswordGenerator.getStrengthLabel(strength.strength)}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>熵值: {strength.entropy} bits</span>
                  </div>
                  {strength.feedback.length > 0 && (
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                      {strength.feedback.map((fb, i) => (
                        <div key={i}>• {fb}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="input-group">
                <label>确认主密码</label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="请再次输入主密码"
                  autoComplete="new-password"
                />
              </div>

              <div className="input-group">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    const pwd = PasswordGenerator.generate({ length: 16 });
                    setMasterPassword(pwd);
                    setConfirmPassword(pwd);
                    setStrength(PasswordGenerator.checkStrength(pwd));
                  }}
                >
                  🎲 生成强密码
                </button>
              </div>
            </>
          )}

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>
            {mode === 'create' ? '创建密码库' : '解锁'}
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
          <strong>⚠️ 重要提示：</strong>
          <ul style={{ marginTop: '8px', paddingLeft: '20px' }}>
            <li>主密码是访问您密码库的唯一钥匙</li>
            <li>如果忘记主密码，将无法恢复任何数据</li>
            <li>请务必记住您的主密码</li>
            <li>建议使用至少12位包含大小写字母、数字和符号的强密码</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
