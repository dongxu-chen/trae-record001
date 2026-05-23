<template>
  <div class="share-modal-overlay" @click.self="$emit('close')">
    <div class="share-modal">
      <div class="modal-header">
        <h3>🔗 分享代码片段</h3>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>
      
      <div class="modal-body">
        <div class="share-section">
          <label class="form-label">过期时间</label>
          <div class="expire-options">
            <button
              v-for="option in expireOptions"
              :key="option.value"
              class="expire-btn"
              :class="{ active: selectedExpire === option.value }"
              @click="selectedExpire = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </div>

        <div class="share-section" v-if="shareId">
          <label class="form-label">分享链接</label>
          <div class="share-link-box">
            <input type="text" class="link-input" :value="shareUrl" readonly />
            <button class="copy-btn" @click="copyLink">
              {{ copied ? '✓ 已复制' : '📋 复制' }}
            </button>
          </div>
          <p class="link-hint">
            此链接为只读模式，他人无法修改您的代码片段
          </p>
        </div>

        <div class="share-section" v-if="!shareId">
          <button class="btn btn-primary generate-btn" @click="generateLink">
            生成分享链接
          </button>
        </div>

        <div class="share-section" v-if="existingShares.length > 0">
          <label class="form-label">已有分享链接 ({{ existingShares.length }})</label>
          <div class="existing-shares">
            <div
              v-for="share in existingShares"
              :key="share.shareId"
              class="share-item"
            >
              <div class="share-info">
                <span class="share-date">
                  创建于 {{ formatDate(share.createdAt) }}
                </span>
                <span class="share-expire" :class="{ expired: isExpired(share) }">
                  {{ getExpireStatus(share) }}
                </span>
              </div>
              <div class="share-actions">
                <button class="mini-btn" @click="copyShareId(share.shareId)">
                  📋
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useStore } from 'vuex'

const props = defineProps({
  snippetId: {
    type: String,
    required: true
  },
  sharedSnippets: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close'])

const store = useStore()
const selectedExpire = ref(86400000)
const shareId = ref(null)
const copied = ref(false)

const expireOptions = [
  { label: '1小时', value: 3600000 },
  { label: '1天', value: 86400000 },
  { label: '7天', value: 604800000 },
  { label: '永久', value: null }
]

const existingShares = computed(() => {
  return props.sharedSnippets.filter(s => s.snippetId === props.snippetId)
})

const shareUrl = computed(() => {
  if (!shareId.value) return ''
  return `${window.location.origin}${window.location.pathname}?share=${shareId.value}`
})

const generateLink = () => {
  shareId.value = store.dispatch('createShareLink', {
    snippetId: props.snippetId,
    expiresIn: selectedExpire.value
  })
}

const copyLink = async () => {
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    const input = document.createElement('input')
    input.value = shareUrl.value
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  }
}

const copyShareId = async (id) => {
  const url = `${window.location.origin}${window.location.pathname}?share=${id}`
  try {
    await navigator.clipboard.writeText(url)
  } catch {
    const input = document.createElement('input')
    input.value = url
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
  }
}

const formatDate = (timestamp) => {
  return new Date(timestamp).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const isExpired = (share) => {
  return share.expiresAt && share.expiresAt < Date.now()
}

const getExpireStatus = (share) => {
  if (!share.expiresAt) return '永久有效'
  if (isExpired(share)) return '已过期'
  const remaining = share.expiresAt - Date.now()
  const hours = Math.floor(remaining / 3600000)
  if (hours < 1) return '即将过期'
  if (hours < 24) return `${hours}小时后过期`
  return `${Math.floor(hours / 24)}天后过期`
}
</script>

<style scoped>
.share-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.share-modal {
  background: var(--bg-secondary);
  border-radius: 12px;
  width: 90%;
  max-width: 480px;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 24px;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  max-height: calc(80vh - 60px);
}

.share-section {
  margin-bottom: 20px;
}

.share-section:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 10px;
  color: var(--text-primary);
}

.expire-options {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.expire-btn {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.expire-btn:hover {
  border-color: var(--accent);
}

.expire-btn.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.share-link-box {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.link-input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 13px;
  font-family: monospace;
}

.copy-btn {
  padding: 10px 16px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.copy-btn:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.link-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
}

.generate-btn {
  width: 100%;
  padding: 12px;
  font-size: 14px;
  font-weight: 500;
}

.existing-shares {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.share-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  border: 1px solid var(--border);
}

.share-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.share-date {
  font-size: 12px;
  color: var(--text-secondary);
}

.share-expire {
  font-size: 11px;
  color: var(--success);
}

.share-expire.expired {
  color: var(--danger);
}

.share-actions {
  display: flex;
  gap: 4px;
}

.mini-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mini-btn:hover {
  background: var(--bg-hover);
}
</style>
