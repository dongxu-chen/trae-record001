import React, { useState, useEffect } from 'react'
import { getConfig, updateConfig } from '../api/client'

function Config() {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const res = await getConfig()
      setConfig(res.data.data)
    } catch (err) {
      console.error('Failed to load config:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateConfig(config)
      alert('配置保存成功')
    } catch (err) {
      alert('保存失败: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading || !config) {
    return <div>加载中...</div>
  }

  return (
    <div>
      <div className="page-header">
        <h2>系统配置</h2>
        <p>配置死锁检测和处理参数</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>数据库连接配置</h3>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>数据库类型</label>
            <select
              value={config.database?.type || 'mysql'}
              onChange={e => setConfig({ ...config, database: { ...config.database, type: e.target.value } })}
            >
              <option value="mysql">MySQL</option>
              <option value="postgres">PostgreSQL</option>
            </select>
          </div>
          <div className="form-group">
            <label>主机地址</label>
            <input
              type="text"
              value={config.database?.host || ''}
              onChange={e => setConfig({ ...config, database: { ...config.database, host: e.target.value } })}
            />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>端口</label>
            <input
              type="number"
              value={config.database?.port || 3306}
              onChange={e => setConfig({ ...config, database: { ...config.database, port: parseInt(e.target.value) || 3306 } })}
            />
          </div>
          <div className="form-group">
            <label>数据库名</label>
            <input
              type="text"
              value={config.database?.dbname || ''}
              onChange={e => setConfig({ ...config, database: { ...config.database, dbname: e.target.value } })}
            />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>用户名</label>
            <input
              type="text"
              value={config.database?.user || ''}
              onChange={e => setConfig({ ...config, database: { ...config.database, user: e.target.value } })}
            />
          </div>
          <div className="form-group">
            <label>密码</label>
            <input
              type="password"
              value={config.database?.password || ''}
              onChange={e => setConfig({ ...config, database: { ...config.database, password: e.target.value } })}
            />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>检测策略配置</h3>
        </div>
        <div className="form-group">
          <div className="toggle-switch">
            <input
              type="checkbox"
              checked={config.strategy?.enabled ?? true}
              onChange={e => setConfig({ ...config, strategy: { ...config.strategy, enabled: e.target.checked } })}
            />
            <span>启用死锁检测</span>
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>检测间隔 (秒)</label>
            <input
              type="number"
              value={config.strategy?.detection_interval || 5}
              onChange={e => setConfig({ ...config, strategy: { ...config.strategy, detection_interval: parseInt(e.target.value) || 5 } })}
            />
          </div>
          <div className="form-group">
            <label>KILL策略</label>
            <select
              value={config.strategy?.kill_strategy || 'priority'}
              onChange={e => setConfig({ ...config, strategy: { ...config.strategy, kill_strategy: e.target.value } })}
            >
              <option value="priority">优先级优先 (推荐)</option>
              <option value="lowest_cost">最低开销优先</option>
              <option value="youngest">最年轻事务 (执行时间最短)</option>
              <option value="oldest">最老事务 (执行时间最长)</option>
              <option value="least_work">最小工作量</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <div className="toggle-switch">
            <input
              type="checkbox"
              checked={config.strategy?.auto_kill ?? false}
              onChange={e => setConfig({ ...config, strategy: { ...config.strategy, auto_kill: e.target.checked } })}
            />
            <span>自动KILL阻塞事务 (谨慎启用)</span>
          </div>
        </div>
        <div className="form-group">
          <label>最大事务时间 (秒)</label>
          <input
            type="number"
            value={config.strategy?.max_transaction_time || 300}
            onChange={e => setConfig({ ...config, strategy: { ...config.strategy, max_transaction_time: parseInt(e.target.value) || 300 } })}
          />
        </div>
        <div className="form-group">
          <label>最小影响行数</label>
          <input
            type="number"
            value={config.strategy?.min_affected_rows || 0}
            onChange={e => setConfig({ ...config, strategy: { ...config.strategy, min_affected_rows: parseInt(e.target.value) || 0 } })}
          />
        </div>
        <div className="form-group">
          <label>排除用户 (逗号分隔)</label>
          <input
            type="text"
            value={(config.strategy?.exclude_users || []).join(', ')}
            onChange={e => setConfig({ 
              ...config, 
              strategy: { 
                ...config.strategy, 
                exclude_users: e.target.value.split(',').map(s => s.trim()).filter(Boolean) 
              } 
            })}
            placeholder="system, admin, root"
          />
        </div>
        <div className="form-group">
          <label>排除数据库 (逗号分隔)</label>
          <input
            type="text"
            value={(config.strategy?.exclude_databases || []).join(', ')}
            onChange={e => setConfig({ 
              ...config, 
              strategy: { 
                ...config.strategy, 
                exclude_databases: e.target.value.split(',').map(s => s.trim()).filter(Boolean) 
              } 
            })}
            placeholder="information_schema, mysql, performance_schema"
          />
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>HTTP服务配置</h3>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>HTTP端口</label>
            <input
              type="number"
              value={config.http_port || 8080}
              onChange={e => setConfig({ ...config, http_port: parseInt(e.target.value) || 8080 })}
            />
          </div>
          <div className="form-group">
            <label>日志级别</label>
            <select
              value={config.log_level || 'info'}
              onChange={e => setConfig({ ...config, log_level: e.target.value })}
            >
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warn">Warning</option>
              <option value="error">Error</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label>数据存储路径</label>
          <input
            type="text"
            value={config.store_path || './data'}
            onChange={e => setConfig({ ...config, store_path: e.target.value })}
          />
        </div>
      </div>

      <div style={{ textAlign: 'right' }}>
        <button 
          className="btn btn-primary" 
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? '保存中...' : '保存配置'}
        </button>
      </div>
    </div>
  )
}

export default Config
