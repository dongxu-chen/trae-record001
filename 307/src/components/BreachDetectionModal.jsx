import React, { useState, useEffect } from 'react';
import { BreachService } from '../utils/breach.js';

export default function BreachDetectionModal({ onClose, onViewPassword, passwordId = null }) {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [results, setResults] = useState(null);
  const [checkingSingle, setCheckingSingle] = useState(false);
  const [singleResult, setSingleResult] = useState(null);

  useEffect(() => {
    if (passwordId) {
      checkSinglePassword();
    }
  }, [passwordId]);

  const checkSinglePassword = async () => {
    try {
      setCheckingSingle(true);
      setLoading(true);
      const result = await BreachService.checkPasswordById(passwordId);
      setSingleResult(result);
    } catch (error) {
      console.error('检查失败:', error);
    } finally {
      setLoading(false);
      setCheckingSingle(false);
    }
  };

  const checkAllPasswords = async () => {
    try {
      setLoading(true);
      const result = await BreachService.checkAllPasswords((current, total) => {
        setProgress({ current, total });
      });
      setResults(result);
    } catch (error) {
      console.error('批量检查失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCount = (count) => {
    return count.toLocaleString('zh-CN');
  };

  if (passwordId && checkingSingle) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div className="loading"></div>
            <p style={{ marginTop: '16px' }}>正在检查密码是否泄露...</p>
          </div>
        </div>
      </div>
    );
  }

  if (passwordId && singleResult) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2 className="modal-title">🔍 密码泄露检测结果</h2>
            <button className="close-btn" onClick={onClose}>×</button>
          </div>

          <div className={`card ${singleResult.breachInfo.breached ? '' : 'bg-green-50'}`} style={{
            background: singleResult.breachInfo.breached ? 'var(--danger-bg)' : 'var(--success-bg)',
            border: `1px solid ${singleResult.breachInfo.breached ? 'var(--danger)' : 'var(--success)'}`
          }}>
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <div style={{ fontSize: '64px', marginBottom: '16px' }}>
                {singleResult.breachInfo.breached ? '⚠️' : '✅'}
              </div>
              <h3 style={{ marginBottom: '8px' }}>
                {singleResult.breachInfo.breached ? '密码已泄露！' : '密码安全'}
              </h3>
              <p style={{ color: 'var(--text-secondary)' }}>
                {singleResult.title} - {singleResult.username}
              </p>
            </div>

            {singleResult.breachInfo.breached && (
              <div className="alert alert-error" style={{ marginTop: '16px' }}>
                <strong>⚠️ 此密码已在数据泄露中被发现 {formatCount(singleResult.breachInfo.count)} 次！</strong>
                <p style={{ marginTop: '8px', fontSize: '14px' }}>
                  建议立即修改此密码，并在其他使用相同密码的网站上也进行修改。
                </p>
              </div>
            )}

            {!singleResult.breachInfo.breached && (
              <div className="alert alert-success" style={{ marginTop: '16px' }}>
                <strong>✅ 很好！</strong>此密码未在已知的数据泄露中被发现。
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ flex: 1 }}
                onClick={onClose}
              >
                关闭
              </button>
              {singleResult.breachInfo.breached && (
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                  onClick={() => {
                    onClose();
                    onViewPassword && onViewPassword(passwordId);
                  }}
                >
                  修改密码
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (results) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2 className="modal-title">🔍 批量泄露检测结果</h2>
            <button className="close-btn" onClick={onClose}>×</button>
          </div>

          <div className="grid grid-cols-3" style={{ marginBottom: '20px' }}>
            <div className="card" style={{ background: 'var(--bg-primary)', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', marginBottom: '4px' }}>🔐</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{results.checked}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>已检查</div>
            </div>
            <div className="card" style={{ background: 'var(--bg-primary)', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', marginBottom: '4px' }}>⚠️</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: results.breachedCount > 0 ? 'var(--danger)' : 'var(--text)' }}>
                {results.breachedCount}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>已泄露</div>
            </div>
            <div className="card" style={{ background: 'var(--bg-primary)', textAlign: 'center' }}>
              <div style={{ fontSize: '24px', marginBottom: '4px' }}>✅</div>
              <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--success)' }}>
                {results.checked - results.breachedCount}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>安全</div>
            </div>
          </div>

          {results.breachedCount > 0 ? (
            <div>
              <h4 style={{ marginBottom: '16px' }}>
                发现 {results.breachedCount} 个泄露的密码：
              </h4>
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                {results.breachedPasswords.map((pwd, i) => (
                  <div key={i} className="audit-item danger" style={{ marginBottom: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: '500', marginBottom: '4px' }}>
                          {pwd.title}
                        </div>
                        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                          {pwd.username}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--danger)', marginTop: '4px' }}>
                          ⚠️ 已泄露 {formatCount(pwd.breachInfo.count)} 次
                        </div>
                      </div>
                      <button
                        className="btn btn-primary btn-small"
                        onClick={() => {
                          onClose();
                          onViewPassword && onViewPassword(pwd.id);
                        }}
                      >
                        修改
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">🎉</div>
              <h3>所有密码都是安全的！</h3>
              <p>您的密码未在已知的数据泄露中被发现。</p>
            </div>
          )}

          <div className="alert alert-info" style={{ marginTop: '20px' }}>
            <strong>ℹ️ 关于 Have I Been Pwned</strong>
            <p style={{ marginTop: '8px', fontSize: '13px' }}>
              使用 k-anonymity 隐私保护技术，仅发送密码哈希的前5个字符，确保您的密码安全。
              数据来源：Have I Been Pwned API。
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1 }}
              onClick={() => setResults(null)}
            >
              重新检查
            </button>
            <button
              type="button"
              className="btn btn-primary"
              style={{ flex: 1 }}
              onClick={onClose}
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (loading && progress.total > 0) {
    const percent = Math.round((progress.current / progress.total) * 100);
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <h3 style={{ marginBottom: '20px' }}>正在检查密码泄露...</h3>
            <div style={{
              width: '100%',
              height: '8px',
              background: 'var(--bg-tertiary)',
              borderRadius: '4px',
              overflow: 'hidden',
              marginBottom: '12px'
            }}>
              <div style={{
                width: `${percent}%`,
                height: '100%',
                background: 'var(--primary)',
                transition: 'width 0.3s ease'
              }}></div>
            </div>
            <p style={{ color: 'var(--text-secondary)' }}>
              {progress.current} / {progress.total} ({percent}%)
            </p>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '16px' }}>
              使用 Have I Been Pwned API 检查密码是否在已知数据泄露中出现
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">🔍 密码泄露检测</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="card" style={{ background: 'var(--bg-tertiary)', marginBottom: '20px' }}>
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <div style={{ fontSize: '64px', marginBottom: '16px' }}>🔍</div>
            <h3 style={{ marginBottom: '8px' }}>检查密码是否已泄露</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              通过 Have I Been Pwned API 检查您的密码是否在已知的数据泄露事件中出现。
            </p>
          </div>
        </div>

        <div className="alert alert-info" style={{ marginBottom: '20px' }}>
          <strong>🔒 隐私保护</strong>
          <ul style={{ marginTop: '8px', paddingLeft: '20px', fontSize: '13px' }}>
            <li>使用 k-anonymity 技术，仅发送密码 SHA-1 哈希的前 5 个字符</li>
            <li>您的完整密码永远不会离开您的设备</li>
            <li>所有检查在本地进行匹配，保护您的隐私</li>
          </ul>
        </div>

        <div style={{ display: 'flex', gap: '12px', flexDirection: 'column' }}>
          <button
            className="btn btn-primary btn-large"
            onClick={checkAllPasswords}
            disabled={loading}
          >
            {loading ? <span className="loading"></span> : '🔍 检查所有密码'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={onClose}
          >
            取消
          </button>
        </div>

        <div style={{ marginTop: '24px', padding: '16px', background: 'var(--bg-tertiary)', borderRadius: '8px' }}>
          <h4 style={{ marginBottom: '8px' }}>什么是密码泄露？</h4>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
            当网站或服务发生数据泄露时，用户的密码可能会被黑客获取并在暗网上分享。
            定期检查您的密码是否已泄露，可以帮助您及时采取措施保护账户安全。
          </p>
        </div>
      </div>
    </div>
  );
}
