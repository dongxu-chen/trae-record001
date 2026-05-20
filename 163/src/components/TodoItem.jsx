import { useState, useEffect } from 'react'

function TodoItem({ todo, onToggle, onDelete, onUpdate, tags, getTagColor, getTagName }) {
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState(todo.text)
  const [editPriority, setEditPriority] = useState(todo.priority)
  const [editTag, setEditTag] = useState(todo.tag || '')

  useEffect(() => {
    if (!isEditing) {
      setEditText(todo.text)
      setEditPriority(todo.priority)
      setEditTag(todo.tag || '')
    }
  }, [todo.text, todo.priority, todo.tag, isEditing])

  const handleSave = () => {
    if (editText.trim()) {
      onUpdate(todo.id, editText.trim(), editPriority, editTag)
      setIsEditing(false)
    }
  }

  const handleCancel = () => {
    setEditText(todo.text)
    setEditPriority(todo.priority)
    setEditTag(todo.tag || '')
    setIsEditing(false)
  }

  const getPriorityClass = () => {
    return `priority-${todo.priority}`
  }

  const getPriorityLabel = () => {
    const labels = { high: '高', medium: '中', low: '低' }
    return labels[todo.priority]
  }

  return (
    <div className={`todo-item ${todo.completed ? 'completed' : ''}`}>
      <input
        type="checkbox"
        checked={todo.completed}
        onChange={() => onToggle(todo.id)}
        className="checkbox"
      />
      
      {isEditing ? (
        <div className="edit-form">
          <input
            type="text"
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSave()}
            autoFocus
            className="edit-input"
          />
          <select
            value={editPriority}
            onChange={(e) => setEditPriority(e.target.value)}
            className="edit-priority"
          >
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
          </select>
          <select
            value={editTag}
            onChange={(e) => setEditTag(e.target.value)}
            className="edit-tag"
          >
            <option value="">无标签</option>
            {tags.map(tag => (
              <option key={tag.id} value={tag.id}>{tag.name}</option>
            ))}
          </select>
          <button onClick={handleSave} className="save-btn">保存</button>
          <button onClick={handleCancel} className="cancel-btn">取消</button>
        </div>
      ) : (
        <>
          <div className="todo-content">
            <span className={`todo-text ${getPriorityClass()}`}>
              {todo.text}
            </span>
            {todo.tag && (
              <span 
                className="tag-badge" 
                style={{ backgroundColor: getTagColor(todo.tag) }}
              >
                {getTagName(todo.tag)}
              </span>
            )}
          </div>
          <span className={`priority-badge ${getPriorityClass()}`}>
            {getPriorityLabel()}
          </span>
          <div className="actions">
            <button
              onClick={() => setIsEditing(true)}
              className="edit-btn"
            >
              编辑
            </button>
            <button
              onClick={() => onDelete(todo.id)}
              className="delete-btn"
            >
              删除
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default TodoItem
