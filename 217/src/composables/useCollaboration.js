import { ref } from 'vue'

const collaboratorColors = [
  '#FF6B6B',
  '#4ECDC4',
  '#45B7D1',
  '#96CEB4',
  '#FFEAA7',
  '#DDA0DD',
  '#98D8C8',
  '#F7DC6F'
]

const collaboratorNames = [
  '张三',
  '李四',
  '王五',
  '赵六',
  '钱七',
  '孙八'
]

export function useCollaboration() {
  const isConnected = ref(false)
  const localUserId = ref('user-' + Math.random().toString(36).substr(2, 9))
  const localUserName = ref('我')
  const remoteCollaborators = ref([])
  const messageHandlers = ref({})

  let mockInterval = null
  let messageQueue = []

  const connect = (canvas, onMessage) => {
    isConnected.value = true
    
    const mockCollaborators = [
      { id: 'user-' + Math.random().toString(36).substr(2, 9), name: '张三', color: '#FF6B6B' },
      { id: 'user-' + Math.random().toString(36).substr(2, 9), name: '李四', color: '#4ECDC4' }
    ]
    
    mockCollaborators.forEach(c => {
      remoteCollaborators.value.push({
        ...c,
        x: Math.random() * 600 + 100,
        y: Math.random() * 400 + 100
      })
    })

    if (onMessage) {
      mockCollaborators.forEach(c => {
        onMessage({
          type: 'COLLABORATOR_JOIN',
          payload: c
        })
      })
    }

    mockInterval = setInterval(() => {
      if (messageQueue.length > 0) {
        const msg = messageQueue.shift()
        if (onMessage) {
          onMessage(msg)
        }
      }

      remoteCollaborators.value.forEach(c => {
        c.x += (Math.random() - 0.5) * 30
        c.y += (Math.random() - 0.5) * 30
        c.x = Math.max(50, Math.min(1200, c.x))
        c.y = Math.max(50, Math.min(600, c.y))

        if (onMessage) {
          onMessage({
            type: 'CURSOR_MOVE',
            payload: { userId: c.id, x: c.x, y: c.y }
          })
        }
      })
    }, 200)

    return Promise.resolve()
  }

  const disconnect = () => {
    isConnected.value = false
    if (mockInterval) {
      clearInterval(mockInterval)
      mockInterval = null
    }
    remoteCollaborators.value = []
  }

  const sendMessage = (type, payload) => {
    const message = {
      type,
      payload,
      senderId: localUserId.value,
      timestamp: Date.now()
    }

    if (type === 'NODE_MOVE') {
      setTimeout(() => {
        messageQueue.push({
          type: 'REMOTE_NODE_MOVE',
          payload: { ...payload, userId: 'simulated' }
        })
      }, 500)
    }
  }

  const broadcastCursor = (x, y) => {
    sendMessage('CURSOR_MOVE', { x, y })
  }

  const broadcastNodeAdd = (node) => {
    sendMessage('NODE_ADD', node)
  }

  const broadcastNodeMove = (nodeId, x, y) => {
    sendMessage('NODE_MOVE', { nodeId, x, y })
  }

  const broadcastNodeUpdate = (nodeId, updates) => {
    sendMessage('NODE_UPDATE', { nodeId, updates })
  }

  const broadcastNodeDelete = (nodeId) => {
    sendMessage('NODE_DELETE', { nodeId })
  }

  const broadcastConnectionAdd = (connection) => {
    sendMessage('CONNECTION_ADD', connection)
  }

  const broadcastConnectionDelete = (connectionId) => {
    sendMessage('CONNECTION_DELETE', { connectionId })
  }

  const broadcastCommentAdd = (comment) => {
    sendMessage('COMMENT_ADD', comment)
  }

  const broadcastCommentReply = (commentId, reply) => {
    sendMessage('COMMENT_REPLY', { commentId, reply })
  }

  const broadcastCommentResolve = (commentId, resolved) => {
    sendMessage('COMMENT_RESOLVE', { commentId, resolved })
  }

  return {
    isConnected,
    localUserId,
    localUserName,
    remoteCollaborators,
    connect,
    disconnect,
    sendMessage,
    broadcastCursor,
    broadcastNodeAdd,
    broadcastNodeMove,
    broadcastNodeUpdate,
    broadcastNodeDelete,
    broadcastConnectionAdd,
    broadcastConnectionDelete,
    broadcastCommentAdd,
    broadcastCommentReply,
    broadcastCommentResolve
  }
}
