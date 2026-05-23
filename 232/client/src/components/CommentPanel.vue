<template>
  <div class="comment-panel" :class="{ open: isOpen }">
    <div class="panel-header" @click="togglePanel">
      <span>💬 评论 ({{ comments.length }})</span>
      <span class="toggle-icon">{{ isOpen ? '▶' : '◀' }}</span>
    </div>
    
    <div v-if="isOpen" class="panel-content">
      <div class="comment-list">
        <div v-if="comments.length === 0" class="empty-state">
          暂无评论<br>
          <small>在画布上点击右键添加评论</small>
        </div>
        
        <div
          v-for="comment in comments"
          :key="comment.id"
          class="comment-item"
          :class="{ active: activeCommentId === comment.id, resolved: comment.resolved }"
          @click="selectComment(comment)"
        >
          <div class="comment-header">
            <div class="comment-author">
              <span class="avatar">{{ comment.author.charAt(0).toUpperCase() }}</span>
              <span class="name">{{ comment.author }}</span>
            </div>
            <span class="time">{{ formatTime(comment.timestamp) }}</span>
          </div>
          
          <div class="comment-content">{{ comment.content }}</div>
          
          <div v-if="comment.replies && comment.replies.length > 0" class="replies">
            <div v-for="reply in comment.replies" :key="reply.id" class="reply-item">
              <div class="reply-author">
                <span class="avatar small">{{ reply.author.charAt(0).toUpperCase() }}</span>
                <span class="name">{{ reply.author }}</span>
                <span class="time">{{ formatTime(reply.timestamp) }}</span>
              </div>
              <div class="reply-content">{{ reply.content }}</div>
            </div>
          </div>
          
          <div class="comment-actions">
            <button class="action-btn" @click.stop="showReplyInput(comment.id)">
              ↩️ 回复
            </button>
            <button class="action-btn resolve" @click.stop="toggleResolve(comment.id)">
              {{ comment.resolved ? '🔄 重新打开' : '✅ 解决' }}
            </button>
          </div>
          
          <div v-if="replyingTo === comment.id" class="reply-input">
            <div class="mention-wrapper">
              <textarea
                ref="replyTextarea"
                v-model="replyContent"
                placeholder="输入回复... (@提及用户)"
                @input="handleReplyInput"
                @keydown="handleReplyKeydown"
                rows="2"
              ></textarea>
              <div v-if="showMentionList" class="mention-list">
                <div
                  v-for="user in mentionUsers"
                  :key="user.id"
                  class="mention-item"
                  @click="insertMention(user)"
                >
                  {{ user.name }}
                </div>
              </div>
            </div>
            <div class="reply-buttons">
              <button class="btn small" @click="cancelReply">取消</button>
              <button class="btn small primary" @click="submitReply(comment.id)">发送</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  comments: { type: Array, default: () => [] },
  activeCommentId: { type: String, default: null },
  currentUser: { type: String, default: '我' },
  onlineUsers: { type: Array, default: () => [] }
})

const emit = defineEmits(['select', 'reply', 'resolve'])

const isOpen = ref(true)
const replyingTo = ref(null)
const replyContent = ref('')
const showMentionList = ref(false)
const mentionSearch = ref('')

const replyTextarea = ref(null)

const mentionUsers = computed(() => {
  const users = props.onlineUsers.map(u => ({ id: u.id, name: u.name }))
  if (!mentionSearch.value) return users
  return users.filter(u => 
    u.name.toLowerCase().includes(mentionSearch.value.toLowerCase())
  )
})

function togglePanel() {
  isOpen.value = !isOpen.value
}

function selectComment(comment) {
  emit('select', comment.id)
}

function showReplyInput(commentId) {
  replyingTo.value = commentId
  replyContent.value = ''
  setTimeout(() => {
    replyTextarea.value?.focus()
  }, 100)
}

function cancelReply() {
  replyingTo.value = null
  replyContent.value = ''
  showMentionList.value = false
}

