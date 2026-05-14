import { useState, useEffect, useMemo } from 'react'
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts'
import useLocalStorage from '../hooks/useLocalStorage'
import { getSessions, getCurrentUser, getSessionsFromCloud } from '../utils/sync'

const COLORS = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dfe6e9']

function Stats() {
  const [sessions, setSessions] = useState([])
  const [timeRange, setTimeRange] = useState('week')
  const [stats, setStats] = useLocalStorage('pomodoro_stats', {
    totalPomodoros: 0,
    todayPomodoros: 0,
    lastSessionDate: null
  })
  const [tasks, setTasks] = useLocalStorage('pomodoro_tasks', [])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadSessions()
  }, [timeRange])

  const loadSessions = async () => {
    setLoading(true)
    const { startDate, endDate } = getDateRange()
    const user = getCurrentUser()
    
    if (user) {
      const cloudSessions = await getSessionsFromCloud(startDate, endDate)
      if (cloudSessions.length > 0) {
        setSessions(cloudSessions)
      } else {
        setSessions(getSessions(startDate, endDate))
      }
    } else {
      setSessions(getSessions(startDate, endDate))
    }
    setLoading(false)
  }

  const getDateRange = () => {
    const now = new Date()
    let startDate = new Date()
    
    switch (timeRange) {
      case 'day':
        startDate.setDate(now.getDate())
        startDate.setHours(0, 0, 0, 0)
        break
      case 'week':
        startDate.setDate(now.getDate() - 6)
        startDate.setHours(0, 0, 0, 0)
        break
      case 'month':
        startDate.setDate(now.getDate() - 29)
        startDate.setHours(0, 0, 0, 0)
        break
      case 'all':
        startDate = new Date(2020, 0, 1)
        break
      default:
        startDate.setDate(now.getDate() - 6)
    }
    
    return { startDate, endDate: now }
  }

  const chartData = useMemo(() => {
    const { startDate, endDate } = getDateRange()
    const data = []
    const dailyData = {}

    const current = new Date(startDate)
    while (current <= endDate) {
      const dateKey = current.toISOString().split('T')[0]
      dailyData[dateKey] = {
        date: dateKey,
        pomodoros: 0,
        minutes: 0,
        label: formatDateLabel(current)
      }
      current.setDate(current.getDate() + 1)
    }

    sessions.forEach(session => {
      const sessionDate = session.createdAt?.split('T')[0]
      if (sessionDate && dailyData[sessionDate]) {
        if (session.type === 'work') {
          dailyData[sessionDate].pomodoros += 1
          dailyData[sessionDate].minutes += session.duration || 0
        }
      }
    })

    return Object.values(dailyData)
  }, [sessions, timeRange])

  const formatDateLabel = (date) => {
    if (timeRange === 'day') {
      return '今天'
    }
    return `${date.getMonth() + 1}/${date.getDate()}`
  }

  const priorityData = useMemo(() => {
    const priorityCount = { high: 0, medium: 0, low: 0 }
    tasks.forEach(task => {
      const prio = task.priority || 'medium'
      priorityCount[prio]++
    })
    return [
      { name: '高优先级', value: priorityCount.high, color: '#ff6b6b' },
      { name: '中优先级', value: priorityCount.medium, color: '#ffd93d' },
      { name: '低优先级', value: priorityCount.low, color: '#a8e6cf' }
    ].filter(item => item.value > 0)
  }, [tasks])

  const statusData = useMemo(() => {
    const statusCount = { todo: 0, 'in-progress': 0, done: 0 }
    tasks.forEach(task => {
      const status = task.status || 'todo'
      statusCount[status]++
    })
    return [
      { name: '待办', value: statusCount.todo, color: '#ff6b6b' },
      { name: '进行中', value: statusCount['in-progress'], color: '#4ecdc4' },
      { name: '已完成', value: statusCount.done, color: '#95e1d3' }
    ].filter(item => item.value > 0)
  }, [tasks])

  const summaryStats = useMemo(() => {
    const workSessions = sessions.filter(s => s.type === 'work')
    const totalMinutes = workSessions.reduce((sum, s) => sum + (s.duration || 0), 0)
    const completedTasks = tasks.filter(t => t.status === 'done').length
    
    return {
      totalPomodoros: workSessions.length,
      totalMinutes,
      totalHours: (totalMinutes / 60).toFixed(1),
      completedTasks,
      completionRate: tasks.length > 0 ? Math.round((completedTasks / tasks.length) * 100) : 0,
      avgPomodorosPerDay: chartData.length > 0 
        ? (workSessions.length / chartData.length).toFixed(1) 
        : 0
    }
  }, [sessions, tasks, chartData])

  const hourlyDistribution = useMemo(() => {
    const hourlyCount = Array(24).fill(0)
    sessions.forEach(session => {
      if (session.type === 'work' && session.createdAt) {
        const hour = new Date(session.createdAt).getHours()
        hourlyCount[hour]++
      }
    })
    return hourlyCount.map((count, hour) => ({
      hour: `${hour}:00`,
      pomodoros: count
    }))
  }, [sessions])

  return (
    <div className="stats-page">
      <h1 className="stats-title">📊 统计分析</h1>

      <div className="time-range-selector">
        {['day', 'week', 'month', 'all'].map(range => (
          <button
            key={range}
            className={`range-btn ${timeRange === range ? 'active' : ''}`}
            onClick={() => setTimeRange(range)}
          >
            {range === 'day' ? '今天' : 
             range === 'week' ? '本周' : 
             range === 'month' ? '本月' : '全部'}
          </button>
        ))}
      </div>

      <div className="summary-cards">
        <div className="summary-card">
          <div className="summary-icon">🍅</div>
          <div className="summary-content">
            <span className="summary-value">{summaryStats.totalPomodoros}</span>
            <span className="summary-label">完成番茄</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">⏱️</div>
          <div className="summary-content">
            <span className="summary-value">{summaryStats.totalHours}</span>
            <span className="summary-label">专注小时</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">✅</div>
          <div className="summary-content">
            <span className="summary-value">{summaryStats.completedTasks}/{tasks.length}</span>
            <span className="summary-label">完成任务</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-icon">📈</div>
          <div className="summary-content">
            <span className="summary-value">{summaryStats.completionRate}%</span>
            <span className="summary-label">完成率</span>
          </div>
        </div>
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3 className="chart-title">番茄趋势</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorPomodoros" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ff6b6b" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#ff6b6b" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" stroke="#999" />
              <YAxis stroke="#999" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'white', 
                  border: 'none', 
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                }}
              />
              <Area 
                type="monotone" 
                dataKey="pomodoros" 
                stroke="#ff6b6b" 
                fillOpacity={1}
                fill="url(#colorPomodoros)"
                name="番茄数"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3 className="chart-title">专注时长</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" stroke="#999" />
              <YAxis stroke="#999" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'white', 
                  border: 'none', 
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                }}
                formatter={(value) => [`${value} 分钟`, '专注时长']}
              />
              <Bar 
                dataKey="minutes" 
                fill="#4ecdc4" 
                radius={[4, 4, 0, 0]}
                name="分钟"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3 className="chart-title">任务优先级分布</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={priorityData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {priorityData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3 className="chart-title">任务状态分布</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={statusData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {statusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card full-width">
          <h3 className="chart-title">活跃时段分布</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={hourlyDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="hour" stroke="#999" interval={2} />
              <YAxis stroke="#999" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'white', 
                  border: 'none', 
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                }}
              />
              <Bar 
                dataKey="pomodoros" 
                fill="#45b7d1" 
                radius={[4, 4, 0, 0]}
                name="番茄数"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner">加载中...</div>
        </div>
      )}
    </div>
  )
}

export default Stats
