import React, { useState } from 'react';
import { ShareService } from '../utils/share.js';
import { cryptoService } from '../utils/crypto.js';
import { dbService } from '../utils/database.js';

export default function SettingsScreen({ 
  onExport, 
  onImport, 
  onChangeMasterPassword,
  onDeleteAllData 
}) {
  const [activeTab, setActiveTab] = useState('general');
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showEmergencyKit, setShowEmergencyKit] = useState(false);
  const [emergencyKit, setEmergencyKit] = useState(null);
  const [fileInput, setFileInput] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      onImport(file);
      if (fileInput) {
        fileInput.value = '';
      }
    }
  };

  const handleChangePassword = async () => {
    if (!oldPassword) {
      alert('请输入当前主密码');
      return;
    }
    if (newPassword.length < 8) {
      alert('新密码长度至少8位');
      return;
    }
    if (newPassword !== confirmPassword) {
      alert('两次输入的新密码不一致');
      return;
    }

    try {
      await onChangeMasterPassword(oldPassword, newPassword);
      setShowChangePassword(false);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      console.error('修改主密码失败:', error);
    }
  };

  const handleGenerateEmergencyKit = async () => {
    try {
      const salt = await dbService.getSetting('salt');
      const masterPassword = prompt('请输入当前主密码以生成应急包：');
      
      if (!masterPassword) {
        return;
      }

      const kit = ShareService.createEmergencyKit(masterPassword, salt);
      setEmergencyKit(kit);
      setShowEmergencyKit(true);
    } catch (error) {
      console.error('生成应急包失败:', error);
    }
  };

  const handleDownloadEmergencyKit = () => {
    if (emergencyKit) {
      const blob = new Blob([JSON.stringify(emergencyKit, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `password-manager-emergency-kit-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const tabs = [
    { id: 'general', label: '通用设置', icon: '⚙️' },
    { id: 'security', label: '安全设置', icon: '🔒' },
    { id: 'data', label: '数据管理', icon: '💾' },
    { id: 'about', label: '关于', icon: 'ℹ️' }
  ];

  return (
    <div className="fade-in">
      <div className="tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'general' && (
        <div>
          <div className="card">
            <h3 style={{ marginBottom: '16px' }}>外观</h3>
            <div className="input-group">
              <label>主题模式</label>
              <select defaultValue="dark">
                <option value="dark">深色模式</option>
                <option value="light">浅色模式</option>
                <option value="system">跟随系统</option>
              </select>
            </div>
            <div className="input-group">
              <label className="checkbox-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input type="checkbox" defaultChecked />
                <span>显示密码强度指示器</span>
              </label>
            </div>
            <div className="input-group">
              <label className="checkbox-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input type="checkbox" defaultChecked />
                <span>收藏密码显示在顶部</span>
              </label>
            </div>
          </div>

          <div className="card" style={{ marginTop: '24px' }}>
            <h3 style={{ marginBottom: '16px' }}>浏览器扩展</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              安装浏览器扩展以启用自动填充功能，快速安全地登录您的账户。
            </p>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button className="btn btn-secondary" disabled>
                🌐 Chrome 扩展
              </button>
              <button className="btn btn-secondary" disabled>
                🦊 Firefox 扩展
              </button>
              <button className="btn btn-secondary" disabled>
                🔵 Edge 扩展
              </button>
            </div>
            <div className="alert alert-info" style={{ marginTop: '16px' }}>
              💡 提示：您可以在项目的 extension 目录中找到扩展源代码，自行加载到浏览器中使用。
            </div>
          </div>
        </div>
      )}

      {activeTab === 'security' && (
        <div>
          <div className="card">
            <h3 style={{ marginBottom: '16px' }}>主密码</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              主密码是保护您所有密码的关键。建议使用至少12位包含大小写字母、数字和符号的强密码。
            </p>
            {showChangePassword ? (
              <div style={{ background: 'var(--bg-tertiary)', padding: '20px', borderRadius: '8px' }}>
                <div className="input-group">
                  <label>当前主密码</label>
                  <input
                    type="password"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    placeholder="请输入当前主密码"
                  />
                </div>
                <div className="input-group">
                  <label>新主密码</label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="请输入新主密码"
                  />
                </div>
                <div className="input-group">
                  <label>确认新主密码</label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="请再次输入新主密码"
                  />
                </div>
                <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                  <button
                    className="btn btn-primary"
                    onClick={handleChangePassword}
                  >
                    确认修改
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setShowChangePassword(false)}
                  >
                    取消
                  </button>
                </div>
              </div>
            ) : (
              <button className="btn btn-primary" onClick={() => setShowChangePassword(true)}>
                🔑 修改主密码
              </button>
            )}
          </div>

          <div className="card" style={{ marginTop: '24px' }}>
            <h3 style={{ marginBottom: '16px' }}>应急包</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              生成应急包包含恢复您的密码库所需的关键信息。请将其保存在安全的离线位置。
            </p>
            <button className="btn btn-secondary" onClick={handleGenerateEmergencyKit}>
              🛡️ 生成应急包
            </button>
            <div className="alert alert-warning" style={{ marginTop: '16px' }}>
              <strong>⚠️ 重要提示：</strong>
              <ul style={{ marginTop: '8px', paddingLeft: '20px', fontSize: '13px' }}>
                <li>应急包包含敏感信息，请务必妥善保管</li>
                <li>建议打印并存放在安全的物理位置</li>
                <li>不要将应急包存储在云端或与主密码相同的位置</li>
              </ul>
            </div>
          </div>

          <div className="card" style={{ marginTop: '24px' }}>
            <h3 style={{ marginBottom: '16px' }}>自动锁定</h3>
            <div className="input-group">
              <label>空闲时自动锁定</label>
              <select defaultValue="300000">
                <option value="60000">1分钟</option>
                <option value="300000">5分钟</option>
                <option value="900000">15分钟</option>
                <option value="1800000">30分钟</option>
                <option value="3600000">1小时</option>
                <option value="0">从不</option>
              </select>
            </div>
            <div className="input-group">
              <label className="checkbox-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input type="checkbox" defaultChecked />
                <span>页面隐藏时自动锁定</span>
              </label>
            </div>
            <div className="input-group">
              <label className="checkbox-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input type="checkbox" />
                <span>清除剪贴板内容（复制密码后）</span>
              </label>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'data' && (
        <div>
          <div className="card">
            <h3 style={{ marginBottom: '16px' }}>数据导出</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              导出所有密码数据为未加密的JSON格式。请妥善保管导出的文件。
            </p>
            <button className="btn btn-secondary" onClick={onExport}>
              📤 导出数据
            </button>
            <div className="alert alert-warning" style={{ marginTop: '16px' }}>
              ⚠️ 导出的文件包含未加密的密码信息，请务必妥善保管，不要通过不安全的渠道发送。
            </div>
          </div>

          <div className="card" style={{ marginTop: '24px' }}>
            <h3 style={{ marginBottom: '16px' }}>数据导入</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              从JSON文件导入密码数据。支持导入本应用导出的文件或其他密码管理器导出的数据。
            </p>
            <input
              ref={el => setFileInput(el)}
              type="file"
              accept=".json"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
            <button 
              className="btn btn-secondary" 
              onClick={() => fileInput?.click()}
            >
              📥 导入数据
            </button>
            <div className="alert alert-info" style={{ marginTop: '16px' }}>
              💡 支持导入 Chrome、Firefox、Bitwarden、1Password 等主流密码管理器导出的JSON格式。
            </div>
          </div>

          <div className="card" style={{ marginTop: '24px' }}>
            <h3 style={{ marginBottom: '16px', color: 'var(--danger)' }}>危险区域</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              以下操作将永久删除您的所有数据，请谨慎操作。
            </p>
            <button 
              className="btn btn-danger" 
              onClick={onDeleteAllData}
            >
              🗑️ 删除所有数据
            </button>
            <div className="alert alert-error" style={{ marginTop: '16px' }}>
              <strong>⚠️ 警告：</strong>此操作将永久删除所有密码和设置，且无法恢复。请确保已备份重要数据。
            </div>
          </div>
        </div>
      )}

      {activeTab === 'about' && (
        <div>
          <div className="card">
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ fontSize: '64px', marginBottom: '16px' }}>🔐</div>
              <h2 style={{ marginBottom: '8px' }}>安全密码管理器</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
                版本 1.0.0
              </p>
            </div>

            <div style={{ 
              background: 'var(--bg-tertiary)', 
              padding: '20px', 
              borderRadius: '8px',
              marginBottom: '20px'
            }}>
              <h4 style={{ marginBottom: '12px' }}>功能特性</h4>
              <ul style={{ paddingLeft: '20px', lineHeight: '2' }}>
                <li>🔑 安全的密码生成器</li>
                <li>🔒 端到端加密存储</li>
                <li>📊 密码强度检测</li>
                <li>🔍 安全审计功能</li>
                <li>📤 安全密码共享</li>
                <li>🔄 多设备同步</li>
                <li>🌐 浏览器自动填充</li>
                <li>💾 数据导入导出</li>
              </ul>
            </div>

            <div style={{ 
              background: 'var(--bg-tertiary)', 
              padding: '20px', 
              borderRadius: '8px',
              marginBottom: '20px'
            }}>
              <h4 style={{ marginBottom: '12px' }}>技术栈</h4>
              <ul style={{ paddingLeft: '20px', lineHeight: '2' }}>
                <li>⚛️ React 18 - 用户界面</li>
                <li>🗄️ IndexedDB - 本地数据存储</li>
                <li>🔐 WebCrypto API - 加密解密</li>
                <li>🧩 浏览器扩展 API - 自动填充</li>
                <li>⚡ Vite - 构建工具</li>
              </ul>
            </div>

            <div style={{ 
              background: 'var(--bg-tertiary)', 
              padding: '20px', 
              borderRadius: '8px'
            }}>
              <h4 style={{ marginBottom: '12px' }}>隐私与安全</h4>
              <p style={{ lineHeight: '1.8', color: 'var(--text-secondary)' }}>
                您的数据安全是我们的首要任务。所有密码在存储前都使用 AES-256-GCM 加密，
                只有您的主密码才能解密。我们不会收集、存储或传输您的任何密码数据。
                端到端加密确保即使在同步时，也只有您可以访问您的数据。
              </p>
            </div>

            <div style={{ 
              textAlign: 'center', 
              marginTop: '24px', 
              paddingTop: '20px', 
              borderTop: '1px solid var(--border)' 
            }}>
              <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                © 2024 安全密码管理器. 开源软件，基于 MIT 许可证发布。
              </p>
            </div>
          </div>
        </div>
      )}

      {showEmergencyKit && emergencyKit && (
        <div className="modal-overlay" onClick={() => setShowEmergencyKit(false)}>
          <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">🛡️ 应急包</h2>
              <button className="close-btn" onClick={() => setShowEmergencyKit(false)}>×</button>
            </div>

            <div className="alert alert-warning" style={{ marginBottom: '20px' }}>
              <strong>⚠️ 请务必阅读以下说明：</strong>
              <ul style={{ marginTop: '8px', paddingLeft: '20px', fontSize: '13px' }}>
                <li>应急包包含恢复密码库的关键信息</li>
                <li>请立即下载并存储在安全的离线位置</li>
                <li>不要将此文件存储在云端或发送给他人</li>
                <li>建议打印纸质版作为备份</li>
              </ul>
            </div>

            <div className="card" style={{ background: 'var(--bg-primary)', marginBottom: '20px' }}>
              <div className="input-group">
                <label>恢复代码</label>
                <div className="password-display">
                  <span style={{ flex: 1, fontFamily: 'monospace', fontSize: '14px', letterSpacing: '2px' }}>
                    {emergencyKit.recoveryCode}
                  </span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-small"
                    onClick={() => navigator.clipboard.writeText(emergencyKit.recoveryCode)}
                  >
                    📋 复制
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2" style={{ marginTop: '16px' }}>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    主密码提示
                  </div>
                  <div style={{ fontFamily: 'monospace' }}>{emergencyKit.hint}</div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    创建时间
                  </div>
                  <div>{new Date(emergencyKit.createdAt).toLocaleString('zh-CN')}</div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ flex: 1 }}
                onClick={() => setShowEmergencyKit(false)}
              >
                关闭
              </button>
              <button
                type="button"
                className="btn btn-primary"
                style={{ flex: 1 }}
                onClick={handleDownloadEmergencyKit}
              >
                📥 下载应急包
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
