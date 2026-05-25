import React, { useState, useEffect } from 'react';
import { PasswordGenerator } from '../utils/passwordGenerator.js';

export default function PasswordGeneratorModal({ onClose, onUsePassword }) {
  const [options, setOptions] = useState({
    length: 16,
    includeUppercase: true,
    includeLowercase: true,
    includeNumbers: true,
    includeSymbols: true,
    excludeAmbiguous: false
  });
  const [password, setPassword] = useState('');
  const [strength, setStrength] = useState(null);
  const [showPassword, setShowPassword] = useState(true);
  const [copied, setCopied] = useState(false);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    generate();
  }, []);

  useEffect(() => {
    if (password) {
      setStrength(PasswordGenerator.checkStrength(password));
    }
  }, [password]);

  const generate = () => {
    const newPassword = PasswordGenerator.generate(options);
    setPassword(newPassword);
    setHistory(prev => [newPassword, ...prev].slice(0, 10));
  };

  const generatePassphrase = () => {
    const newPassword = PasswordGenerator.generatePassphrase(4);
    setPassword(newPassword);
    setHistory(prev => [newPassword, ...prev].slice(0, 10));
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('复制失败:', error);
    }
  };

  const handleOptionChange = (key, value) => {
    setOptions(prev => ({ ...prev, [key]: value }));
  };

  const usePassword = () => {
    if (onUsePassword) {
      onUsePassword(password);
    } else {
      copyToClipboard();
      onClose();
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">🎲 密码生成器</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="password-display" style={{ marginBottom: '20px' }}>
          <span 
            style={{ flex: 1, fontFamily: 'monospace', fontSize: '18px', letterSpacing: '2px' }}
            className={showPassword ? '' : 'password-masked'}
          >
            {showPassword ? password : '•'.repeat(password.length)}
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
            onClick={copyToClipboard}
          >
            {copied ? '✓ 已复制' : '📋'}
          </button>
        </div>

        {strength && (
          <div style={{ marginBottom: '20px' }}>
            <div className="strength-bar">
              <div className={`strength-fill ${PasswordGenerator.getStrengthClass(strength.strength)}`}></div>
            </div>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              fontSize: '14px',
              marginTop: '8px'
            }}>
              <span style={{ color: PasswordGenerator.getStrengthColor(strength.strength), fontWeight: '500' }}>
                强度: {PasswordGenerator.getStrengthLabel(strength.strength)}
              </span>
              <span style={{ color: 'var(--text-secondary)' }}>
                熵值: {strength.entropy} bits
              </span>
              <span style={{ color: 'var(--text-secondary)' }}>
                评分: {strength.score}/6
              </span>
            </div>
            {strength.feedback.length > 0 && (
              <div style={{ 
                marginTop: '12px', 
                padding: '12px', 
                background: 'var(--bg-tertiary)',
                borderRadius: '8px',
                fontSize: '13px'
              }}>
                {strength.feedback.map((fb, i) => (
                  <div key={i} style={{ marginBottom: '4px' }}>• {fb}</div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="card" style={{ marginBottom: '20px', background: 'var(--bg-tertiary)' }}>
          <h4 style={{ marginBottom: '16px' }}>生成选项</h4>
          
          <div className="input-group">
            <label>密码长度: {options.length}</label>
            <input
              type="range"
              min="8"
              max="128"
              value={options.length}
              onChange={(e) => handleOptionChange('length', parseInt(e.target.value))}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              <span>8</span>
              <span>128</span>
            </div>
          </div>

          <div className="checkbox-group">
            <label className="checkbox-item">
              <input
                type="checkbox"
                checked={options.includeUppercase}
                onChange={(e) => handleOptionChange('includeUppercase', e.target.checked)}
              />
              大写字母 (A-Z)
            </label>
            <label className="checkbox-item">
              <input
                type="checkbox"
                checked={options.includeLowercase}
                onChange={(e) => handleOptionChange('includeLowercase', e.target.checked)}
              />
              小写字母 (a-z)
            </label>
            <label className="checkbox-item">
              <input
                type="checkbox"
                checked={options.includeNumbers}
                onChange={(e) => handleOptionChange('includeNumbers', e.target.checked)}
              />
              数字 (0-9)
            </label>
            <label className="checkbox-item">
              <input
                type="checkbox"
                checked={options.includeSymbols}
                onChange={(e) => handleOptionChange('includeSymbols', e.target.checked)}
              />
              特殊符号 (!@#$...)
            </label>
            <label className="checkbox-item">
              <input
                type="checkbox"
                checked={options.excludeAmbiguous}
                onChange={(e) => handleOptionChange('excludeAmbiguous', e.target.checked)}
              />
              排除易混淆字符 (i, l, I, O, 0, 1)
            </label>
          </div>
        </div>

        {history.length > 1 && (
          <div className="input-group">
            <label>生成历史（最近10个）</label>
            <div style={{ 
              background: 'var(--bg-tertiary)', 
              padding: '12px', 
              borderRadius: '8px',
              maxHeight: '150px',
              overflowY: 'auto'
            }}>
              {history.slice(1).map((pwd, i) => (
                <div 
                  key={i}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 0',
                    borderBottom: i < history.length - 2 ? '1px solid var(--border)' : 'none',
                    fontFamily: 'monospace',
                    fontSize: '13px'
                  }}
                >
                  <span className="password-masked">{'•'.repeat(Math.min(pwd.length, 20))}</span>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-small"
                      onClick={() => navigator.clipboard.writeText(pwd)}
                    >
                      📋
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-small"
                      onClick={() => setPassword(pwd)}
                    >
                      ↩️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button 
            type="button" 
            className="btn btn-secondary" 
            onClick={generatePassphrase}
            style={{ flex: 1 }}
          >
            📝 密码短语
          </button>
          <button 
            type="button" 
            className="btn btn-primary" 
            onClick={generate}
            style={{ flex: 1 }}
          >
            🔄 重新生成
          </button>
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
          <button 
            type="button" 
            className="btn btn-secondary" 
            onClick={onClose}
            style={{ flex: 1 }}
          >
            关闭
          </button>
          <button 
            type="button" 
            className="btn btn-success" 
            onClick={usePassword}
            style={{ flex: 1 }}
          >
            {onUsePassword ? '✓ 使用此密码' : '📋 复制并关闭'}
          </button>
        </div>
      </div>
    </div>
  );
}