function handleReplyInput(e) {
  const text = e.target.value
  const lastAt = text.lastIndexOf('@')
  
  if (lastAt !== -1 && lastAt === text.length - 1) {
    showMentionList.value = true
    mentionSearch.value = ''
  } else if (lastAt !== -1) {
    const afterAt = text.slice(lastAt + 1)
    if (!afterAt.includes(' ')) {
      showMentionList.value = true
      mentionSearch.value = afterAt
    } else {
      showMentionList.value = false
    }
  } else {
    showMentionList.value = false
  }
}

function handleReplyKeydown(e) {
  if (e.key === 'Escape') {
    cancelReply()
  }
}

function insertMention(user) {
  const lastAt = replyContent.value.lastIndexOf('@')
  if (lastAt !== -1) {
    replyContent.value = replyContent.value.slice(0, lastAt) + '@' + user.name + ' '
  }
  showMentionList.value = false
  replyTextarea.value?.focus()
}

function submitReply(commentId) {
  if (!replyContent.value.trim()) return
  
  emit('reply', {
    commentId,
    content: replyContent.value.trim()
  })
  
  cancelReply()
}

function toggleResolve(commentId) {
  emit('resolve', commentId)
}

function formatTime(timestamp) {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString().slice(0, 5)
}
</script>

<style scoped>
.comment-panel {
  position: absolute;
  right: 280px;
  top: 50%;
  transform: translateY(-50%);
  background: var(--toolbar-bg);
  border-radius: var(--border-radius) 0 0 var(--border-radius);
  box-shadow: var(--shadow);
  z-index: 100;
  transition: all 0.3s;
  max-height: 80vh;
  overflow: hidden;
}

.panel-header {
  padding: 12px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  white-space: nowrap;
  font-weight: 500;
  border-bottom: 1px solid #e5e7eb;
}

.toggle-icon {
  font-size: 12px;
  color: var(--secondary-color);
}

.panel-content {
  width: 320px;
  max-height: calc(80vh - 50px);
  overflow-y: auto;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--secondary-color);
  font-size: 14px;
  line-height: 1.6;
}

.comment-list {
  padding: 8px;
}

.comment-item {
  padding: 12px;
  margin-bottom: 8px;
  background: white;
  border-radius: var(--border-radius);
  border: 1px solid #e5e7eb;
  cursor: pointer;
  transition: all 0.2s;
}

.comment-item:hover {
  border-color: var(--primary-color);
}

.comment-item.active {
  border-color: var(--primary-color);
  background: #eff6ff;
}

.comment-item.resolved {
  opacity: 0.6;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.comment-author {
  display: flex;
  align-items: center;
  gap: 6px;
}

.avatar {
  width: 24px;
  height: 24px;
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
}

.avatar.small {
  width: 20px;
  height: 20px;
  font-size: 10px;
}

.name {
  font-weight: 500;
  font-size: 13px;
}

.time {
  font-size: 11px;
  color: var(--secondary-color);
}

.comment-content {
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 8px;
}

.replies {
  margin-left: 20px;
  padding-left: 12px;
  border-left: 2px solid #e5e7eb;
  margin-bottom: 8px;
}

.reply-item {
  margin-bottom: 8px;
}

.reply-author {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.reply-content {
  font-size: 12px;
  line-height: 1.4;
  color: #4b5563;
}

.comment-actions {
  display: flex;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid #f3f4f6;
}

.action-btn {
  padding: 4px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 11px;
  color: var(--secondary-color);
  border-radius: 4px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f3f4f6;
  color: var(--primary-color);
}

.action-btn.resolve:hover {
  color: #10b981;
}

.reply-input {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #f3f4f6;
}

.mention-wrapper {
  position: relative;
}

.reply-input textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 12px;
  resize: none;
  font-family: inherit;
}

.reply-input textarea:focus {
  outline: none;
  border-color: var(--primary-color);
}

.mention-list {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  max-height: 150px;
  overflow-y: auto;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  box-shadow: var(--shadow);
  margin-bottom: 4px;
  z-index: 10;
}

.mention-item {
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
}

.mention-item:hover {
  background: #eff6ff;
}

.reply-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 8px;
}

.btn.small {
  padding: 4px 12px;
  font-size: 12px;
}

.btn.small.primary {
  background: var(--primary-color);
  color: white;
}

.btn.small.primary:hover {
  background: #2563eb;
}
</style>
