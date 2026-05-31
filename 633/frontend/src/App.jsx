import { useState, useEffect } from 'react'
import axios from 'axios'
import QueryForm from './components/QueryForm'
import StatusPanel from './components/StatusPanel'
import DrillPanel from './components/DrillPanel'
import ResourceGroupPanel from './components/ResourceGroupPanel'

function App() {
  const [activeTab, setActiveTab] = useState('query')
  const [status, setStatus] = useState(null)
  const [history, setHistory] = useState([])
  const [queryResult, setQueryResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const fetchStatus = async () => {
    try {
      const res = await axios.get('/api/status')
      setStatus(res.data)
    } catch (err) {
      console.error('Failed to fetch status:', err)
    }
  }

  const fetchHistory = async () => {
    try {
      const res = await axios.get('/api/history')
      setHistory(res.data)
    } catch (err) {
      console.error('Failed to fetch history:', err)
    }
  }

  const executeQuery = async (queryData) => {
    setLoading(true)
    setQueryResult(null)
    try {
      const res = await axios.post('/api/query', queryData)
      setQueryResult(res.data)
      fetchHistory()
      fetchStatus()
    } catch (err) {
      setQueryResult({
        status: 'error',
        error: err.response?.data?.message || err.message
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    fetchHistory()

    const interval = setInterval(() => {
      fetchStatus()
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="container">
      <header className="header">
        <h1>🚀 ClickHouse 查询限流工具</h1>
        <p>基于查询复杂度的动态限流系统，支持熔断降级、用户级限流和查询优先级</p>
      </header>

      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'query' ? 'active' : ''}`}
          onClick={() => setActiveTab('query')}
        >
          查询执行
        </button>
        <button 
          className={`tab ${activeTab === 'status' ? 'active' : ''}`}
          onClick={() => setActiveTab('status')}
        >
          系统状态
        </button>
        <button 
          className={`tab ${activeTab === 'resource_groups' ? 'active' : ''}`}
          onClick={() => setActiveTab('resource_groups')}
        >
          资源组管理
        </button>
        <button 
          className={`tab ${activeTab === 'drill' ? 'active' : ''}`}
          onClick={() => setActiveTab('drill')}
        >
          限流演练
        </button>
        <button 
          className={`tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          查询历史
        </button>
      </div>

      <div className="grid">
        {activeTab === 'query' && (
          <>
            <div className="card card-full">
              <h2>📝 SQL 查询</h2>
              <QueryForm onSubmit={executeQuery} loading={loading} />
              {queryResult && (
                <div className="result-section">
                  <ResultDisplay result={queryResult} />
                </div>
              )}
            </div>
          </>
        )}

        {activeTab === 'status' && (
          <div className="card card-full">
            <h2>📊 系统状态监控</h2>
            <StatusPanel status={status} />
          </div>
        )}

        {activeTab === 'resource_groups' && (
          <div className="card card-full">
            <h2>👥 资源组管理</h2>
            <ResourceGroupPanel status={status} />
          </div>
        )}

        {activeTab === 'drill' && (
          <div className="card card-full">
            <h2>🧪 限流演练</h2>
            <DrillPanel />
          </div>
        )}

        {activeTab === 'history' && (
          <div className="card card-full">
            <h2>📋 查询历史记录</h2>
            <QueryHistory history={history} />
          </div>
        )}
      </div>
    </div>
  )
}

export default App
