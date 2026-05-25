import React, { useState, useEffect } from 'react';

const SYNC_INTERVAL_OPTIONS = [
  { value: 60 * 1000, label: '1分钟' },
  { value: 5 * 60 * 1000, label: '5分钟' },
  { value: 15 * 60 * 1000, label: '15分钟' },
  { value: 30 * 60 * 1000, label: '30分钟' },
  { value: 60 * 60 * 1000, label: '1小时' }
];

export default function SyncSettings({ syncService, showNotification }) {
  const [syncStatus, setSyncStatus] = useState(null);
  const [syncSettings, setSyncSettings] = useState(null);
  const [syncKey, setSyncKey] = useState(null);
  const [importKey, setImportKey] = useState('');
  const [showSyncKey, setShowSyncKey] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadStatus();
    
    const unsubscribe = syncService.addSyncListener((status) => {
      setSyncStatus(status);
    });

    return unsubscribe;
  }, [syncService]);

  const loadStatus = async () => {
    try {
      const status = await syncService.getSyncStatus();
      setSyncStatus(status);

      const settings = await syncService.getSyncSettings();
      setSyncSettings(settings);

      if (status.hasSyncKey) {
        const key = await syncService.exportSyncKey();
        setSyncKey(key);
      }
    } catch (error) {
      console.error('加载同步状态失败:', error);
    }
  };

  const handleGenerateKey = async () => {
    try {
      await syncService.generateSyncKey();
      await loadStatus();
      showNotification('同步密钥已生成', 'success');
    } catch (error) {
      showNotification('生成密钥失败: ' + error.message, 'error');
    }
  };

  const handleImportKey = async () => {
    try {
      await syncService.importSyncKey(importKey.trim());
      setShowImportModal(false);
      setImportKey('');
      await loadStatus();
      showNotification('同步密钥已导入', 'success');
    } catch (error) {
      showNotification('导入失败: ' + error.message, 'error');
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      await syncService.sync();
      await loadStatus();
      showNotification('同步完成', 'success');
    } catch (error) {
      showNotification('同步失败: ' + error.message, 'error');
    } finally {
      setSyncing(false);
    }
  };

  const handleSettingChange = async (key, value) => {
    try {
      const newSettings = { ...syncSettings, [key]: value };
      await syncService.updateSyncSettings(newSettings);
      setSyncSettings(newSettings);
      showNotification('设置已更新', 'success');
    } catch (error) {
      showNotification('更新设置失败: ' + error.message, 'error');
    }
  };

  const handleResetSync = async () => {
    if (confirm('确定要重置同步吗？这将删除本地同步配置，但不会影响您的密码数据。')) {
      try {
        await syncService.resetSync();
        setSyncKey(null);
        await loadStatus();
        showNotification('同步已重置', 'success');
      } catch (error) {
        showNotification('重置失败: ' + error.message, 'error');
      }
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
    if (!timestamp) return '从未同步';
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'synced': return '✅';
      case 'syncing': return '🔄';
      case 'error': return '❌';
      default: return '⏸️';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'synced': return '已同步';
      case 'syncing': return '同步中...';
      case 'error': return '同步错误';
      default: return '未同步';
    }
  };

  return (
    <div className="fade-in">
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '20px'
        }}>
          <div>
            <h2 style={{ marginBottom: '8px' }}>多设备同步</h2>
            <p style={{ color: 'var(--text-secondary)' }}>
              使用端到端加密在多个设备之间同步您的密码数据
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '24px' }}>{getStatusIcon(syncStatus?.status)}</span>
            <span>{getStatusLabel(syncStatus?.status)}</span>
          </div>
        </div>

        <div className="grid grid-cols-2" style={{ marginBottom: '20px' }}>
          <div className="card" style={{ background: 'var(--bg-primary)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              上次同步
            </div>
            <div style={{ fontSize: '14px' }}>{formatDate(syncStatus?.lastSyncTime)}</div>
          </div>
          <div className="card" style={{ background: 'var(--bg-primary)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
              自动同步
            </div>
            <div style={{ fontSize: '14px' }}>
              {syncStatus?.autoSyncEnabled ? '已启用' : '已禁用'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            className="btn btn-primary"
            onClick={handleSync}
            disabled={syncing || !syncStatus?.hasSyncKey}
          >
            {syncing ? <span className="loading"></span> : '🔄 立即同步'}
          </button>
          {syncStatus?.hasSyncKey && (
            <button
              className="btn btn-secondary"
              onClick={handleResetSync}
            >
              重置同步
            </button>
          )}
        </div>
      </div>

      {!syncStatus?.hasSyncKey ? (
        <div className="card">
          <h3 style={{ marginBottom: '16px' }}>设置同步密钥</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
            同步密钥用于端到端加密您的数据。请在所有设备上使用相同的同步密钥。
            <strong> 请务必妥善保管您的同步密钥，丢失将无法恢复同步数据。</strong>
          </p>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={handleGenerateKey}>
              🔑 生成新密钥
            </button>
            <button className="btn btn-secondary" onClick={() => setShowImportModal(true)}>
              📥 导入已有密钥
            </button>
          </div>

          <div className="alert alert-warning" style={{ marginTop: '20px' }}>
            <strong>⚠️ 重要提示：</strong>
            <ul style={{ marginTop: '8px', paddingLeft: '20px', fontSize: '13px' }}>
              <li>同步密钥是端到端加密的关键，我们无法访问或恢复您的密钥</li>
              <li>请将同步密钥保存在安全的地方，如密码管理器或离线存储</li>
              <li>所有需要同步的设备必须使用相同的同步密钥</li>
              <li>生成新密钥后，请立即导出并备份</li>
            </ul>
          </div>
        </div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3>同步密钥</h3>
              <span style={{ 
                padding: '4px 12px', 
                borderRadius: '20px', 
                background: 'var(--success-bg)', 
                color: 'var(--success)',
                fontSize: '12px'
              }}>
                ✅ 已配置
              </span>
            </div>

            <div className="input-group">
              <label>您的同步密钥</label>
              <div className="password-display">
                <span 
                  style={{ flex: 1, fontFamily: 'monospace', fontSize: '13px' }}
                  className={showSyncKey ? '' : 'password-masked'}
                >
                  {showSyncKey ? syncKey : '•'.repeat(Math.min(syncKey?.length || 64, 40))}
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-small"
                  onClick={() => setShowSyncKey(!showSyncKey)}
                >
                  {showSyncKey ? '🙈' : '👁️'}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-small"
                  onClick={() => copyToClipboard(syncKey)}
                >
                  {copied ? '✓ 已复制' : '📋 复制'}
                </button>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                请将此密钥复制到其他设备以启用同步
              </p>
            </div>
          </div>

          <div className="card" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '16px' }}>同步设置</h3>

            <div className="input-group">
              <label className="checkbox-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  checked={syncSettings?.autoSync || false}
                  onChange={(e) => handleSettingChange('autoSync', e.target.checked)}
                />
                <span>启用自动同步</span>
              </label>
            </div>

            {syncSettings?.autoSync && (
              <div className="input-group">
                <label>同步间隔</label>
                <select
                  value={syncSettings?.syncInterval || 300000}
                  onChange={(e) => handleSettingChange('syncInterval', Number(e.target.value))}
                >
                  {SYNC_INTERVAL_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="input-group">
              <label className="checkbox-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  checked={syncSettings?.syncOnStart || false}
                  onChange={(e) => handleSettingChange('syncOnStart', e.target.checked)}
                />
                <span>启动时自动同步</span>
              </label>
            </div>

            <div className="input-group">
              <label className="checkbox-item" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  checked={syncSettings?.syncOnChange !== false}
                  onChange={(e) => handleSettingChange('syncOnChange', e.target.checked)}
                />
                <span>数据变更时自动同步</span>
              </label>
            </div>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: '16px' }}>添加新设备</h3>
            <div style={{ 
              background: 'var(--bg-tertiary)', 
              padding: '20px', 
              borderRadius: '8px',
              marginBottom: '16px'
            }}>
              <h4 style={{ marginBottom: '12px' }}>操作步骤：</h4>
              <ol style={{ paddingLeft: '20px', lineHeight: '2' }}>
                <li>在新设备上安装并打开密码管理器</li>
                <li>点击"导入已有密钥"按钮</li>
                <li>输入或粘贴上方显示的同步密钥</li>
                <li>点击同步按钮开始数据同步</li>
              </ol>
            </div>
            <div className="alert alert-info">
              💡 提示：您也可以通过扫描二维码的方式快速配置同步（需浏览器支持摄像头）
            </div>
          </div>
        </>
      )}

      {showImportModal && (
        <div className="modal-overlay" onClick={() => setShowImportModal(false)}>
          <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">📥 导入同步密钥</h2>
              <button className="close-btn" onClick={() => setShowImportModal(false)}>×</button>
            </div>

            <div className="input-group">
              <label>请输入您的同步密钥</label>
              <textarea
                value={importKey}
                onChange={(e) => setImportKey(e.target.value)}
                placeholder="粘贴您的同步密钥..."
                rows={4}
                style={{ fontFamily: 'monospace', fontSize: '13px' }}
              />
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                密钥应是一个长字符串，由另一台设备导出获得
              </p>
            </div>

            <div className="alert alert-warning" style={{ marginTop: '16px' }}>
              ⚠️ 请确保密钥的完整性，任何字符的缺失或错误都会导致导入失败
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowImportModal(false)}
              >
                取消
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleImportKey}
                disabled={!importKey.trim()}
              >
                导入
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
