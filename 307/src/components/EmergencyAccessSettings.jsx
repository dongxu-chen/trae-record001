import React, { useState, useEffect } from 'react';
import { EmergencyAccessService } from '../utils/emergency.js';

export default function EmergencyAccessSettings({ showNotification }) {
  const [activeTab, setActiveTab] = useState('contacts');
  const [contacts, setContacts] = useState([]);
  const [requests, setRequests] = useState([]);
  const [grants, setGrants] = useState([]);
  const [showAddContact, setShowAddContact] = useState(false);
  const [newContact, setNewContact] = useState({ name: '', email: '', waitingPeriod: 24 * 60 * 60 * 1000 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    try {
      const [contactsData, requestsData, grantsData] = await Promise.all([
        EmergencyAccessService.getContacts(),
        EmergencyAccessService.getRequests(),
        EmergencyAccessService.getActiveGrants()
      ]);
      setContacts(contactsData);
      setRequests(requestsData);
      setGrants(grantsData);
    } catch (error) {
      console.error('加载数据失败:', error);
    }
  };

  const handleAddContact = async (e) => {
    e.preventDefault();
    
    if (!newContact.name || !newContact.email) {
      showNotification('请填写联系人名称和邮箱', 'error');
      return;
    }

    try {
      setLoading(true);
      await EmergencyAccessService.addContact(newContact);
      setShowAddContact(false);
      setNewContact({ name: '', email: '', waitingPeriod: 24 * 60 * 60 * 1000 });
      await loadData();
      showNotification('紧急联系人添加成功', 'success');
    } catch (error) {
      showNotification(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveContact = async (contactId) => {
    if (confirm('确定要删除此紧急联系人吗？相关的访问请求也会被撤销。')) {
      try {
        await EmergencyAccessService.removeContact(contactId);
        await loadData();
        showNotification('联系人已删除', 'success');
      } catch (error) {
        showNotification(error.message, 'error');
      }
    }
  };

  const handleApproveRequest = async (requestId) => {
    try {
      setLoading(true);
      const duration = 1 * 60 * 60 * 1000;
      const result = await EmergencyAccessService.approveRequest(requestId, { duration });
      await loadData();
      showNotification('紧急访问已批准，访问链接已生成', 'success');
      
      if (confirm('是否复制紧急访问链接？\n' + result.accessUrl)) {
        navigator.clipboard.writeText(result.accessUrl);
      }
    } catch (error) {
      showNotification(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDenyRequest = async (requestId) => {
    const reason = prompt('请输入拒绝原因（可选）：');
    try {
      await EmergencyAccessService.denyRequest(requestId, reason);
      await loadData();
      showNotification('已拒绝访问请求', 'success');
    } catch (error) {
      showNotification(error.message, 'error');
    }
  };

  const handleRevokeGrant = async (grantId) => {
    if (confirm('确定要撤销此紧急访问授权吗？')) {
      try {
        await EmergencyAccessService.revokeGrant(grantId);
        await loadData();
        showNotification('访问授权已撤销', 'success');
      } catch (error) {
        showNotification(error.message, 'error');
      }
    }
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  const formatWaitingPeriod = (ms) => {
    if (ms === 0) return '立即';
    const hours = ms / (60 * 60 * 1000);
    if (hours < 24) return `${hours}小时`;
    return `${hours / 24}天`;
  };

  const getStatusLabel = (status) => {
    const labels = {
      pending: { label: '待处理', class: 'warning' },
      approved: { label: '已批准', class: 'success' },
      denied: { label: '已拒绝', class: 'danger' },
      cancelled: { label: '已取消', class: 'secondary' },
      active: { label: '活跃', class: 'success' },
      revoked: { label: '已撤销', class: 'danger' },
      expired: { label: '已过期', class: 'secondary' }
    };
    return labels[status] || { label: status, class: 'secondary' };
  };

  const tabs = [
    { id: 'contacts', label: '紧急联系人', icon: '👥', count: contacts.length },
    { id: 'requests', label: '访问请求', icon: '📨', count: requests.filter(r => r.status === 'pending').length },
    { id: 'grants', label: '活跃授权', icon: '🔑', count: grants.length }
  ];

  return (
    <div className="fade-in">
      <div className="card" style={{ marginBottom: '24px' }}>
        <h2 style={{ marginBottom: '8px' }}>🛡️ 紧急访问</h2>
        <p style={{ color: 'var(--text-secondary)' }}>
          设置紧急联系人，在您无法访问时可请求访问您的密码库。
        </p>
      </div>

      <div className="tabs" style={{ marginBottom: '20px' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon} {tab.label}
            {tab.count > 0 && (
              <span className="badge" style={{ marginLeft: '8px' }}>{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {activeTab === 'contacts' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3>紧急联系人</h3>
            <button
              className="btn btn-primary"
              onClick={() => setShowAddContact(true)}
            >
              ➕ 添加联系人
            </button>
          </div>

          {contacts.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">👥</div>
              <h3>暂无紧急联系人</h3>
              <p>添加紧急联系人，确保在紧急情况下仍能访问您的密码库。</p>
            </div>
          ) : (
            contacts.map(contact => (
              <div key={contact.id} className="card" style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <div style={{ fontSize: '32px' }}>👤</div>
                      <div>
                        <h4 style={{ marginBottom: '2px' }}>{contact.name}</h4>
                        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                          {contact.email}
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2" style={{ marginTop: '12px' }}>
                      <div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                          等待期
                        </div>
                        <div>{formatWaitingPeriod(contact.waitingPeriod)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                          添加时间
                        </div>
                        <div style={{ fontSize: '13px' }}>{formatDate(contact.createdAt)}</div>
                      </div>
                    </div>
                    <div style={{ marginTop: '8px' }}>
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        权限：{contact.permissions.includes('read') ? '只读' : '无'}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <button
                      className="btn btn-danger btn-small"
                      onClick={() => handleRemoveContact(contact.id)}
                    >
                      删除
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}

          {showAddContact && (
            <div className="modal-overlay" onClick={() => setShowAddContact(false)}>
              <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <h2 className="modal-title">➕ 添加紧急联系人</h2>
                  <button className="close-btn" onClick={() => setShowAddContact(false)}>×</button>
                </div>

                <form onSubmit={handleAddContact}>
                  <div className="input-group">
                    <label>联系人名称</label>
                    <input
                      type="text"
                      value={newContact.name}
                      onChange={(e) => setNewContact({ ...newContact, name: e.target.value })}
                      placeholder="如：家人姓名"
                      required
                    />
                  </div>

                  <div className="input-group">
                    <label>电子邮箱</label>
                    <input
                      type="email"
                      value={newContact.email}
                      onChange={(e) => setNewContact({ ...newContact, email: e.target.value })}
                      placeholder="example@email.com"
                      required
                    />
                  </div>

                  <div className="input-group">
                    <label>等待期</label>
                    <select
                      value={newContact.waitingPeriod}
                      onChange={(e) => setNewContact({ ...newContact, waitingPeriod: Number(e.target.value) })}
                    >
                      {EmergencyAccessService.getWaitingPeriodOptions().map(opt => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                      等待期是指从请求访问到自动批准的时间，在此期间您可以拒绝请求。
                    </p>
                  </div>

                  <div className="alert alert-warning" style={{ marginTop: '16px' }}>
                    <strong>⚠️ 重要提示：</strong>
                    <ul style={{ marginTop: '8px', paddingLeft: '20px', fontSize: '13px' }}>
                      <li>紧急联系人将有权访问您的所有密码</li>
                      <li>建议设置合理的等待期，防止未授权访问</li>
                      <li>您可以随时撤销紧急联系人的访问权限</li>
                    </ul>
                  </div>

                  <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '24px' }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setShowAddContact(false)}
                    >
                      取消
                    </button>
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={loading}
                    >
                      {loading ? <span className="loading"></span> : '添加'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'requests' && (
        <div>
          <h3 style={{ marginBottom: '16px' }}>访问请求</h3>
          
          {requests.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📨</div>
              <h3>暂无访问请求</h3>
              <p>当紧急联系人请求访问时，您可以在此处批准或拒绝。</p>
            </div>
          ) : (
            requests.map(request => {
              const status = getStatusLabel(request.status);
              return (
                <div key={request.id} className="card" style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                        <h4 style={{ margin: 0 }}>{request.contactName}</h4>
                        <span className={`badge badge-${status.class}`}>{status.label}</span>
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                        {request.contactEmail}
                      </div>
                      {request.reason && (
                        <div className="card" style={{ background: 'var(--bg-tertiary)', padding: '12px', marginBottom: '12px' }}>
                          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                            请求原因：
                          </div>
                          <div>{request.reason}</div>
                        </div>
                      )}
                      <div className="grid grid-cols-2" style={{ marginTop: '12px' }}>
                        <div>
                          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                            请求时间
                          </div>
                          <div style={{ fontSize: '13px' }}>{formatDate(request.requestedAt)}</div>
                        </div>
                        {request.status === 'pending' && (
                          <div>
                            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                              等待期结束
                            </div>
                            <div style={{ fontSize: '13px' }}>{formatDate(request.waitingPeriodEnds)}</div>
                          </div>
                        )}
                      </div>
                    </div>
                    {request.status === 'pending' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginLeft: '16px' }}>
                        <button
                          className="btn btn-primary btn-small"
                          onClick={() => handleApproveRequest(request.id)}
                          disabled={loading}
                        >
                          批准
                        </button>
                        <button
                          className="btn btn-secondary btn-small"
                          onClick={() => handleDenyRequest(request.id)}
                        >
                          拒绝
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {activeTab === 'grants' && (
        <div>
          <h3 style={{ marginBottom: '16px' }}>活跃授权</h3>
          
          {grants.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🔑</div>
              <h3>暂无活跃授权</h3>
              <p>当前没有活跃的紧急访问授权。</p>
            </div>
          ) : (
            grants.map(grant => (
              <div key={grant.id} className="card" style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <h4 style={{ margin: 0 }}>{grant.contactName}</h4>
                      <span className="badge badge-success">活跃</span>
                    </div>
                    <div className="grid grid-cols-2" style={{ marginTop: '12px' }}>
                      <div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                          授权时间
                        </div>
                        <div style={{ fontSize: '13px' }}>{formatDate(grant.grantedAt)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '2px' }}>
                          过期时间
                        </div>
                        <div style={{ fontSize: '13px' }}>{formatDate(grant.expiresAt)}</div>
                      </div>
                    </div>
                    <div style={{ marginTop: '8px' }}>
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        权限：{grant.permissions.includes('read') ? '只读' : '无'}
                      </span>
                    </div>
                  </div>
                  <div style={{ marginLeft: '16px' }}>
                    <button
                      className="btn btn-danger btn-small"
                      onClick={() => handleRevokeGrant(grant.id)}
                    >
                      撤销
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      <div className="card" style={{ marginTop: '24px' }}>
        <h3 style={{ marginBottom: '16px' }}>🔒 安全说明</h3>
        <div style={{ background: 'var(--bg-tertiary)', padding: '20px', borderRadius: '8px' }}>
          <h4 style={{ marginBottom: '12px' }}>紧急访问如何工作？</h4>
          <ol style={{ paddingLeft: '20px', lineHeight: '2', fontSize: '14px' }}>
            <li>您添加紧急联系人并设置等待期</li>
            <li>紧急联系人可随时请求访问您的密码库</li>
            <li>请求发出后，系统会通知您</li>
            <li>在等待期内，您可以批准或拒绝请求</li>
            <li>如果等待期结束您未处理，请求将自动批准</li>
            <li>批准后，紧急联系人将获得有限时间的访问权限</li>
          </ol>
          <div className="alert alert-warning" style={{ marginTop: '16px' }}>
            <strong>💡 建议：</strong>
            <ul style={{ marginTop: '8px', paddingLeft: '20px', fontSize: '13px' }}>
              <li>选择您信任的家人或朋友作为紧急联系人</li>
              <li>设置合理的等待期（建议至少24小时）</li>
              <li>定期检查访问请求</li>
              <li>及时撤销不再需要的访问权限</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
