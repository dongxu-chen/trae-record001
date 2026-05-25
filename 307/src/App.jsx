import React, { useState, useEffect, useCallback } from 'react';
import { dbService } from './utils/database.js';
import { cryptoService } from './utils/crypto.js';
import { syncService } from './utils/sync.js';
import { ShareService } from './utils/share.js';
import { AuditService } from './utils/audit.js';
import { PasswordGenerator } from './utils/passwordGenerator.js';
import { EmergencyAccessService } from './utils/emergency.js';

import LoginScreen from './components/LoginScreen.jsx';
import PasswordList from './components/PasswordList.jsx';
import AddPasswordModal from './components/AddPasswordModal.jsx';
import ViewPasswordModal from './components/ViewPasswordModal.jsx';
import PasswordGeneratorModal from './components/PasswordGeneratorModal.jsx';
import AuditScreen from './components/AuditScreen.jsx';
import ShareModal from './components/ShareModal.jsx';
import SyncSettings from './components/SyncSettings.jsx';
import SettingsScreen from './components/SettingsScreen.jsx';
import ShareReceiveScreen from './components/ShareReceiveScreen.jsx';
import BreachDetectionModal from './components/BreachDetectionModal.jsx';
import EmergencyAccessSettings from './components/EmergencyAccessSettings.jsx';
import HealthReportScreen from './components/HealthReportScreen.jsx';

