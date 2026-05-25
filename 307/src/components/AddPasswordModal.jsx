import React, { useState, useEffect } from 'react';
import { PasswordGenerator } from '../utils/passwordGenerator.js';

const CATEGORIES = [
  { value: 'general', label: '通用', icon: '🔑' },
  { value: 'social', label: '社交媒体', icon: '🌐' },
  { value: 'work', label: '工作', icon: '💼' },
  { value: 'finance', label: '金融', icon: '💰' },
  { value: 'personal', label: '个人', icon: '👤' },
  { value: 'shopping', label: '购物', icon: '🛒' },
  { value: 'email', label: '邮箱', icon: '📧' },
  { value: 'entertainment', label: '娱乐', icon: '🎮' }
];

export default function AddPasswordModal({ onClose, onSave, initialData = null }) {
  const [formData, setFormData] = useState({
    title: '',
    username: '',
    password: '',
    url: '',
    category: 'general',
    notes: '',
    tags: []
  });
  const [showPassword, setShowPassword] = useState(false);
  const [strength, setStrength] = useState(null);
  const [tagInput, setTagInput] = useState('');
  const [generatorOptions, setGeneratorOptions] = useState({
    length: 16,
    includeUppercase: true,
    includeLowercase: true,
    includeNumbers: true,
    includeSymbols: true,
    excludeAmbiguous: false
  });
  const [showGenerator, setShowGenerator] = useState(false);

  useEffect(() => {
    if (initialData) {
      setFormData(initialData);
      if (initialData.password) {
        setStrength(PasswordGenerator.checkStrength(initialData.password));
      }
    }
  }, [initialData]);

  useEffect(() => {
    if (formData.password) {
      setStrength(PasswordGenerator.checkStrength(formData.password));
    } else {
      setStrength(null);
    }
  }, [formData.password]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.title || !formData.password) {
      alert('请填写标题和密码');
      return;
    }
    onSave(formData);
  };

  const generatePassword = () => {
    const password = PasswordGenerator.generate(generatorOptions);
    setFormData(prev => ({ ...prev, password }));
  };

  const generatePassphrase = () => {
    const password = PasswordGenerator.generatePassphrase(4);
    setFormData(prev => ({ ...prev, password }));
  };

  const addTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, tagInput.trim()]
      }));
      setTagInput('');
    }
  };

  const removeTag = (tagToRemove) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }));
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">
            {initialData ? '编辑密码' : '添加新密码'}
          </h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label>标题 *</label>
            <input
              type="text"
              name="title"
              value={formData.title}
              onChange={handleChange}
              placeholder="例如：GitHub 账户"
              autoFocus
            />
          </div>

          <div className="input-group">
            <label>用户名/邮箱</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder="username@example.com"
            />
          </div>

          <div className="input-group">
            <label>密码 *</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="请输入密码或点击生成"
                style={{ paddingRight: '100px' }}
              />
              <div style={{ 
                position: 'absolute', 
                right: '12px', 
                top: '50%', 
                transform: 'translateY(-50%)',
                display: 'flex',
                gap: '8px'
              }}>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '16px'
                  }}
                >
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowGenerator(!showGenerator)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: '16px'
                  }}
                >
                  🎲
                </button>
              </div>
            </div>

            {strength && (
              <div style={{ marginTop: '8px' }}>
                <div className="strength-bar">
                  <div className={`strength-fill ${PasswordGenerator.getStrengthClass(strength.strength)}`}></div>
                </div>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  fontSize: '12px',
                  marginTop: '4px'
                }}>
                  <span style={{ color: PasswordGenerator.getStrengthColor(strength.strength) }}>
                    强度: {PasswordGenerator.getStrengthLabel(strength.strength)}
                  </span>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    熵值: {strength.entropy} bits
                  </span>
                </div>
                {strength.feedback.length > 0 && (
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    {strength.feedback.map((fb, i) => (
                      <div key={i}>• {fb}</div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {showGenerator && (
            <div className="card" style={{ marginBottom: '20px', background: 'var(--bg-tertiary)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h4 style={{ margin: 0 }}>密码生成器</h4>
                <button 
                  type="button" 
                  className="btn btn-primary btn-small"
                  onClick={generatePassword}
                >
                  生成
                </button>
              </div>

              <div className="input-group">
                <label>密码长度: {generatorOptions.length}</label>
                <input
                  type="range"
                  min="8"
                  max="128"
                  value={generatorOptions.length}
                  onChange={(e) => setGeneratorOptions(prev => ({
                    ...prev,
                    length: parseInt(e.target.value)
                  }))}
                />
              </div>

              <div className="checkbox-group">
                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={generatorOptions.includeUppercase}
                    onChange={(e) => setGeneratorOptions(prev => ({
                      ...prev,
                      includeUppercase: e.target.checked
                    }))}
                  />
                  大写字母 (A-Z)
                </label>
                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={generatorOptions.includeLowercase}
                    onChange={(e) => setGeneratorOptions(prev => ({
                      ...prev,
                      includeLowercase: e.target.checked
                    }))}
                  />
                  小写字母 (a-z)
                </label>
                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={generatorOptions.includeNumbers}
                    onChange={(e) => setGeneratorOptions(prev => ({
                      ...prev,
                      includeNumbers: e.target.checked
                    }))}
                  />
                  数字 (0-9)
                </label>
                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={generatorOptions.includeSymbols}
                    onChange={(e) => setGeneratorOptions(prev => ({
                      ...prev,
                      includeSymbols: e.target.checked
                    }))}
                  />
                  特殊符号 (!@#$...)
                </label>
                <label className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={generatorOptions.excludeAmbiguous}
                    onChange={(e) => setGeneratorOptions(prev => ({
                      ...prev,
                      excludeAmbiguous: e.target.checked
                    }))}
                  />
                  排除易混淆字符
                </label>
              </div>

              <div style={{ marginTop: '16px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={generatePassphrase}
                >
                  📝 生成易记密码短语
                </button>
              </div>
            </div>
          )}

          <div className="input-group">
            <label>网站/应用 URL</label>
            <input
              type="url"
              name="url"
              value={formData.url}
              onChange={handleChange}
              placeholder="https://example.com"
            />
          </div>

          <div className="input-group">
            <label>分类</label>
            <select
              name="category"
              value={formData.category}
              onChange={handleChange}
            >
              {CATEGORIES.map(cat => (
                <option key={cat.value} value={cat.value}>
                  {cat.icon} {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div className="input-group">
            <label>标签</label>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                placeholder="输入标签后按回车"
                style={{ flex: 1 }}
              />
              <button type="button" className="btn btn-secondary btn-small" onClick={addTag}>
                添加
              </button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {formData.tags.map((tag, i) => (
                <span 
                  key={i}
                  style={{
                    background: 'var(--bg-tertiary)',
                    padding: '4px 12px',
                    borderRadius: '20px',
                    fontSize: '12px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => removeTag(tag)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div className="input-group">
            <label>备注</label>
            <textarea
              name="notes"
              value={formData.notes}
              onChange={handleChange}
              placeholder="可选备注信息"
              rows="3"
              style={{ resize: 'vertical' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              取消
            </button>
            <button type="submit" className="btn btn-primary">
              {initialData ? '保存更改' : '添加密码'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
