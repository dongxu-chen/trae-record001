import React, { useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { addAlert, updateAlert, deleteAlert, toggleAlert } from '../store/dashboardSlice'

export default function AlertCenter({ onClose }) {
  const dispatch = useDispatch()
  const alerts = useSelector((state) => state.dashboard.alerts)
  const components = useSelector((state) => state.dashboard.components)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    metricName: '',
    condition: 'above',
    threshold: '',
    severity: 'warning',
    enabled: true,
  })

  const metricComponents = components.filter(c => c.type === 'metric')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!formData.metricName || !formData.threshold) return

    dispatch(addAlert({
      ...formData,
      threshold: parseFloat(formData.threshold),
    }))
    setFormData({
      metricName: '',
      condition: 'above',
      threshold: '',
      severity: 'warning',
      enabled: true,
    })
    setShowForm(false)
  }

  const getConditionText = (condition) => {
    const map = {
      above: '高于',
      below: '低于',
      equal: '等于',
    }
    return map[condition] || condition
  }

  const getSeverityColor = (severity) => {
    const map = {
      info: '#1890ff',
      warning: '#faad14',
      danger: '#f5222d',
    }
    return map[severity] || '#1890ff'
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content alert-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">🔔 数据预警中心</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="alert-actions">
          <button className="add-alert-btn" onClick={() => setShowForm(!showForm)}>
            {showForm ? '取消' : '+ 添加预警'}
          </button>
        </div>

        {showForm && (
          <form className="alert-form" onSubmit={handleSubmit}>
            <h4>新建预警规则</h4>
            <div className="form-row">
              <label>监控指标</label>
              <select
                value={formData.metricName}
                onChange={(e) => setFormData({ ...formData, metricName: e.target.value })}
                required
              >
                <option value="">选择要监控的指标</option>
                {metricComponents.map(c => (
                  <option key={c.id} value={c.title}>{c.title}</option>
                ))}
                <option value="总销售额">总销售额</option>
                <option value="转化率">转化率</option>
                <option value="活跃用户">活跃用户</option>
              </select>
            </div>
            <div className="form-row">
              <label>条件</label>
              <select
                value={formData.condition}
                onChange={(e) => setFormData({ ...formData, condition: e.target.value })}
              >
                <option value="above">高于</option>
                <option value="below">低于</option>
                <option value="equal">等于</option>
              </select>
            </div>
            <div className="form-row">
              <label>阈值</label>
              <input
                type="number"
                value={formData.threshold}
                onChange={(e) => setFormData({ ...formData, threshold: e.target.value })}
                placeholder="输入阈值"
                required
              />
            </div>
            <div className="form-row">
              <label>严重程度</label>
              <select
                value={formData.severity}
                onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
              >
                <option value="info">信息</option>
                <option value="warning">警告</option>
                <option value="danger">危险</option>
              </select>
            </div>
            <button type="submit" className="submit-btn">
              创建预警
            </button>
          </form>
        )}

        <div className="alerts-list">
          {alerts.length === 0 ? (
            <div className="empty-alerts">
              <p>暂无预警规则，点击上方按钮添加</p>
            </div>
          ) : (
            alerts.map(alert => (
              <div
                key={alert.id}
                className={`alert-item ${alert.isActive ? 'active' : ''} ${!alert.enabled ? 'disabled' : ''}`}
                style={{ borderLeftColor: getSeverityColor(alert.severity) }}
              >
                <div className="alert-info">
                  <div className="alert-header">
                    <span className="alert-severity" style={{ backgroundColor: getSeverityColor(alert.severity) }}>
                      {alert.severity === 'danger' ? '🔴' : alert.severity === 'warning' ? '🟡' : '🔵'}
                    </span>
                    <span className="alert-title">
                      {alert.metricName} {getConditionText(alert.condition)} {alert.threshold}
                    </span>
                    {alert.isActive && (
                      <span className="alert-active-badge">⚠️ 告警中</span>
                    )}
                  </div>
                  <div className="alert-desc">
                    当指标{getConditionText(alert.condition)}阈值 {alert.threshold} 时触发告警
                  </div>
                </div>
                <div className="alert-actions-row">
                  <button
                    className={`toggle-btn ${alert.enabled ? 'on' : 'off'}`}
                    onClick={() => dispatch(toggleAlert(alert.id))}
                  >
                    {alert.enabled ? '启用' : '禁用'}
                  </button>
                  <button
                    className="delete-btn"
                    onClick={() => dispatch(deleteAlert(alert.id))}
                  >
                    删除
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
