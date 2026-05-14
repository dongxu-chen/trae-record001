import { db } from './firebase'
import {
  collection,
  addDoc,
  query,
  where,
  orderBy,
  limit,
  getDocs,
  onSnapshot
} from 'firebase/firestore'

const ACTIVITY_COLLECTION = 'activity_logs'

const ACTIVITY_TYPES = {
  CARD_CREATED: 'card_created',
  CARD_UPDATED: 'card_updated',
  CARD_DELETED: 'card_deleted',
  CARD_MOVED: 'card_moved',
  COMMENT_ADDED: 'comment_added',
  COMMENT_DELETED: 'comment_deleted',
  ATTACHMENT_UPLOADED: 'attachment_uploaded',
  ATTACHMENT_DELETED: 'attachment_deleted',
  MENTIONED: 'mentioned',
  LIST_CREATED: 'list_created',
  LIST_UPDATED: 'list_updated',
  LIST_DELETED: 'list_deleted'
}

function generateActivityDescription(type, data) {
  const templates = {
    [ACTIVITY_TYPES.CARD_CREATED]: () =>
      `创建了卡片"${data.cardTitle}"`,
    [ACTIVITY_TYPES.CARD_UPDATED]: () =>
      `更新了卡片"${data.cardTitle}"`,
    [ACTIVITY_TYPES.CARD_DELETED]: () =>
      `删除了卡片"${data.cardTitle}"`,
    [ACTIVITY_TYPES.CARD_MOVED]: () =>
      `将"${data.cardTitle}"从"${data.fromListTitle}"移动到"${data.toListTitle}"`,
    [ACTIVITY_TYPES.COMMENT_ADDED]: () =>
      `在卡片"${data.cardTitle}"中添加了评论`,
    [ACTIVITY_TYPES.COMMENT_DELETED]: () =>
      `删除了卡片"${data.cardTitle}"中的一条评论`,
    [ACTIVITY_TYPES.ATTACHMENT_UPLOADED]: () =>
      `上传了附件"${data.fileName}"到"${data.cardTitle}"`,
    [ACTIVITY_TYPES.ATTACHMENT_DELETED]: () =>
      `删除了附件"${data.fileName}"`,
    [ACTIVITY_TYPES.MENTIONED]: () =>
      `在评论中@了${data.mentionedName}`,
    [ACTIVITY_TYPES.LIST_CREATED]: () =>
      `创建了列表"${data.listTitle}"`,
    [ACTIVITY_TYPES.LIST_UPDATED]: () =>
      `更新了列表"${data.listTitle}"`,
    [ACTIVITY_TYPES.LIST_DELETED]: () =>
      `删除了列表"${data.listTitle}"`
  }

  const template = templates[type]
  return template ? template() : '执行了一个操作'
}

async function logActivity({
  type,
  userId = 'anonymous',
  userName = '匿名用户',
  listId = null,
  cardId = null,
  data = {},
  mentionedUserIds = []
}) {
  if (!ACTIVITY_TYPES[type]) {
    console.warn(`未知的活动类型: ${type}`)
    return null
  }

  const activity = {
    type,
    userId,
    userName,
    listId,
    cardId,
    data,
    mentionedUserIds,
    description: generateActivityDescription(type, data),
    createdAt: new Date(),
    read: false
  }

  try {
    const docRef = await addDoc(collection(db, ACTIVITY_COLLECTION), activity)
    activity.id = docRef.id
    return activity
  } catch (error) {
    console.error('记录活动日志失败:', error)
    return null
  }
}

async function getActivityLogs({
  userId = null,
  cardId = null,
  listId = null,
  mentionedUserId = null,
  limitCount = 50
}) {
  try {
    let q = query(collection(db, ACTIVITY_COLLECTION), orderBy('createdAt', 'desc'))

    if (userId) {
      q = query(q, where('userId', '==', userId))
    }
    if (cardId) {
      q = query(q, where('cardId', '==', cardId))
    }
    if (listId) {
      q = query(q, where('listId', '==', listId))
    }
    if (mentionedUserId) {
      q = query(q, where('mentionedUserIds', 'array-contains', mentionedUserId))
    }

    q = query(q, limit(limitCount))

    const snapshot = await getDocs(q)
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      createdAt: doc.data().createdAt?.toDate?.() || doc.data().createdAt
    }))
  } catch (error) {
    console.error('获取活动日志失败:', error)
    return []
  }
}

function subscribeToMentions(userId, callback) {
  if (!userId) return () => {}

  const q = query(
    collection(db, ACTIVITY_COLLECTION),
    where('mentionedUserIds', 'array-contains', userId),
    orderBy('createdAt', 'desc')
  )

  return onSnapshot(q, (snapshot) => {
    const mentions = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      createdAt: doc.data().createdAt?.toDate?.() || doc.data().createdAt
    }))
    callback(mentions)
  })
}

function formatTimeAgo(timestamp) {
  if (!timestamp) return ''

  const date = timestamp instanceof Date ? timestamp : new Date(timestamp)
  const now = new Date()
  const diff = now - date

  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  const weeks = Math.floor(days / 7)

  if (seconds < 60) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  if (weeks < 4) return `${weeks}周前`

  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

function extractMentions(text, users = []) {
  const mentionPattern = /@(\S+)/g
  const matches = text.match(mentionPattern) || []
  const mentionedNames = matches.map(m => m.slice(1))

  const mentionedUserIds = []
  const validMentions = []

  mentionedNames.forEach(name => {
    const user = users.find(u =>
      u.name === name || u.displayName === name || u.username === name
    )
    if (user) {
      mentionedUserIds.push(user.id)
      validMentions.push({ name, userId: user.id })
    }
  })

  return {
    mentionedUserIds,
    mentions: validMentions,
    rawMentions: mentionedNames
  }
}

function highlightMentions(text, onMentionClick = null) {
  const mentionPattern = /@(\S+)/g

  return text.replace(mentionPattern, (match, name) => {
    if (onMentionClick) {
      return `<span class="mention" data-name="${name}" style="color: #0079bf; font-weight: 600; cursor: pointer;">${match}</span>`
    }
    return `<span class="mention" style="color: #0079bf; font-weight: 600;">${match}</span>`
  })
}

export {
  logActivity,
  getActivityLogs,
  subscribeToMentions,
  formatTimeAgo,
  extractMentions,
  highlightMentions,
  ACTIVITY_TYPES
}
