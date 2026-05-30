import { useState, useEffect } from 'react';
import { fetchAutoRepair, applyManualRepair, updateRepairStatus, triggerAutoRepairAll } from '../api';

function AutoRepairPanel({ taskName, onClose }) {
  const [repairData, setRepairData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualForm, setManualForm] = useState({
    repairAction: '',
    oldValue: '',
    newValue: '',
    riskLevel: 'MEDIUM'
  });

  useEffect(() => {
    if (taskName) {
      loadAutoRepairData();
    }
  }, [taskName]);

  const loadAutoRepairData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAutoRepair(taskName);
      setRepairData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusClass = (status) => {
    switch (status) {
      case 'HEALTHY': return 'status-healthy';
      case 'STABLE': return 'status-stable';
      case 'NEEDS_ATTENTION': return 'status-warning';
      case 'CRITICAL': return 'status-critical';
      default: return 'status-unknown';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'HEALTHY': return '健康';
      case 'STABLE': return '稳定';
      case 'NEEDS_ATTENTION': return '需关注';
      case 'CRITICAL': return '严重';
      default: return '未知';
    }
  };

  const getRiskClass = (risk) => {
    switch (risk?.toUpperCase()) {
      case 'HIGH': return 'risk-high';
      case 'MEDIUM': return 'risk-medium';
      default: return 'risk-low';
    }
  };

  const getRepairActionLabel = (action) => {
    switch (action) {
      case 'INCREASE_RETRY_PARAMETERS': return '增加重试参数';
      case 'INCREASE_TIMEOUT': return '增加超时时间';
      case 'INCREASE_RETRY_AND_DELAY': return '增加重试和延迟';
      case 'MANUAL': return '手动修复';
      default: return action;
    }
  };

  const getFailureTypeLabel = (type) => {
    switch (type) {
      case 'LOW_SUCCESS_RATE': return '低成功率';
      case 'HIGH_DURATION': return '执行时间过长';
      case 'HIGH_VARIANCE': return '执行波动大';
      case 'MANUAL': return '手动操作';
      default: return type;
    }
  };

  const handleSubmitManualRepair = async (e) => {
    e.preventDefault();
    try {
      await applyManualRepair(taskName, manualForm);
      setShowManualForm(false);
      setManualForm({ repairAction: '', oldValue: '', newValue: '', riskLevel: 'MEDIUM' });
      await loadAutoRepairData();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUpdateRepairStatus = async (repairId, status) => {
    try {
      await updateRepairStatus(repairId, { status });
      await loadAutoRepairData();
    } catch (err) {
      setError(err.message);
    }
  };

  const formatTime = (timeStr) => {
    return new Date(timeStr).toLocaleString('zh-CN');
  };

  if (loading) return <div className="loading">加载自动修复数据中...</div>;
  if (error) return <div className="error">加载失败: {error}</div>;
  if (!repairData) return null;

  return (
    <div className="auto-repair-panel">
      <div className="panel-header">
        <h3>🔧 自动修复中心</h3>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="repair-summary">
        <div className="repair-summary-card">
          <div className="repair-label">自动修复状态</div>
          <div className={`repair-value ${getStatusClass(repairData.autoRepairStatus)}`}>
            {getStatusLabel(repairData.autoRepairStatus)}
          </div>
        </div>
        <div className="repair-summary-card">
          <div className="repair-label">总修复次数</div>
          <div className="repair-value">{repairData.autoRepairCount ?? 0}</div>
        </div>
        <div className="repair-summary-card">
          <div className="repair-label">成功修复</div>
          <div className="repair-value success">{repairData.successfulRepairs ?? 0}</div>
        </div>
        <div className="repair-summary-card">
          <div className="repair-label">失败修复</div>
          <div className="repair-value danger">{repairData.failedRepairs ?? 0}</div>
        </div>
      </div>

      <div className="current-config">
        <h4>⚙️ 当前配置参数</h4>
        <div className="config-grid">
          <div className="config-item">
            <span className="config-label">最大重试次数:</span>
            <span className="config-value">{repairData.currentConfig?.maxRetries ?? 'N/A'}</span>
          </div>
          <div className="config-item">
            <span className="config-label">重试延迟:</span>
            <span className="config-value">{repairData.currentConfig?.retryDelayMs ?? 'N/A'} ms</span>
          </div>
          <div className="config-item">
            <span className="config-label">超时时间:</span>
            <span className="config-value">{repairData.currentConfig?.timeoutMs ?? 'N/A'} ms</span>
          </div>
          <div className="config-item">
            <span className="config-label">当前成功率:</span>
            <span className={`config-value ${repairData.currentConfig?.currentSuccessRate >= 95 ? 'success' : repairData.currentConfig?.currentSuccessRate >= 85 ? 'warning' : 'danger'}`}>
              {repairData.currentConfig?.currentSuccessRate?.toFixed(1) ?? 'N/A'}%
            </span>
          </div>
          <div className="config-item">
            <span className="config-label">当前评分:</span>
            <span className="config-value">{repairData.currentConfig?.currentScore ?? 'N/A'}</span>
          </div>
          <div className="config-item">
            <span className="config-label">自动修复:</span>
            <span className={`config-value ${repairData.currentConfig?.autoRepairEnabled ? 'success' : 'danger'}`}>
              {repairData.currentConfig?.autoRepairEnabled ? '已启用' : '已禁用'}
            </span>
          </div>
        </div>
      </div>

      <div className="repair-actions">
        <button className="btn btn-primary" onClick={loadAutoRepairData}>
          🔄 重新分析
        </button>
        <button className="btn btn-secondary" onClick={() => setShowManualForm(!showManualForm)}>
          ✋ 手动修复
        </button>
        <button className="btn btn-info" onClick={() => triggerAutoRepairAll()}>
          🚀 批量修复所有任务
        </button>
      </div>

      {showManualForm && (
        <div className="manual-repair-form">
          <h4>手动提交修复请求</h4>
          <form onSubmit={handleSubmitManualRepair}>
            <div className="form-group">
              <label>修复操作:</label>
              <input
                type="text"
                value={manualForm.repairAction}
                onChange={(e) => setManualForm({ ...manualForm, repairAction: e.target.value })}
                placeholder="例如: 调整重试参数"
                required
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>原值:</label>
                <input
                  type="text"
                  value={manualForm.oldValue}
                  onChange={(e) => setManualForm({ ...manualForm, oldValue: e.target.value })}
                  placeholder="retries=3"
                />
              </div>
              <div className="form-group">
                <label>新值:</label>
                <input
                  type="text"
                  value={manualForm.newValue}
                  onChange={(e) => setManualForm({ ...manualForm, newValue: e.target.value })}
                  placeholder="retries=5"
                />
              </div>
            </div>
            <div className="form-group">
              <label>风险等级:</label>
              <select
                value={manualForm.riskLevel}
                onChange={(e) => setManualForm({ ...manualForm, riskLevel: e.target.value })}
              >
                <option value="LOW">低风险</option>
                <option value="MEDIUM">中风险</option>
                <option value="HIGH">高风险</option>
              </select>
            </div>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary">提交</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowManualForm(false)}>取消</button>
            </div>
          </form>
        </div>
      )}

      <div className="recent-repairs">
        <h4>📋 最近修复记录</h4>
        {repairData.recentRepairs?.length > 0 ? (
          <div className="repair-list">
            {repairData.recentRepairs.map((repair) => (
              <div key={repair.id} className="repair-item">
                <div className="repair-item-header">
                  <span className={`failure-type ${repair.failureType === 'MANUAL' ? 'manual' : ''}`}>
                    {getFailureTypeLabel(repair.failureType)}
                  </span>
                  <span className={`risk-badge ${getRiskClass(repair.riskLevel)}`}>
                    {repair.riskLevel === 'HIGH' ? '高风险' : repair.riskLevel === 'MEDIUM' ? '中风险' : '低风险'}
                  </span>
                </div>
                <div className="repair-item-action">
                  <strong>{getRepairActionLabel(repair.repairAction)}:</strong>
                  <span className="value-change">
                    <span className="old-value">{repair.oldValue}</span>
                    <span className="arrow">→</span>
                    <span className="new-value">{repair.newValue}</span>
                  </span>
                </div>
                <div className="repair-item-footer">
                  <span className="repair-time">{formatTime(repair.repairTime)}</span>
                  <span className={`repair-status status-${repair.status?.toLowerCase()}`}>
                    {repair.status === 'SUCCESS' ? '成功' :
                     repair.status === 'FAILED' ? '失败' :
                     repair.status === 'PENDING' ? '待处理' : repair.status}
                  </span>
                  {repair.successRateAfter && (
                    <span className="repair-result">
                      修复后成功率: {repair.successRateAfter.toFixed(1)}%
                    </span>
                  )}
                  {repair.status === 'PENDING' && (
                    <div className="repair-status-actions">
                      <button className="btn btn-small btn-success" onClick={() => handleUpdateRepairStatus(repair.id, 'SUCCESS')}>
                        ✓ 标记成功
                      </button>
                      <button className="btn btn-small btn-danger" onClick={() => handleUpdateRepairStatus(repair.id, 'FAILED')}>
                        ✗ 标记失败
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">暂无修复记录</div>
        )}
      </div>

      <div className="repair-recommendations">
        <h4>💡 优化建议</h4>
        <p>{repairData.recommendations}</p>
      </div>
    </div>
  );
}

export default AutoRepairPanel;
