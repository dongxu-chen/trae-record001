import React, { useState, useEffect } from 'react';
import { AuditService } from '../utils/audit.js';
import { PasswordGenerator } from '../utils/passwordGenerator.js';
import { BreachService } from '../utils/breach.js';

export default function AuditScreen({ auditData, onRunAudit, onViewPassword, onCheckBreach }) {
  const [loading, setLoading] = useState(false);
  const [breachLoading, setBreachLoading] = useState(false);
  const [breachStats, setBreachStats] = useState(null);
  const [breachedPasswords, setBreachedPasswords] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [recommendations, setRecommendations] = useState([]);

  useEffect(() => {
    loadRecommendations();
    loadBreachData();
  }, []);

  const loadRecommendations = async () => {
    try {
      const recs = await AuditService.generateRecommendations();
      setRecommendations(recs);
    } catch (error) {
      console.error('加载建议失败:', error);
    }
  };

  const loadBreachData = async () => {
    try {
      const [stats, passwords] = await Promise.all([
        BreachService.getBreachStats(),
        BreachService.getBreachedPasswords()
      ]);
      setBreachStats(stats);
      setBreachedPasswords(passwords);
    } catch (error) {
      console.error('加载泄露数据失败:', error);
    }
  };

  const handleRunBreachCheck = async () => {
    try {
      setBreachLoading(true);
      await BreachService.checkAllPasswords();
      await loadBreachData();
    } catch (error) {
      console.error('泄露检测失败:', error);
    } finally {
      setBreachLoading(false);
    }
  };

  const handleRunAudit = async () => {
    setLoading(true);
    await onRunAudit();
    await loadRecommendations();
    setLoading(false);
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return '从未';
    return new Date(timestamp).toLocaleDateString('zh-CN');
  };

  const getScoreColor = (score) => {
    if (score >= 90) return 'var(--success)';
    if (score >= 70) return 'var(--info)';
    if (score >= 50) return 'var(--warning)';
    return 'var(--danger)';
  };

  const getScoreLabel = (score) => {
    if (score >= 90) return '优秀';
    if (score >= 70) return '良好';
    if (score >= 50) return '一般';
    return '较差';
  };

  if (!auditData) {
    return (
      <div className="fade-in">
        <div className="card" style={{ textAlign: 'center', padding: '60px' }}>
          <div style={{ fontSize: '64px', marginBottom: '16px' }}>🔍</div>
          <h2 style={{ marginBottom: '16px' }}>安全审计</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
            运行安全审计来检查您的密码安全状况，包括弱密码、重复密码和长期未更新的密码。
          </p>
          <button 
            className="btn btn-primary btn-large" 
            onClick={handleRunAudit}
            disabled={loading}
          >
            {loading ? <span className="loading"></span> : '🔍 开始安全审计'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '24px'
        }}>
          <div>
            <h2 style={{ marginBottom: '8px' }}>安全审计报告</h2>
            <p style={{ color: 'var(--text-secondary)' }}>
              共扫描 {auditData.total} 个密码记录
            </p>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div 
              style={{ 
                fontSize: '48px', 
                fontWeight: 'bold',
                color: getScoreColor(auditData.score)
              }}
            >
              {auditData.score}
            </div>
            <div style={{ color: getScoreColor(auditData.score) }}>
              {getScoreLabel(auditData.score)}
            </div>
          </div>
        </div>

        {auditData.issues.length > 0 && (
          <div style={{ marginBottom: '24px' }}>
            {auditData.issues.map((issue, i) => (
              <div 
                key={i} 
                className={`alert alert-${issue.type === 'danger' ? 'error' : 'warning'}`}
              >
                ⚠️ {issue.message}
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-5" style={{ marginBottom: '24px' }}>
          <div className="card" style={{ background: 'var(--bg-primary)', textAlign: 'center' }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔐</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold' }}>{auditData.total}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>总密码数</div>
          </div>
          <div className="card" style={{ background: 'var(--bg-primary)', textAlign: 'center' }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>⚠️</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--danger)' }}>
              {auditData.weakPasswords.length}
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>弱密码</div>
          </div>
          <div className="card" style={{ background: 'var(--bg-primary)', textAlign: 'center' }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔄</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--warning)' }}>
              {auditData.duplicatePasswords.length}
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>重复密码组</div>
          </div>
          <div className="card" style={{ background: 'var(--bg-primary)', textAlign: 'center' }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>📅</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: 'var(--info)' }}>
              {auditData.oldPasswords.length}
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>长期未更新</div>
          </div>
          <div className="card" style={{ background: 'var(--bg-primary)', textAlign: 'center' }}>
            <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔍</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: breachedPasswords.length > 0 ? 'var(--danger)' : 'var(--text)' }}>
              {breachedPasswords.length}
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>已泄露</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button 
            className="btn btn-primary" 
            onClick={handleRunAudit}
            disabled={loading}
          >
            {loading ? <span className="loading"></span> : '🔄 重新审计'}
          </button>
          <button 
            className="btn btn-secondary" 
            onClick={handleRunBreachCheck}
            disabled={breachLoading}
          >
            {breachLoading ? <span className="loading"></span> : '🔍 检查密码泄露'}
          </button>
        </div>
      </div>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          安全建议
        </button>
        <button 
          className={`tab ${activeTab === 'weak' ? 'active' : ''}`}
          onClick={() => setActiveTab('weak')}
        >
          弱密码 ({auditData.weakPasswords.length})
        </button>
        <button 
          className={`tab ${activeTab === 'duplicate' ? 'active' : ''}`}
          onClick={() => setActiveTab('duplicate')}
        >
          重复密码 ({auditData.duplicatePasswords.length})
        </button>
        <button 
          className={`tab ${activeTab === 'old' ? 'active' : ''}`}
          onClick={() => setActiveTab('old')}
        >
          老旧密码 ({auditData.oldPasswords.length})
        </button>
        <button 
          className={`tab ${activeTab === 'breached' ? 'active' : ''}`}
          onClick={() => setActiveTab('breached')}
        >
          已泄露 ({breachedPasswords.length})
        </button>
      </div>

      {activeTab === 'overview' && (
        <div>
          {recommendations.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🎉</div>
              <h3>密码安全状况优秀！</h3>
              <p>您的密码安全习惯很好，请继续保持。</p>
            </div>
          ) : (
            recommendations.map((rec, i) => (
              <div 
                key={i} 
                className={`audit-item ${rec.priority === 'high' ? 'danger' : ''}`}
              >
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'flex-start',
                  marginBottom: '8px'
                }}>
                  <div>
                    <h4 style={{ marginBottom: '4px' }}>{rec.title}</h4>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                      {rec.description}
                    </p>
                  </div>
                  <span 
                    style={{ 
                      padding: '4px 12px', 
                      borderRadius: '20px',
                      fontSize: '12px',
                      background: rec.priority === 'high' ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)',
                      color: rec.priority === 'high' ? 'var(--danger)' : 'var(--warning)'
                    }}
                  >
                    {rec.priority === 'high' ? '高优先级' : '中优先级'}
                  </span>
                </div>
                {rec.items && rec.items.length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                      受影响的账户：
                    </div>
                    {rec.items.slice(0, 3).map((item, j) => (
                      <div 
                        key={j}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '8px 12px',
                          background: 'var(--bg-primary)',
                          borderRadius: '6px',
                          marginBottom: '4px',
                          fontSize: '13px',
                          cursor: 'pointer'
                        }}
                        onClick={() => onViewPassword(item.id)}
                      >
                        <span>{item.title}</span>
                        <span style={{ color: 'var(--primary)' }}>查看 →</span>
                      </div>
                    ))}
                    {rec.items.length > 3 && (
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        还有 {rec.items.length - 3} 个...
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'weak' && (
        <div>
          {auditData.weakPasswords.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">✅</div>
              <h3>没有弱密码</h3>
              <p>您的所有密码强度都很好！</p>
            </div>
          ) : (
            auditData.weakPasswords.map((pwd, i) => (
              <div key={i} className="audit-item danger">
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center' 
                }}>
                  <div>
                    <h4 style={{ marginBottom: '4px' }}>{pwd.title}</h4>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                      {pwd.username}
                    </p>
                    <p style={{ color: 'var(--danger)', fontSize: '12px', marginTop: '4px' }}>
                      ⚠️ {pwd.reason}
                    </p>
                  </div>
                  <button 
                    className="btn btn-primary btn-small"
                    onClick={() => onViewPassword(pwd.id)}
                  >
                    修复
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'duplicate' && (
        <div>
          {auditData.duplicatePasswords.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">✅</div>
              <h3>没有重复密码</h3>
              <p>您的所有密码都是唯一的！</p>
            </div>
          ) : (
            auditData.duplicatePasswords.map((group, i) => (
              <div key={i} className="audit-item">
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center' 
                  }}>
                    <h4 style={{ marginBottom: '4px' }}>
                      密码重复使用 {group.count} 次
                    </h4>
                    <span style={{ 
                      fontFamily: 'monospace', 
                      fontSize: '13px',
                      background: 'var(--bg-primary)',
                      padding: '4px 8px',
                      borderRadius: '4px'
                    }}>
                      {group.password.substring(0, 4)}***
                    </span>
                  </div>
                </div>
                <div>
                  {group.entries.map((entry, j) => (
                    <div 
                      key={j}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '8px 12px',
                        background: 'var(--bg-primary)',
                        borderRadius: '6px',
                        marginBottom: '4px',
                        fontSize: '13px'
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: '500' }}>{entry.title}</div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                          {entry.username}
                        </div>
                      </div>
                      <button 
                        className="btn btn-secondary btn-small"
                        onClick={() => onViewPassword(entry.id)}
                      >
                        查看
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'old' && (
        <div>
          {auditData.oldPasswords.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">✅</div>
              <h3>没有长期未更新的密码</h3>
              <p>您定期更新密码的习惯很好！</p>
            </div>
          ) : (
            auditData.oldPasswords.map((pwd, i) => (
              <div key={i} className="audit-item">
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center' 
                }}>
                  <div>
                    <h4 style={{ marginBottom: '4px' }}>{pwd.title}</h4>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                      {pwd.username}
                    </p>
                    <p style={{ color: 'var(--warning)', fontSize: '12px', marginTop: '4px' }}>
                      📅 上次更新: {formatDate(pwd.updatedAt)}
                    </p>
                  </div>
                  <button 
                    className="btn btn-primary btn-small"
                    onClick={() => onViewPassword(pwd.id)}
                  >
                    更新
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'breached' && (
        <div>
          {breachedPasswords.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">✅</div>
              <h3>没有发现已泄露的密码</h3>
              <p>您的密码未在已知的数据泄露中出现。</p>
              <button 
                className="btn btn-primary" 
                style={{ marginTop: '16px' }}
                onClick={handleRunBreachCheck}
                disabled={breachLoading}
              >
                {breachLoading ? <span className="loading"></span> : '🔍 立即检查'}
              </button>
            </div>
          ) : (
            <div>
              {breachStats && (
                <div className="alert alert-error" style={{ marginBottom: '20px' }}>
                  <strong>⚠️ 发现 {breachedPasswords.length} 个密码已泄露！</strong>
                  <p style={{ marginTop: '8px', fontSize: '14px' }}>
                    这些密码已在数据泄露事件中被暴露 {breachStats.totalExposures.toLocaleString()} 次。
                    建议立即修改这些密码。
                  </p>
                </div>
              )}
              {breachedPasswords.map((pwd, i) => (
                <div key={i} className="audit-item danger">
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center' 
                  }}>
                    <div>
                      <h4 style={{ marginBottom: '4px' }}>{pwd.title}</h4>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                        {pwd.username}
                      </p>
                      <p style={{ color: 'var(--danger)', fontSize: '12px', marginTop: '4px' }}>
                        ⚠️ 已泄露 {pwd.breachInfo?.count?.toLocaleString()} 次
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button 
                        className="btn btn-secondary btn-small"
                        onClick={() => onCheckBreach && onCheckBreach(pwd.id)}
                      >
                        重新检查
                      </button>
                      <button 
                        className="btn btn-primary btn-small"
                        onClick={() => onViewPassword(pwd.id)}
                      >
                        修改密码
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
