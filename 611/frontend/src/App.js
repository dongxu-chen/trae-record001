import React, { useState, useEffect } from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Resources from './pages/Resources';
import Rules from './pages/Rules';
import Compliance from './pages/Compliance';
import ResourceDetail from './pages/ResourceDetail';
import CostAllocation from './pages/CostAllocation';
import AuditLogs from './pages/AuditLogs';
import TagTemplates from './pages/TagTemplates';
import { api } from './services/api';

function App() {
  const [health, setHealth] = useState('checking');
  const [session, setSession] = useState(null);
  const [showAccountSwitcher, setShowAccountSwitcher] = useState(false);
  const [availableAccounts, setAvailableAccounts] = useState([
    { id: 'account-prod-001', name: '生产账号' },
    { id: 'account-dev-001', name: '开发账号' },
  ]);
  const [availableRoles, setAvailableRoles] = useState([
    { id: 'role-admin', name: '管理员', description: '完整权限' },
    { id: 'role-prod-viewer', name: '生产环境查看者', description: '只读权限' },
    { id: 'role-dev-admin', name: '开发环境管理员', description: '开发环境完整权限' },
  ]);
  const [isSwitching, setIsSwitching] = useState(false);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.get('/health');
        setHealth('ok');
      } catch (error) {
        setHealth('error');
      }
    };
    checkHealth();

    const mockSession = {
      sessionId: 'sess-mock-' + Date.now(),
      token: 'mock-token-xxx',
      role: { id: 'role-admin', name: '管理员' },
      account: { id: 'account-prod-001', name: '生产账号' },
      expiresAt: new Date(Date.now() + 86400000).toISOString(),
      trustPath: [],
    };
    setSession(mockSession);
  }, []);

  const handleSeamlessSwitch = async (targetAccountId) => {
    setIsSwitching(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 800));

      const accountNames = {
        'account-prod-001': '生产账号',
        'account-dev-001': '开发账号',
      };

      let trustPath = [];
      if (session.account.id !== targetAccountId) {
        trustPath = [
          { from: session.account.name, to: accountNames[targetAccountId], via: 'chain-dev-to-prod' },
        ];
      }

      setSession({
        ...session,
        account: { id: targetAccountId, name: accountNames[targetAccountId] },
        trustPath: trustPath,
        sessionId: 'sess-mock-' + Date.now(),
      });
      setShowAccountSwitcher(false);
    } finally {
      setIsSwitching(false);
    }
  };

  const handleRoleSwitch = async (roleId) => {
    setIsSwitching(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 500));

      const roleNames = {
        'role-admin': '管理员',
        'role-prod-viewer': '生产环境查看者',
        'role-dev-admin': '开发环境管理员',
      };

      setSession({
        ...session,
        role: { id: roleId, name: roleNames[roleId] },
        sessionId: 'sess-mock-' + Date.now(),
      });
      setShowAccountSwitcher(false);
    } finally {
      setIsSwitching(false);
    }
  };

  return (
    <div className="app-container">
      <nav className="navbar">
        <div className="navbar-brand">
          <span>🏷️</span>
          <span>云资源标签合规性检查</span>
          {health === 'ok' && <span className="badge badge-compliant" style={{fontSize: '0.7rem'}}>后端正常</span>}
          {health === 'error' && <span className="badge badge-noncompliant" style={{fontSize: '0.7rem'}}>后端异常</span>}
        </div>
        <ul className="navbar-nav">
          <li><NavLink to="/" end>仪表盘</NavLink></li>
          <li><NavLink to="/resources">资源列表</NavLink></li>
          <li><NavLink to="/rules">规则管理</NavLink></li>
          <li><NavLink to="/compliance">合规检查</NavLink></li>
          <li><NavLink to="/cost">成本分摊</NavLink></li>
          <li><NavLink to="/audit">审计日志</NavLink></li>
          <li><NavLink to="/templates">标签模板</NavLink></li>
        </ul>
        <div className="navbar-user">
          {session && (
            <div className="account-switcher">
              <button
                className="account-switch-btn"
                onClick={() => setShowAccountSwitcher(!showAccountSwitcher)}
                disabled={isSwitching}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 1rem',
                  background: 'transparent',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  color: '#374151',
                  fontSize: '0.875rem',
                }}
              >
                {isSwitching ? (
                  <span>切换中...</span>
                ) : (
                  <>
                    <span style={{ fontSize: '1rem' }}>👤</span>
                    <span style={{ fontWeight: '500' }}>{session.role.name}</span>
                    <span style={{ color: '#9ca3af' }}>@</span>
                    <span style={{ color: '#3b82f6' }}>{session.account.name}</span>
                    <span style={{ fontSize: '0.75rem' }}>▼</span>
                  </>
                )}
              </button>

              {showAccountSwitcher && (
                <div className="dropdown-menu" style={{
                  position: 'absolute',
                  top: '100%',
                  right: '1rem',
                  marginTop: '0.5rem',
                  background: 'white',
                  borderRadius: '12px',
                  boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
                  minWidth: '320px',
                  zIndex: '1000',
                  border: '1px solid #e5e7eb',
                  overflow: 'hidden',
                }}>
                  <div style={{ padding: '1rem', background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>当前会话</div>
                    <div style={{ fontWeight: '600', color: '#111827' }}>
                      {session.role.name} @ {session.account.name}
                    </div>
                    {session.trustPath && session.trustPath.length > 0 && (
                      <div style={{ fontSize: '0.75rem', color: '#10b981', marginTop: '0.5rem' }}>
                        🔗 通过信任链切换: {session.trustPath.map(p => `${p.from} → ${p.to}`).join(', ')}
                      </div>
                    )}
                  </div>

                  <div style={{ padding: '0.75rem 1rem', fontSize: '0.75rem', color: '#6b7280', fontWeight: '500' }}>
                    快速切换账号
                  </div>
                  {availableAccounts.map(account => (
                    <button
                      key={account.id}
                      onClick={() => handleSeamlessSwitch(account.id)}
                      disabled={isSwitching || account.id === session.account.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        width: '100%',
                        padding: '0.75rem 1rem',
                        border: 'none',
                        background: account.id === session.account.id ? '#eff6ff' : 'transparent',
                        cursor: account.id === session.account.id ? 'default' : 'pointer',
                        textAlign: 'left',
                        transition: 'background 0.2s',
                      }}
                      onMouseEnter={(e) => e.target.style.background = account.id === session.account.id ? '#eff6ff' : '#f9fafb'}
                      onMouseLeave={(e) => e.target.style.background = account.id === session.account.id ? '#eff6ff' : 'transparent'}
                    >
                      <span style={{ fontSize: '1.25rem' }}>
                        {account.id.includes('prod') ? '🔴' : '🟢'}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: '500', color: '#111827' }}>{account.name}</div>
                        <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{account.id}</div>
                      </div>
                      {account.id === session.account.id && (
                        <span style={{ color: '#3b82f6', fontSize: '0.875rem' }}>✓</span>
                      )}
                    </button>
                  ))}

                  <div style={{ padding: '0.75rem 1rem', fontSize: '0.75rem', color: '#6b7280', fontWeight: '500', borderTop: '1px solid #e5e7eb' }}>
                    切换角色
                  </div>
                  {availableRoles.map(role => (
                    <button
                      key={role.id}
                      onClick={() => handleRoleSwitch(role.id)}
                      disabled={isSwitching || role.id === session.role.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        width: '100%',
                        padding: '0.75rem 1rem',
                        border: 'none',
                        background: role.id === session.role.id ? '#eff6ff' : 'transparent',
                        cursor: role.id === session.role.id ? 'default' : 'pointer',
                        textAlign: 'left',
                        transition: 'background 0.2s',
                      }}
                      onMouseEnter={(e) => e.target.style.background = role.id === session.role.id ? '#eff6ff' : '#f9fafb'}
                      onMouseLeave={(e) => e.target.style.background = role.id === session.role.id ? '#eff6ff' : 'transparent'}
                    >
                      <span style={{ fontSize: '1.25rem' }}>
                        {role.id.includes('admin') ? '🔑' : role.id.includes('viewer') ? '👁️' : '👤'}
                      </span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: '500', color: '#111827' }}>{role.name}</div>
                        <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{role.description}</div>
                      </div>
                      {role.id === session.role.id && (
                        <span style={{ color: '#3b82f6', fontSize: '0.875rem' }}>✓</span>
                      )}
                    </button>
                  ))}

                  <div style={{ padding: '0.75rem 1rem', background: '#f9fafb', borderTop: '1px solid #e5e7eb', fontSize: '0.75rem', color: '#9ca3af' }}>
                    💡 账号切换通过角色信任链实现，无需重新登录
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/resources" element={<Resources />} />
          <Route path="/resources/:id" element={<ResourceDetail />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/compliance" element={<Compliance />} />
          <Route path="/cost" element={<CostAllocation />} />
          <Route path="/audit" element={<AuditLogs />} />
          <Route path="/templates" element={<TagTemplates />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
