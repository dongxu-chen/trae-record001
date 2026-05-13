const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:3001/api'
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:3002'

const RETRYABLE_STATUS_CODES = new Set([408, 429, 500, 502, 503, 504])
const IDEMPOTENT_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function shouldRetry(method, statusCode, attempt, maxAttempts) {
  if (attempt >= maxAttempts) {
    return false
  }
  if (!IDEMPOTENT_METHODS.has(method)) {
    return false
  }
  return RETRYABLE_STATUS_CODES.has(statusCode) || statusCode === 0
}

async function fetchWithRetry(url, options = {}, maxAttempts = 3) {
  let lastError = null

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const method = (options.method || 'GET').toUpperCase()
      const res = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      })

      if (!res.ok) {
        const statusCode = res.status
        if (shouldRetry(method, statusCode, attempt, maxAttempts)) {
          const delay = Math.min(100 * Math.pow(2, attempt), 2000)
          await wait(delay)
          lastError = new Error(`API call failed: ${statusCode} ${res.statusText}`)
          continue
        }
        throw new Error(`API call failed: ${statusCode} ${res.statusText}`)
      }

      return res.json()
    } catch (err) {
      const method = (options.method || 'GET').toUpperCase()
      if (shouldRetry(method, 0, attempt, maxAttempts)) {
        const delay = Math.min(100 * Math.pow(2, attempt), 2000)
        await wait(delay)
        lastError = err
        continue
      }
      throw err
    }
  }

  throw lastError || new Error('Request failed')
}

function fetchAPI(path, options = {}) {
  const url = `${API_BASE_URL}${path}`
  return fetchWithRetry(url, options, 3)
}

export async function getPosts() {
  return fetchAPI('/posts', { method: 'GET' })
}

export async function getPost(id) {
  return fetchAPI(`/posts/${id}`, { method: 'GET' })
}

export async function getComments(postId) {
  return fetchAPI(`/posts/${postId}/comments`, { method: 'GET' })
}

export async function createComment(postId, data) {
  return fetchAPI(`/posts/${postId}/comments`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

let globalWs = null
let globalWsListeners = new Map()
let reconnectTimer = null
let globalSubscriptions = new Set()

function createWsClient({ onOpen, onMessage, onClose, onError } = {}) {
  let ws = null
  let reconnectAttempts = 0
  const maxReconnectDelay = 10000
  const listeners = new Map()

  function connect() {
    if (ws && ws.readyState === 1) {
      return
    }
    if (ws) {
      ws.removeEventListener('open', handleOpen)
      ws.removeEventListener('message', handleMessage)
      ws.removeEventListener('close', handleClose)
      ws.removeEventListener('error', handleError)
    }

    ws = new WebSocket(WS_BASE_URL)

    ws.addEventListener('open', handleOpen)
    ws.addEventListener('message', handleMessage)
    ws.addEventListener('close', handleClose)
    ws.addEventListener('error', handleError)
  }

  function handleOpen() {
    reconnectAttempts = 0
    globalSubscriptions.forEach((postId) => {
      sendSafe({ type: 'subscribe', postId })
    })
    if (onOpen) onOpen()
  }

  function handleMessage(event) {
    let data
    try {
      data = JSON.parse(event.data)
    } catch (err) {
      return
    }
    if (onMessage) onMessage(data)
    listeners.forEach((handler) => {
      try {
        handler(data)
      } catch (err) {
        console.warn('WS listener error:', err)
      }
    })
  }

  function handleClose() {
    if (onClose) onClose()
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), maxReconnectDelay)
    reconnectAttempts += 1
    setTimeout(() => connect(), delay)
  }

  function handleError(err) {
    if (onError) onError(err)
  }

  function sendSafe(payload) {
    if (!ws || ws.readyState !== 1) {
      return false
    }
    try {
      ws.send(JSON.stringify(payload))
      return true
    } catch (err) {
      return false
    }
  }

  function addListener(id, handler) {
    listeners.set(id, handler)
  }

  function removeListener(id) {
    listeners.delete(id)
  }

  function getState() {
    return ws ? ws.readyState : 3
  }

  function dispose() {
    if (ws) {
      ws.removeEventListener('open', handleOpen)
      ws.removeEventListener('message', handleMessage)
      ws.removeEventListener('close', handleClose)
      ws.removeEventListener('error', handleError)
      ws.close()
      ws = null
    }
    listeners.clear()
  }

  return {
    connect,
    sendSafe,
    addListener,
    removeListener,
    getState,
    dispose
  }
}

function ensureGlobalWs() {
  if (globalWs) {
    return
  }
  globalWs = createWsClient()
  globalWs.connect()
}

export function subscribeToPost(postId, onNewComment) {
  if (typeof window === 'undefined') {
    return () => {}
  }

  ensureGlobalWs()

  const stringId = String(postId)
  const listenerId = `post-${stringId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

  function handleMessage(data) {
    if (
      data &&
      data.type === 'new_comment' &&
      String(data.postId) === stringId &&
      data.comment
    ) {
      onNewComment(data.comment)
    }
  }

  globalWs.addListener(listenerId, handleMessage)
  globalSubscriptions.add(stringId)

  if (globalWs.getState() === 1) {
    globalWs.sendSafe({ type: 'subscribe', postId: stringId })
  }

  return function unsubscribe() {
    if (!globalWs) return
    globalWs.removeListener(listenerId)
    globalSubscriptions.delete(stringId)
    globalWs.sendSafe({ type: 'unsubscribe', postId: stringId })
  }
}

export function publishComment(postId, comment) {
  if (typeof window === 'undefined') {
    return false
  }
  ensureGlobalWs()
  return globalWs.sendSafe({
    type: 'comment',
    postId: String(postId),
    comment
  })
}

export default {
  getPosts,
  getPost,
  getComments,
  createComment,
  subscribeToPost,
  publishComment
}