export default function App() {
  const [isInitialized, setIsInitialized] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [activeTab, setActiveTab] = useState('passwords');
  const [passwords, setPasswords] = useState([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(null);
  const [showGeneratorModal, setShowGeneratorModal] = useState(false);
  const [showShareModal, setShowShareModal] = useState(null);
  const [showBreachModal, setShowBreachModal] = useState(false);
  const [breachCheckPasswordId, setBreachCheckPasswordId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [notification, setNotification] = useState(null);
  const [stats, setStats] = useState(null);
  const [auditData, setAuditData] = useState(null);

  useEffect(() => {
    initApp();
  }, []);

  const initApp = async () => {
    try {
      await dbService.init();
      await syncService.init();
      setIsInitialized(true);

      dbService.addListener(() => {
        loadPasswords();
        loadStats();
      });

      const hash = window.location.hash;
      if (hash.startsWith('#/share/')) {
        return;
      }

      const hasVault = await dbService.getSetting('salt');
      if (hasVault && cryptoService.isInitialized()) {
        setIsUnlocked(true);
        loadPasswords();
        loadStats();
      }
    } catch (error) {
      console.error('初始化失败:', error);
    }
  };

  const loadPasswords = useCallback(async () => {
    try {
      const allPasswords = await dbService.getAllPasswords(false);
      let filtered = allPasswords;
      
      if (searchQuery) {
        const lowerQuery = searchQuery.toLowerCase();
        filtered = allPasswords.filter(p => 
          p.title.toLowerCase().includes(lowerQuery) ||
          p.username.toLowerCase().includes(lowerQuery) ||
          p.url.toLowerCase().includes(lowerQuery)
        );
      }

      setPasswords(filtered.sort((a, b) => b.updatedAt - a.updatedAt));
    } catch (error) {
      console.error('加载密码失败:', error);
    }
  }, [searchQuery]);

  const loadStats = useCallback(async () => {
    try {
      const statsData = await dbService.getStats();
      setStats(statsData);
    } catch (error) {
      console.error('加载统计失败:', error);
    }
  }, []);

  const handleCreateVault = async (masterPassword) => {
    try {
      const { salt } = await cryptoService.init(masterPassword);
      await dbService.setSetting('salt', salt);
      
      const hash = await cryptoService.hashPassword(masterPassword);
      await dbService.setSetting('masterPasswordHash', hash);
      
      setIsUnlocked(true);
      loadPasswords();
      loadStats();
      showNotification('密码库创建成功！', 'success');
    } catch (error) {
      showNotification('创建失败: ' + error.message, 'error');
    }
  };

  const handleUnlock = async (masterPassword) => {
    try {
      const salt = await dbService.getSetting('salt');
      if (!salt) {
        throw new Error('未找到密码库，请先创建');
      }

      await cryptoService.init(masterPassword, salt);
      setIsUnlocked(true);
      loadPasswords();
      loadStats();
      showNotification('解锁成功！', 'success');
    } catch (error) {
      showNotification('解锁失败: ' + error.message, 'error');
    }
  };

  const handleLock = () => {
    cryptoService.clearKeys();
    setIsUnlocked(false);
    setPasswords([]);
    setStats(null);
    showNotification('已锁定', 'success');
  };

  const handleAddPassword = async (passwordData) => {
    try {
      await dbService.addPassword(passwordData);
      setShowAddModal(false);
      showNotification('密码添加成功！', 'success');
    } catch (error) {
      showNotification('添加失败: ' + error.message, 'error');
    }
  };

  const handleUpdatePassword = async (id, passwordData) => {
    try {
      await dbService.updatePassword(id, passwordData);
      setShowViewModal(null);
      showNotification('密码更新成功！', 'success');
    } catch (error) {
      showNotification('更新失败: ' + error.message, 'error');
    }
  };

  const handleDeletePassword = async (id) => {
    if (confirm('确定要删除这个密码吗？此操作不可恢复。')) {
      try {
        await dbService.deletePassword(id);
        setShowViewModal(null);
        showNotification('密码已删除', 'success');
      } catch (error) {
        showNotification('删除失败: ' + error.message, 'error');
      }
    }
  };

  const handleCopyPassword = async (id) => {
    try {
      const decrypted = await dbService.getDecryptedPassword(id);
      await navigator.clipboard.writeText(decrypted.password);
      await dbService.markAsUsed(id);
      showNotification('密码已复制到剪贴板', 'success');
    } catch (error) {
      showNotification('复制失败: ' + error.message, 'error');
    }
  };

  const handleCopyUsername = async (username) => {
    try {
      await navigator.clipboard.writeText(username);
      showNotification('用户名已复制到剪贴板', 'success');
    } catch (error) {
      showNotification('复制失败: ' + error.message, 'error');
    }
  };

  const handleToggleFavorite = async (id) => {
    try {
      await dbService.toggleFavorite(id);
      showNotification('收藏状态已更新', 'success');
    } catch (error) {
      showNotification('操作失败: ' + error.message, 'error');
    }
  };

  const handleShare = async (passwordId, options) => {
    try {
      const result = await ShareService.createShareLink(passwordId, options);
      showNotification('分享链接已生成', 'success');
      return result;
    } catch (error) {
      showNotification('分享失败: ' + error.message, 'error');
      throw error;
    }
  };

  const handleExportData = async () => {
    try {
      const data = await dbService.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `passwords-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showNotification('数据导出成功', 'success');
    } catch (error) {
      showNotification('导出失败: ' + error.message, 'error');
    }
  };

  const handleImportData = async (file) => {
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      const count = await dbService.importData(data);
      showNotification(`成功导入 ${count} 条密码记录`, 'success');
    } catch (error) {
      showNotification('导入失败: ' + error.message, 'error');
    }
  };

  const handleRunAudit = async () => {
    try {
      const audit = await AuditService.runFullAudit();
      setAuditData(audit);
      showNotification('安全审计完成', 'success');
    } catch (error) {
      showNotification('审计失败: ' + error.message, 'error');
    }
  };

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const hash = window.location.hash;
  if (hash.startsWith('#/share/')) {
    const token = hash.replace('#/share/', '');
    return (
      <div className="app-container">
        <ShareReceiveScreen token={token} showNotification={showNotification} />
      </div>
    );
  }

  if (!isInitialized) {
    return (
      <div className="app-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <div className="loading"></div>
      </div>
    );
  }

  if (!isUnlocked) {
    return (
      <LoginScreen
        onCreateVault={handleCreateVault}
        onUnlock={handleUnlock}
        hasVault={!!dbService.getSetting && dbService.getSetting('salt')}
      />
    );
  }

  return (
    <div className="app-container">
      {notification && (
        <div className={`alert alert-${notification.type}`} style={{ position: 'fixed', top: 20, right: 20, zIndex: 9999 }}>
          {notification.message}
        </div>
      )}

      <header className="header">
        <div className="logo">
          🔐 安全密码管理器
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button className="btn btn-secondary btn-small" onClick={() => setShowBreachModal(true)}>
            🔍 泄露检测
          </button>
          <button className="btn btn-secondary btn-small" onClick={() => setShowGeneratorModal(true)}>
            生成密码
          </button>
          <button className="btn btn-secondary btn-small" onClick={() => setActiveTab('settings')}>
            设置
          </button>
          <button className="btn btn-danger btn-small" onClick={handleLock}>
            锁定
          </button>
        </div>
      </header>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'passwords' ? 'active' : ''}`}
          onClick={() => setActiveTab('passwords')}
        >
          密码列表
        </button>
        <button 
          className={`tab ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => { setActiveTab('audit'); handleRunAudit(); }}
        >
          安全审计
        </button>
        <button 
          className={`tab ${activeTab === 'health' ? 'active' : ''}`}
          onClick={() => setActiveTab('health')}
        >
          健康报告
        </button>
        <button 
          className={`tab ${activeTab === 'emergency' ? 'active' : ''}`}
          onClick={() => setActiveTab('emergency')}
        >
          紧急访问
        </button>
        <button 
          className={`tab ${activeTab === 'sync' ? 'active' : ''}`}
          onClick={() => setActiveTab('sync')}
        >
          同步设置
        </button>
      </div>

      {activeTab === 'passwords' && (
        <PasswordList
          passwords={passwords}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onAdd={() => setShowAddModal(true)}
          onView={setShowViewModal}
          onCopy={handleCopyPassword}
          onCopyUsername={handleCopyUsername}
          onToggleFavorite={handleToggleFavorite}
          onShare={setShowShareModal}
          stats={stats}
        />
      )}

      {activeTab === 'audit' && (
        <AuditScreen
          auditData={auditData}
          onRunAudit={handleRunAudit}
          onViewPassword={setShowViewModal}
          onCheckBreach={(passwordId) => {
            setBreachCheckPasswordId(passwordId);
            setShowBreachModal(true);
          }}
        />
      )}

      {activeTab === 'health' && (
        <HealthReportScreen
          showNotification={showNotification}
        />
      )}

      {activeTab === 'emergency' && (
        <EmergencyAccessSettings
          showNotification={showNotification}
        />
      )}

      {activeTab === 'sync' && (
        <SyncSettings
          syncService={syncService}
          showNotification={showNotification}
        />
      )}

      {activeTab === 'settings' && (
        <SettingsScreen
          onExport={handleExportData}
          onImport={handleImportData}
          onChangeMasterPassword={async (oldPassword, newPassword) => {
            try {
              const salt = await dbService.getSetting('salt');
              await cryptoService.init(oldPassword, salt);
              
              const allPasswords = await dbService.getAllPasswords(true);
              
              const { salt: newSalt } = await cryptoService.init(newPassword);
              await dbService.setSetting('salt', newSalt);
              
              const newHash = await cryptoService.hashPassword(newPassword);
              await dbService.setSetting('masterPasswordHash', newHash);
              
              for (const pwd of allPasswords) {
                if (pwd.password) {
                  await dbService.updatePassword(pwd.id, { password: pwd.password, notes: pwd.notes });
                }
              }
              
              showNotification('主密码修改成功', 'success');
            } catch (error) {
              showNotification('修改失败: ' + error.message, 'error');
            }
          }}
          onDeleteAllData={async () => {
            if (confirm('确定要删除所有数据吗？此操作不可恢复！')) {
              await dbService.deleteDatabase();
              cryptoService.clearKeys();
              setIsUnlocked(false);
              showNotification('所有数据已删除', 'success');
            }
          }}
        />
      )}

      {showAddModal && (
        <AddPasswordModal
          onClose={() => setShowAddModal(false)}
          onSave={handleAddPassword}
        />
      )}

      {showViewModal && (
        <ViewPasswordModal
          passwordId={showViewModal}
          onClose={() => setShowViewModal(null)}
          onUpdate={handleUpdatePassword}
          onDelete={handleDeletePassword}
          onCopy={handleCopyPassword}
          onCopyUsername={handleCopyUsername}
          onShare={setShowShareModal}
        />
      )}

      {showGeneratorModal && (
        <PasswordGeneratorModal
          onClose={() => setShowGeneratorModal(false)}
          onUsePassword={(password) => {
            setShowGeneratorModal(false);
            setShowAddModal(true);
          }}
        />
      )}

      {showShareModal && (
        <ShareModal
          passwordId={showShareModal}
          onClose={() => setShowShareModal(null)}
          onShare={handleShare}
        />
      )}

      {showBreachModal && (
        <BreachDetectionModal
          passwordId={breachCheckPasswordId}
          onClose={() => {
            setShowBreachModal(false);
            setBreachCheckPasswordId(null);
          }}
          onViewPassword={(id) => {
            setShowBreachModal(false);
            setBreachCheckPasswordId(null);
            setShowViewModal(id);
          }}
        />
      )}
    </div>
  );
}
