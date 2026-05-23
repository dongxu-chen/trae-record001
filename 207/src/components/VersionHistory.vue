<template>
  <div class="version-history">
    <div class="version-header">
      <h3>📜 版本历史</h3>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>
    
    <div class="version-list" v-if="versions && versions.length > 0">
      <div
        v-for="(version, index) in versions"
        :key="version.id"
        class="version-item"
        :class="{ 'viewing': viewingVersion === version.id }"
      >
        <div class="version-info" @click="toggleView(version)">
          <div class="version-meta">
            <span class="version-badge">v{{ versions.length - index }}</span>
            <span class="version-date">{{ formatDate(version.createdAt) }}</span>
            <span class="version-lang">{{ version.language }}</span>
          </div>
          <div class="version-title">{{ version.title }}</div>
        </div>
        
        <div v-if="viewingVersion === version.id" class="version-detail">
          <div class="version-tags" v-if="version.tags && version.tags.length">
            <span class="mini-tag" v-for="tag in version.tags" :key="tag">{{ tag }}</span>
          </div>
          <div class="version-code">
            <pre><code>{{ version.code.slice(0, 500) }}{{ version.code.length > 500 ? '...' : '' }}</code></pre>
          </div>
          <div class="version-actions">
            <button class="btn btn-primary btn-sm" @click="rollback(version)">
              ↩️ 回滚到此版本
            </button>
            <button class="btn btn-secondary btn-sm" @click="deleteVersion(version)">
              🗑️ 删除
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="empty-versions">
      <p>暂无历史版本</p>
      <p class="hint">保存代码时会自动创建版本记录</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useStore } from 'vuex'

const props = defineProps({
  snippetId: {
    type: String,
    required: true
  },
  versions: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'rollback'])

const store = useStore()
const viewingVersion = ref(null)

const toggleView = (version) => {
  viewingVersion.value = viewingVersion.value === version.id ? null : version.id
}

const rollback = (version) => {
  if (confirm('确定要回滚到此版本吗？当前内容将被保存为新版本。')) {
    store.dispatch('rollbackVersion', {
      snippetId: props.snippetId,
      versionId: version.id
    })
    viewingVersion.value = null
    emit('rollback')
  }
}

const deleteVersion = (version) => {
  if (confirm('确定要删除这个历史版本吗？')) {
    store.dispatch('deleteVersion', {
      snippetId: props.snippetId,
      versionId: version.id
    })
    if (viewingVersion.value === version.id) {
      viewingVersion.value = null
    }
  }
}

const formatDate = (timestamp) => {
  return new Date(timestamp).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.version-history {
  background: var(--bg-secondary);
  border-left: 1px solid var(--border);
  width: 350px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.version-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.version-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 20px;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.version-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.version-item {
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.version-item:hover {
  border-color: var(--accent);
}

.version-item.viewing {
  border-color: var(--accent);
}

.version-info {
  padding: 12px;
  cursor: pointer;
  background: var(--bg-tertiary);
}

.version-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.version-badge {
  background: var(--accent);
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.version-date {
  font-size: 12px;
  color: var(--text-secondary);
}

.version-lang {
  font-size: 11px;
  background: var(--bg-hover);
  padding: 1px 6px;
  border-radius: 8px;
}

.version-title {
  font-size: 14px;
  font-weight: 500;
}

.version-detail {
  padding: 12px;
  border-top: 1px solid var(--border);
  background: var(--bg-primary);
}

.version-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.mini-tag {
  background: var(--accent-light);
  color: var(--accent);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}

.version-code {
  background: var(--bg-tertiary);
  border-radius: 6px;
  padding: 10px;
  max-height: 200px;
  overflow: auto;
  margin-bottom: 10px;
}

.version-code pre {
  margin: 0;
}

.version-code code {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-all;
}

.version-actions {
  display: flex;
  gap: 8px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.empty-versions {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-versions p {
  margin-bottom: 4px;
}

.hint {
  font-size: 12px;
  opacity: 0.7;
}
</style>
