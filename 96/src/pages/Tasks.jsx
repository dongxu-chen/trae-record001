import { useState, useCallback } from 'react'
import useLocalStorage from '../hooks/useLocalStorage'

const TASK_STATUS = {
  TODO: { key: 'todo', label: '待办', color: '#ff6b6b' },
  IN_PROGRESS: { key: 'in-progress', label: '进行中', color: '#4ecdc4' },
  DONE: { key: 'done', label: '已完成', color: '#95e1d3' }
}

const PRIORITIES = {
  LOW: { key: 'low', label: '低', color: '#a8e6cf' },
  MEDIUM: { key: 'medium', label: '中', color: '#ffd93d' },
  HIGH: { key: 'high', label: '高', color: '#ff6b6b' }
}

function Tasks() {
  const [tasks, setTasks] = useLocalStorage('pomodoro_tasks', [])
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [newTaskPriority, setNewTaskPriority] = useState('medium')
  const [editingTaskId, setEditingTaskId] = useState(null)
  const [editTitle, setEditTitle] = useState('')
  const [draggedTask, setDraggedTask] = useState(null)
  const [dragOverColumn, setDragOverColumn] = useState(null)

  const generateId = () => Date.now().toString(36) + Math.random().toString(36).substr(2)

  const handleAddTask = () => {
    if (!newTaskTitle.trim()) return
    
    const newTask = {
      id: generateId(),
      title: newTaskTitle.trim(),
      status: TASK_STATUS.TODO.key,
      priority: newTaskPriority,
      pomodoros: 0,
      estimatedPomodoros: 1,
      createdAt: new Date().toISOString(),
      completedAt: null
    }

    setTasks([...tasks, newTask])
    setNewTaskTitle('')
    setNewTaskPriority('medium')
  }

  const handleDeleteTask = (taskId) => {
    setTasks(tasks.filter(task => task.id !== taskId))
  }

  const handleStatusChange = (taskId, newStatus) => {
    setTasks(tasks.map(task => {
      if (task.id === taskId) {
        return {
          ...task,
          status: newStatus,
          completedAt: newStatus === TASK_STATUS.DONE.key ? new Date().toISOString() : null
        }
      }
      return task
    }))
  }

  const handlePriorityChange = (taskId, newPriority) => {
    setTasks(tasks.map(task => {
      if (task.id === taskId) {
        return { ...task, priority: newPriority }
      }
      return task
    }))
  }

  const handleEstimatedChange = (taskId, value) => {
    const estimated = Math.max(1, parseInt(value) || 1)
    setTasks(tasks.map(task => {
      if (task.id === taskId) {
        return { ...task, estimatedPomodoros: estimated }
      }
      return task
    }))
  }

  const handleIncrementPomodoro = (taskId) => {
    setTasks(tasks.map(task => {
      if (task.id === taskId) {
        return { ...task, pomodoros: task.pomodoros + 1 }
      }
      return task
    }))
  }

  const handleEditStart = (task) => {
    setEditingTaskId(task.id)
    setEditTitle(task.title)
  }

  const handleEditSave = (taskId) => {
    if (!editTitle.trim()) {
      setEditingTaskId(null)
      return
    }
    
    setTasks(tasks.map(task => {
      if (task.id === taskId) {
        return { ...task, title: editTitle.trim() }
      }
      return task
    }))
    setEditingTaskId(null)
  }

  const handleKeyPress = (e, action, ...args) => {
    if (e.key === 'Enter') {
      action(...args)
    } else if (e.key === 'Escape') {
      setEditingTaskId(null)
    }
  }

  const getTasksByStatus = (statusKey) => {
    return tasks.filter(task => task.status === statusKey)
  }

  const getPriorityColor = (priority) => {
    return PRIORITIES[priority.toUpperCase()]?.color || PRIORITIES.MEDIUM.color
  }

  const handleDragStart = useCallback((e, task) => {
    setDraggedTask(task)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', task.id)
  }, [])

  const handleDragEnd = useCallback(() => {
    setDraggedTask(null)
    setDragOverColumn(null)
  }, [])

  const handleDragOver = useCallback((e, statusKey) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverColumn(statusKey)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragOverColumn(null)
  }, [])

  const handleDrop = useCallback((e, targetStatus) => {
    e.preventDefault()
    setDragOverColumn(null)
    
    if (!draggedTask) return

    setTasks(prevTasks => {
      const updatedTasks = prevTasks.map(task => {
        if (task.id === draggedTask.id) {
          return {
            ...task,
            status: targetStatus,
            completedAt: targetStatus === TASK_STATUS.DONE.key 
              ? new Date().toISOString() 
              : (task.status === TASK_STATUS.DONE.key ? null : task.completedAt)
          }
        }
        return task
      })
      return updatedTasks
    })

    setDraggedTask(null)
  }, [draggedTask, setTasks])

  const TaskCard = ({ task }) => {
    const isEditing = editingTaskId === task.id
    const isDragging = draggedTask?.id === task.id

    return (
      <div 
        className={`task-card ${isDragging ? 'dragging' : ''}`} 
        style={{ borderLeftColor: getPriorityColor(task.priority) }}
        draggable={!isEditing}
        onDragStart={(e) => handleDragStart(e, task)}
        onDragEnd={handleDragEnd}
      >
        {isEditing ? (
          <div className="task-edit">
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onKeyDown={(e) => handleKeyPress(e, handleEditSave, task.id)}
              onBlur={() => handleEditSave(task.id)}
              autoFocus
              className="task-edit-input"
            />
          </div>
        ) : (
          <>
            <div className="task-header">
              <h4 className="task-title" onClick={() => handleEditStart(task)}>
                {task.title}
              </h4>
              <button className="task-delete" onClick={() => handleDeleteTask(task.id)}>
                ×
              </button>
            </div>

            <div className="task-info">
              <select
                value={task.priority}
                onChange={(e) => handlePriorityChange(task.id, e.target.value)}
                className="task-priority"
              >
                {Object.values(PRIORITIES).map(p => (
                  <option key={p.key} value={p.key}>{p.label}</option>
                ))}
              </select>
              
              <div className="task-pomodoros">
                <span>🍅 {task.pomodoros}/{task.estimatedPomodoros}</span>
                <button 
                  className="pomodoro-increment"
                  onClick={() => handleIncrementPomodoro(task.id)}
                >
                  +
                </button>
                <input
                  type="number"
                  value={task.estimatedPomodoros}
                  onChange={(e) => handleEstimatedChange(task.id, e.target.value)}
                  min="1"
                  className="pomodoro-estimate"
                />
              </div>
            </div>

            <div className="task-actions">
              {Object.values(TASK_STATUS).filter(s => s.key !== task.status).map(status => (
                <button
                  key={status.key}
                  className="status-btn"
                  style={{ backgroundColor: status.color }}
                  onClick={() => handleStatusChange(task.id, status.key)}
                >
                  移至 {status.label}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    )
  }

  const Column = ({ status }) => {
    const columnTasks = getTasksByStatus(status.key)
    const isDragOver = dragOverColumn === status.key

    return (
      <div 
        className={`task-column ${isDragOver ? 'drag-over' : ''}`}
        onDragOver={(e) => handleDragOver(e, status.key)}
        onDragLeave={handleDragLeave}
        onDrop={(e) => handleDrop(e, status.key)}
      >
        <div className="column-header" style={{ backgroundColor: status.color }}>
          <h3>{status.label}</h3>
          <span className="task-count">{columnTasks.length}</span>
        </div>

        <div className="task-list">
          {columnTasks.map(task => (
            <TaskCard key={task.id} task={task} />
          ))}
          {columnTasks.length === 0 && (
            <div className="empty-column">
              {isDragOver ? '释放以放置任务' : '暂无任务'}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="tasks-page">
      <h1 className="tasks-title">📋 任务看板</h1>

      <div className="add-task-form">
        <input
          type="text"
          value={newTaskTitle}
          onChange={(e) => setNewTaskTitle(e.target.value)}
          onKeyDown={(e) => handleKeyPress(e, handleAddTask)}
          placeholder="输入新任务..."
          className="task-input"
        />
        <select
          value={newTaskPriority}
          onChange={(e) => setNewTaskPriority(e.target.value)}
          className="priority-select"
        >
          {Object.values(PRIORITIES).map(p => (
            <option key={p.key} value={p.key}>{p.label}优先级</option>
          ))}
        </select>
        <button className="add-btn" onClick={handleAddTask}>
          添加任务
        </button>
      </div>

      <div className="board-container">
        {Object.values(TASK_STATUS).map(status => (
          <Column key={status.key} status={status} />
        ))}
      </div>

      <div className="board-stats">
        <div className="stat-card">
          <span className="stat-label">总任务数</span>
          <span className="stat-value">{tasks.length}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">进行中</span>
          <span className="stat-value">{getTasksByStatus('in-progress').length}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">已完成</span>
          <span className="stat-value">{getTasksByStatus('done').length}</span>
        </div>
      </div>
    </div>
  )
}

export default Tasks
