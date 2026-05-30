import React, { useState, useEffect } from 'react'
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { getStatistics } from '../api/client'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']
const SEVERITY_COLORS = {
  'CRITICAL': '#ff4d4f',
  'HIGH': '#fa8c16',
  'MEDIUM': '#faad14',
  'LOW': '#52c41a'
}
const TYPE_COLORS = {
  'READ': '#52c41a',
  'WRITE': '#1890ff',
  'DDL': '#ff4d4f',
  'UNKNOWN': '#666'
}

function Statistics() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStatistics()
  }, [])

  const loadStatistics = async () => {
    try {
      const res = await getStatistics()
      setStats(res.data.data)
    } catch (err) {
      console.error('Failed to load statistics:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div>加载中...</div>
  }

  const userData = stats?.TopDeadlockUsers?.map(item => ({
    name: item.Key,
    value: item.Value
  })) || []

  const tableData = stats?.TopDeadlockTables?.map(item => ({
    name: item.Key,
    value: item.Value
  })) || []

  const hourlyData = stats?.DeadlocksByHour?.map(item => ({
    name: item.Time.split(' ')[1] || item.Time,
    死锁数: item.Count
  })) || []

  const typeData = stats?.DeadlocksByType?.map(item => ({
    name: item.Key,
    value: item.Value
  })) || []

  const severityData = stats?.DeadlocksBySeverity?.map(item => ({
    name: item.Key,
    value: item.Value
  })) || []

  return (
    <div>
      <div className="page-header">
        <h2>统计分析</h2>
        <p>死锁历史数据分析和趋势</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">总死锁数</div>
          <div className="value">{stats?.TotalDeadlocks || 0}</div>
        </div>
        <div className="stat-card success">
          <div className="label">已解决</div>
          <div className="value">{stats?.ResolvedDeadlocks || 0}</div>
        </div>
        <div className="stat-card">
          <div className="label">自动KILL</div>
          <div className="value">{stats?.AutoKilledCount || 0}</div>
        </div>
        <div className="stat-card warning">
          <div className="label">手动KILL</div>
          <div className="value">{stats?.ManualKilledCount || 0}</div>
        </div>
      </div>

      {stats?.AvgDetectionLatency && (
        <div className="card">
          <div className="card-header">
            <h3>检测性能</h3>
          </div>
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#1890ff' }}>
              平均检测延迟: {stats.AvgDetectionLatency}
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>死锁时间分布</h3>
        </div>
        <div className="chart-container">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="死锁数" fill="#1890ff" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="form-row">
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-header">
            <h3>用户死锁分布</h3>
          </div>
          <div className="chart-container">
            {userData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={userData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {userData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p style={{ textAlign: 'center', paddingTop: '100px', color: '#666' }}>
                暂无数据
              </p>
            )}
          </div>
        </div>

        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-header">
            <h3>事务类型分布</h3>
          </div>
          <div className="chart-container">
            {typeData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={typeData}
                    cx="50%"
                    cy="50%"
                    labelLine={true}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {typeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={TYPE_COLORS[entry.name] || COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p style={{ textAlign: 'center', paddingTop: '100px', color: '#666' }}>
                暂无数据
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>严重等级分布</h3>
        </div>
        <div className="chart-container">
          {severityData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={severityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" name="死锁数">
                  {severityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={SEVERITY_COLORS[entry.name] || COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ textAlign: 'center', paddingTop: '100px', color: '#666' }}>
              暂无数据
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default Statistics
