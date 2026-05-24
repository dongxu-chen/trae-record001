import React, { useEffect, useRef } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { startCollaboration, stopCollaboration, updateCursor } from '../store/dashboardSlice'

export default function CollaborationPanel() {
  const dispatch = useDispatch()
  const collaboration = useSelector((state) => state.dashboard.collaboration)
  const currentUser = useSelector((state) => state.dashboard.currentUser)
  const canvasRef = useRef(null)

  useEffect(() => {
    if (!collaboration.isCollaborating) return

    const handleMouseMove = (e) => {
      const canvas = document.getElementById('dashboard-content')
      if (canvas) {
        const rect = canvas.getBoundingClientRect()
        dispatch(updateCursor({
          userId: currentUser.id,
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
          componentId: null,
        }))
      }
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [collaboration.isCollaborating, currentUser.id, dispatch])

  useEffect(() => {
    if (!collaboration.isCollaborating) return

    const interval = setInterval(() => {
      collaboration.users.forEach(user => {
        if (user.id !== currentUser.id && Math.random() > 0.7) {
          const canvas = document.getElementById('dashboard-content')
          if (canvas) {
            const rect = canvas.getBoundingClientRect()
            dispatch(updateCursor({
              userId: user.id,
              x: Math.random() * rect.width,
              y: Math.random() * rect.height,
              componentId: null,
            }))
          }
        }
      })
    }, 3000)

    return () => clearInterval(interval)
  }, [collaboration.isCollaborating, collaboration.users, currentUser.id, dispatch])

  const handleToggleCollaboration = () => {
    if (collaboration.isCollaborating) {
      dispatch(stopCollaboration())
    } else {
      dispatch(startCollaboration())
    }
  }

  return (
    <div className="collaboration-panel">
      <button
        className={`collab-toggle ${collaboration.isCollaborating ? 'active' : ''}`}
        onClick={handleToggleCollaboration}
      >
        {collaboration.isCollaborating ? '🔴 协作中' : '👥 开始协作'}
      </button>

      {collaboration.isCollaborating && (
        <div className="collab-users">
          <span className="collab-label">在线用户:</span>
          <div className="user-avatars">
            {collaboration.users.map(user => (
              <div
                key={user.id}
                className={`user-avatar ${user.id === currentUser.id ? 'current' : ''}`}
                style={{ borderColor: user.color }}
                title={`${user.name}${user.id === currentUser.id ? ' (你)' : ''}`}
              >
                {user.avatar}
              </div>
            ))}
          </div>
        </div>
      )}

      {collaboration.isCollaborating && <CursorLayer users={collaboration.users} cursors={collaboration.cursors} />}
    </div>
  )
}

function CursorLayer({ users, cursors }) {
  const canvas = document.getElementById('dashboard-content')
  if (!canvas) return null

  return (
    <div className="cursor-layer">
      {Object.entries(cursors).map(([userId, cursor]) => {
        const user = users.find(u => u.id === userId)
        if (!user) return null
        const timeDiff = Date.now() - cursor.updatedAt
        if (timeDiff > 10000) return null

        return (
          <div
            key={userId}
            className="remote-cursor"
            style={{
              left: cursor.x,
              top: cursor.y,
              '--cursor-color': user.color,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M2 2 L18 8 L12 12 L10 18 Z"
                fill={user.color}
                stroke="white"
                strokeWidth="1"
              />
            </svg>
            <span
              className="cursor-label"
              style={{ backgroundColor: user.color }}
            >
              {user.name}
            </span>
          </div>
        )
      })}
    </div>
  )
}
