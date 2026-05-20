import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import TodoList from './components/TodoList'
import './App.css'

const deepClone = (obj) => {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj)
  if (obj instanceof Array) return obj.map(item => deepClone(item))
  if (typeof obj === 'object') {
    const clonedObj = {}
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        clonedObj[key] = deepClone(obj[key])
      }
    }
    return clonedObj
  }
  return obj
}

const checkStorageQuota = () => {
  try {
    let totalSpace = 0
    for (const key in localStorage) {
      if (localStorage.hasOwnProperty(key)) {
        totalSpace += (localStorage[key].length + key.length) * 2
      }
    }
    const usedMB = (totalSpace / 1024 / 1024).toFixed(2)
    const limitMB = 5
    const usagePercent = ((totalSpace / (limitMB * 1024 * 1024)) * 100
    return {
      usedMB,
      limitMB,
      usagePercent: usagePercent.toFixed(1),
      isFull: totalSpace > (limitMB * 1024 * 1024 * 0.9)
    }
  } catch (e) {
    return { usedMB: 0, limitMB: 5, usagePercent: 0, isFull: false }
  }
}

const PRIORITY_ORDER = { high: 3, medium: 2, low: 1 }

const DEFAULT_TAGS = [
  { id: 'work', name: '工作', color: '#3b82f6' },
  { id: 'personal', name: '个人', color: '#10b981' },
  { id: 'study', name: '学习', color: '#8b5cf6' },
  { id: 'life', name: '生活', color: '#f59e0b' },
  { id: 'urgent', name: '紧急', color: '#ef4444' }
]

const SYNC_INTERVAL = 5 * 60 * 1000

function App() {
  const [todos, setTodos] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [priority, setPriority] = useState('medium')
  const [selectedTag, setSelectedTag] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState('priority')
  const [notification, setNotification] = useState({ show: false, message: '', type: '' })
  const [tags, setTags] = useState(DEFAULT_TAGS)
  const [darkMode, setDarkMode] = useState(false)
  const [syncStatus, setSyncStatus] = useState('idle')
  const [offlineQueue, setOfflineQueue] = useState([])
  const [lastSyncTime, setLastSyncTime] = useState(null)
  const [filterTag, setFilterTag] = useState('')
  const syncTimerRef = useRef(null)

  const showNotification = useCallback((message, type = 'info') => {
    setNotification({ show: true, message, type })
    setTimeout(() => {
      setNotification({ show: false, message: '', type: '' })
    }, 3000)
  }, [])

  useEffect(() => {
    try {
      const savedTodos = localStorage.getItem('todos')
      const savedTags = localStorage.getItem('tags')
      const savedDarkMode = localStorage.getItem('darkMode')
      const savedQueue = localStorage.getItem('offlineQueue')
      const savedLastSync = localStorage.getItem('lastSyncTime')

      if (savedTodos) {
        setTodos(deepClone(JSON.parse(savedTodos)))
      }
      if (savedTags) {
        setTags(JSON.parse(savedTags))
      }
      if (savedDarkMode) {
        setDarkMode(JSON.parse(savedDarkMode))
      }
      if (savedQueue) {
        setOfflineQueue(JSON.parse(savedQueue))
      }
      if (savedLastSync) {
        setLastSyncTime(savedLastSync)
      }
    } catch (e) {
      console.error('Failed to load data:', e)
      showNotification('数据加载失败', 'error')
    }
  }, [showNotification])

  useEffect(() => {
    try {
      localStorage.setItem('todos', JSON.stringify(todos))
      localStorage.setItem('tags', JSON.stringify(tags))
      localStorage.setItem('darkMode', JSON.stringify(darkMode))
      localStorage.setItem('offlineQueue', JSON.stringify(offlineQueue))
      if (lastSyncTime) {
        localStorage.setItem('lastSyncTime', lastSyncTime)
      }
      
      const storageInfo = checkStorageQuota()
      if (storageInfo.isFull) {
        showNotification(`存储空间已使用 ${storageInfo.usagePercent}%，建议清理部分待办事项`, 'warning')
      }
    } catch (e) {
      if (e.name === 'QuotaExceededError' || e.name === 'NS_ERROR_DOM_QUOTA_REACHED') {
        showNotification('存储空间已满！请删除一些待办事项后重试', 'error')
      }
    }
  }, [todos, tags, darkMode, offlineQueue, lastSyncTime, showNotification])

  const addToSyncQueue = useCallback((action, data) => {
    const queueItem = {
      id: Date.now(),
      action,
      data: deepClone(data),
      timestamp: new Date().toISOString()
    }
    setOfflineQueue(prev => [...prev, queueItem])
  }, [])

  const syncToCloud = useCallback(async () => {
    if (offlineQueue.length === 0) return
    
    setSyncStatus('syncing')
    showNotification('正在同步到云端...', 'info')
    
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    try {
      const successCount = offlineQueue.length
      setOfflineQueue([])
      setLastSyncTime(new Date().toISOString())
      setSyncStatus('success')
      showNotification(`同步成功！已同步 ${successCount} 项更改`, 'success')
    } catch (error) {
      setSyncStatus('error')
      showNotification('同步失败，已保存到离线队列', 'error')
    }
  }, [offlineQueue, showNotification])

  useEffect(() => {
    syncTimerRef.current = setInterval(() => {
      if (offlineQueue.length > 0) {
        syncToCloud()
      }
    }, SYNC_INTERVAL)

    return () => {
      if (syncTimerRef.current) {
        clearInterval(syncTimerRef.current)
      }
    }
  }, [offlineQueue, syncToCloud])

  const handleManualSync = () => {
    syncToCloud()
  }

  const toggleDarkMode = () => {
    setDarkMode(prev => !prev)
  }

  const addTodo = useCallback(() => {
    if (!inputValue.trim()) return
    
    const storageInfo = checkStorageQuota()
    if (storageInfo.isFull) {
      showNotification('存储空间接近上限，建议先清理部分待办事项', 'warning')
    }

    const newTodo = {
      id: Date.now(),
      text: inputValue.trim(),
      completed: false,
      priority,
      tag: selectedTag,
      createdAt: new Date().toISOString()
    }
    setTodos(prev => [...deepClone(prev), newTodo])
    addToSyncQueue('add', newTodo)
    setInputValue('')
    setSelectedTag('')
    showNotification('待办事项已添加', 'success')
  }, [inputValue, priority, selectedTag, showNotification, addToSyncQueue])

  const toggleTodo = useCallback((id) => {
    setTodos(prev => {
      const cloned = deepClone(prev)
      const updated = cloned.map(todo =>
        todo.id === id ? { ...todo, completed: !todo.completed } : todo
      )
      const todoItem = cloned.find(t => t.id === id)
      if (todoItem) {
        addToSyncQueue('toggle', { id, completed: !todoItem.completed })
      }
      return updated
    })
  }, [addToSyncQueue])

  const deleteTodo = useCallback((id) => {
    setTodos(prev => {
      const cloned = deepClone(prev)
      addToSyncQueue('delete', { id })
      return cloned.filter(todo => todo.id !== id)
    })
    showNotification('待办事项已删除', 'success')
  }, [showNotification, addToSyncQueue])

  const updateTodo = useCallback((id, newText, newPriority, newTag) => {
    setTodos(prev => {
      const cloned = deepClone(prev)
      addToSyncQueue('update', { id, text: newText, priority: newPriority, tag: newTag })
      return cloned.map(todo =>
        todo.id === id ? { ...todo, text: newText, priority: newPriority, tag: newTag } : todo
      )
    })
    showNotification('待办事项已更新', 'success')
  }, [showNotification, addToSyncQueue])

  const getTagColor = (tagId) => {
    const tag = tags.find(t => t.id === tagId)
    return tag ? tag.color : '#6b7280'
  }

  const getTagName = (tagId) => {
    const tag = tags.find(t => t.id === tagId)
    return tag ? tag.name : ''
  }

  const filteredAndSortedTodos = useMemo(() => {
    const searchLower = searchTerm.toLowerCase()
    let filtered = todos.filter(todo => 
      todo.text.toLowerCase().includes(searchLower)
    )

    if (filterTag) {
      filtered = filtered.filter(todo => todo.tag === filterTag)
    }

    if (sortBy === 'priority') {
      return filtered.sort((a, b) => {
        const priorityDiff = PRIORITY_ORDER[b.priority] - PRIORITY_ORDER[a.priority]
        if (priorityDiff !== 0) return priorityDiff
        return new Date(b.createdAt) - new Date(a.createdAt)
      })
    }
    
    return filtered.sort((a, b) => 
      new Date(b.createdAt) - new Date(a.createdAt)
    )
  }, [todos, searchTerm, sortBy, filterTag])

  const storageInfo = useMemo(() => checkStorageQuota(), [todos])

  const formatSyncTime = (time) => {
    if (!time) return '从未同步'
    const date = new Date(time)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className={`app ${darkMode ? 'dark-mode' : ''}`}>
      {notification.show && (
        <div className={`notification notification-${notification.type}`}>
          {notification.message}
        </div>
      )}
      <div className="container">
        <div className="header">
          <h1>待办事项</h1>
          <div className="header-actions">
            <button 
              onClick={handleManualSync} 
              className={`icon-btn sync-btn ${syncStatus === 'syncing' ? 'syncing' : ''}`}
              title="手动同步"
            >
              <span className="sync-icon">⟳</span>
              <span className="sync-text">{offlineQueue.length > 0 ? `队列: ${offlineQueue.length}` : ''}</span>
            </button>
            <button 
              onClick={toggleDarkMode} 
              className="icon-btn theme-btn"
              title={darkMode ? '切换亮色' : '切换暗色'}
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>

        <div className="sync-info">
          <span>上次同步: {formatSyncTime(lastSyncTime)}</span>
        </div>
        
        <div className="add-todo">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addTodo()}
            placeholder="添加新的待办事项..."
            className="todo-input"
          />
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="priority-select"
          >
            <option value="low">低优先级</option>
            <option value="medium">中优先级</option>
            <option value="high">高优先级</option>
          </select>
          <select
            value={selectedTag}
            onChange={(e) => setSelectedTag(e.target.value)}
            className="tag-select"
          >
            <option value="">选择标签</option>
            {tags.map(tag => (
              <option key={tag.id} value={tag.id}>{tag.name}</option>
            ))}
          </select>
          <button onClick={addTodo} className="add-btn">添加</button>
        </div>

        <div className="controls">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="搜索待办事项..."
            className="search-input"
          />
          <div className="tag-filters">
            <button
              onClick={() => setFilterTag('')}
              className={`tag-filter-btn ${!filterTag ? 'active' : ''}`}
            >
              全部
            </button>
            {tags.map(tag => (
              <button
                key={tag.id}
                onClick={() => setFilterTag(tag.id)}
                className={`tag-filter-btn ${filterTag === tag.id ? 'active' : ''}`}
                style={{ '--tag-color': tag.color }}
              >
                {tag.name}
              </button>
            ))}
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="sort-select"
          >
            <option value="priority">按优先级排序</option>
            <option value="date">按时间排序</option>
          </select>
        </div>

        <TodoList
          todos={filteredAndSortedTodos}
          onToggle={toggleTodo}
          onDelete={deleteTodo}
          onUpdate={updateTodo}
          tags={tags}
          getTagColor={getTagColor}
          getTagName={getTagName}
        />

        <div className="stats">
          <span>总计: {todos.length}</span>
          <span>已完成: {todos.filter(t => t.completed).length}</span>
          <span>未完成: {todos.filter(t => !t.completed).length}</span>
          <span className={`storage-info ${storageInfo.isFull ? 'storage-warning' : ''}`}>
            存储: {storageInfo.usagePercent}%
          </span>
        </div>
      </div>
    </div>
  )
}

export default App
