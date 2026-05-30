import React, { useState, useEffect } from 'react'
import { getRules, createRule, updateRule, deleteRule } from '../api/client'

function Rules() {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    enabled: true,
    priority: 1,
    condition: {
      min_transaction_time: 0,
      min_affected_rows: 0,
      min_cost_score: 0,
      users: '',
      databases: '',
      query_patterns: '',
      transaction_types: [],
      severity_levels: []
    },
    action: {
      kill_transaction: true,
      log_only: false,
      notify: true,
      message: '',
      priority_boost: 0
    }
  })

  useEffect(() => {
    loadRules()
  }, [])

  const loadRules = async () => {
    try {
      const res = await getRules()
      setRules(res.data.data || [])
    } catch (err) {
      console.error('Failed to load rules:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (rule) => {
    setEditingRule(rule)
    setFormData({
      id: rule.id,
      name: rule.name,
      description: rule.description,
      enabled: rule.enabled,
      priority: rule.priority,
      condition: {
        min_transaction_time: rule.condition?.min_transaction_time || 0,
        min_affected_rows: rule.condition?.min_affected_rows || 0,
        min_cost_score: rule.condition?.min_cost_score || 0,
        users: (rule.condition?.users || []).join(','),
        databases: (rule.condition?.databases || []).join(','),
        query_patterns: (rule.condition?.query_patterns || []).join(','),
        transaction_types: rule.condition?.transaction_types || [],
        severity_levels: rule.condition?.severity_levels || []
      },
      action: {
        kill_transaction: rule.action?.kill_transaction || false,
        log_only: rule.action?.log_only || false,
        notify: rule.action?.notify || false,
        message: rule.action?.message || '',
        priority_boost: rule.action?.priority_boost || 0
      }
    })
    setShowModal(true)
  }

  const handleAdd = () => {
    setEditingRule(null)
    setFormData({
      name: '',
      description: '',
      enabled: true,
      priority: 1,
      condition: {
        min_transaction_time: 0,
        min_affected_rows: 0,
        min_cost_score: 0,
        users: '',
        databases: '',
        query_patterns: '',
        transaction_types: [],
        severity_levels: []
      },
      action: {
        kill_transaction: true,
        log_only: false,
        notify: true,
        message: '',
        priority_boost: 0
      }
    })
    setShowModal(true)
  }

  const handleTransactionTypeChange = (type) => {
    const current = formData.condition.transaction_types
    const updated = current.includes(type)
      ? current.filter(t => t !== type)
      : [...current, type]
    setFormData({
      ...formData,
      condition: { ...formData.condition, transaction_types: updated }
    })
  }

  const handleSeverityLevelChange = (level) => {
    const current = formData.condition.severity_levels
    const updated = current.includes(level)
      ? current.filter(l => l !== level)
      : [...current, level]
    setFormData({
      ...formData,
      condition: { ...formData.condition, severity_levels: updated }
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const ruleData = {
        ...formData,
        condition: {
          ...formData.condition,
          users: formData.condition.users ? formData.condition.users.split(',').map(s => s.trim()).filter(Boolean) : [],
          databases: formData.condition.databases ? formData.condition.databases.split(',').map(s => s.trim()).filter(Boolean) : [],
          query_patterns: formData.condition.query_patterns ? formData.condition.query_patterns.split(',').map(s => s.trim()).filter(Boolean) : []
        }
      }

      if (editingRule) {
        await updateRule(editingRule.id, ruleData)
      } else {
        ruleData.id = 'rule_' + Date.now()
        await createRule(ruleData)
      }

      setShowModal(false)
      loadRules()
    } catch (err) {
      alert('保存失败: ' + err.message)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('确定要删除此规则吗？')) {
      return
    }
    try {
      await deleteRule(id)
      loadRules()
    } catch (err) {
      alert('删除失败: ' + err.message)
    }
  }

  if (loading) {
    return <div>加载中...</div>
  }

  return (
    <div>
      <div className="page-header">
        <h2>规则引擎</h2>
        <p>管理死锁处理规则</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>规则列表</h3>
          <button className="btn btn-primary" onClick={handleAdd}>
            添加规则
          </button>
        </div>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>描述</th>
              <th>优先级</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {rules.map(rule => (
              <tr key={rule.id}>
                <td>{rule.id}</td>
                <td>{rule.name}</td>
                <td>{rule.description}</td>
                <td>{rule.priority}</td>
                <td>
                  <span className={`status-badge ${rule.enabled ? 'resolved' : 'pending'}`}>
                    {rule.enabled ? '启用' : '禁用'}
                  </span>
                </td>
                <td>
                  <button className="btn" onClick={() => handleEdit(rule)} style={{ marginRight: '8px' }}>
                    编辑
                  </button>
                  <button className="btn btn-danger" onClick={() => handleDelete(rule.id)}>
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div className="card" style={{ width: '700px', maxHeight: '90vh', overflow: 'auto' }}>
            <div className="card-header">
              <h3>{editingRule ? '编辑规则' : '添加规则'}</h3>
              <button className="btn" onClick={() => setShowModal(false)}>关闭</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>规则名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>描述</label>
                <textarea
                  value={formData.description}
                  onChange={e => setFormData({ ...formData, description: e.target.value })}
                  rows="2"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>优先级</label>
                  <input
                    type="number"
                    value={formData.priority}
                    onChange={e => setFormData({ ...formData, priority: parseInt(e.target.value) || 1 })}
                    min="1"
                  />
                </div>
                <div className="form-group">
                  <label>状态</label>
                  <div className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={formData.enabled}
                      onChange={e => setFormData({ ...formData, enabled: e.target.checked })}
                    />
                    <span>{formData.enabled ? '启用' : '禁用'}</span>
                  </div>
                </div>
              </div>

              <h4 style={{ margin: '20px 0 12px' }}>条件配置</h4>
              <div className="form-row">
                <div className="form-group">
                  <label>最小事务时间 (秒)</label>
                  <input
                    type="number"
                    value={formData.condition.min_transaction_time}
                    onChange={e => setFormData({
                      ...formData,
                      condition: { ...formData.condition, min_transaction_time: parseInt(e.target.value) || 0 }
                    })}
                  />
                </div>
                <div className="form-group">
                  <label>最小影响行数</label>
                  <input
                    type="number"
                    value={formData.condition.min_affected_rows}
                    onChange={e => setFormData({
                      ...formData,
                      condition: { ...formData.condition, min_affected_rows: parseInt(e.target.value) || 0 }
                    })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>最小开销分数</label>
                <input
                  type="number"
                  value={formData.condition.min_cost_score}
                  onChange={e => setFormData({
                    ...formData,
                    condition: { ...formData.condition, min_cost_score: parseInt(e.target.value) || 0 }
                  })}
                />
              </div>
              <div className="form-group">
                <label>用户 (逗号分隔)</label>
                <input
                  type="text"
                  value={formData.condition.users}
                  onChange={e => setFormData({
                    ...formData,
                    condition: { ...formData.condition, users: e.target.value }
                  })}
                  placeholder="user1, user2, user3"
                />
              </div>
              <div className="form-group">
                <label>数据库 (逗号分隔)</label>
                <input
                  type="text"
                  value={formData.condition.databases}
                  onChange={e => setFormData({
                    ...formData,
                    condition: { ...formData.condition, databases: e.target.value }
                  })}
                  placeholder="db1, db2, db3"
                />
              </div>
              <div className="form-group">
                <label>查询模式 (逗号分隔)</label>
                <input
                  type="text"
                  value={formData.condition.query_patterns}
                  onChange={e => setFormData({
                    ...formData,
                    condition: { ...formData.condition, query_patterns: e.target.value }
                  })}
                  placeholder="UPDATE, DELETE, INSERT"
                />
              </div>
              
              <div className="form-group">
                <label>事务类型</label>
                <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
                  {['READ', 'WRITE', 'DDL'].map(type => (
                    <label key={type} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input
                        type="checkbox"
                        checked={formData.condition.transaction_types.includes(type)}
                        onChange={() => handleTransactionTypeChange(type)}
                      />
                      {type}
                    </label>
                  ))}
                </div>
              </div>
              
              <div className="form-group">
                <label>严重等级</label>
                <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
                  {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map(level => (
                    <label key={level} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input
                        type="checkbox"
                        checked={formData.condition.severity_levels.includes(level)}
                        onChange={() => handleSeverityLevelChange(level)}
                      />
                      {level}
                    </label>
                  ))}
                </div>
              </div>

              <h4 style={{ margin: '20px 0 12px' }}>动作配置</h4>
              <div className="form-group">
                <div className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={formData.action.kill_transaction}
                    onChange={e => setFormData({
                      ...formData,
                      action: { ...formData.action, kill_transaction: e.target.checked }
                    })}
                  />
                  <span>KILL事务</span>
                </div>
              </div>
              <div className="form-group">
                <div className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={formData.action.log_only}
                    onChange={e => setFormData({
                      ...formData,
                      action: { ...formData.action, log_only: e.target.checked }
                    })}
                  />
                  <span>仅记录日志</span>
                </div>
              </div>
              <div className="form-group">
                <div className="toggle-switch">
                  <input
                    type="checkbox"
                    checked={formData.action.notify}
                    onChange={e => setFormData({
                      ...formData,
                      action: { ...formData.action, notify: e.target.checked }
                    })}
                  />
                  <span>发送通知</span>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>优先级提升</label>
                  <input
                    type="number"
                    value={formData.action.priority_boost}
                    onChange={e => setFormData({
                      ...formData,
                      action: { ...formData.action, priority_boost: parseInt(e.target.value) || 0 }
                    })}
                    min="0"
                    max="100"
                  />
                </div>
                <div className="form-group">
                  <label>消息</label>
                  <input
                    type="text"
                    value={formData.action.message}
                    onChange={e => setFormData({
                      ...formData,
                      action: { ...formData.action, message: e.target.value }
                    })}
                  />
                </div>
              </div>

              <div style={{ marginTop: '24px', textAlign: 'right' }}>
                <button type="button" className="btn" onClick={() => setShowModal(false)} style={{ marginRight: '12px' }}>
                  取消
                </button>
                <button type="submit" className="btn btn-primary">
                  保存
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Rules
