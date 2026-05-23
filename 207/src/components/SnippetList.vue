<template>
  <div class="snippet-list">
    <div class="list-header">
      <h3>代码片段</h3>
      <button class="btn btn-primary btn-sm" @click="$emit('create')">
        <span>+</span> 新建
      </button>
    </div>
    
    <div class="snippet-items">
      <div
        v-for="snippet in snippets"
        :key="snippet.id"
        class="snippet-item"
        :class="{ active: snippet.id === currentId }"
        @click="$emit('select', snippet.id)"
      >
        <div class="snippet-title">{{ snippet.title }}</div>
        <div class="snippet-meta">
          <span class="lang-badge">{{ getLanguageLabel(snippet.language) }}</span>
          <span class="date">{{ formatDate(snippet.updatedAt) }}</span>
        </div>
        <div class="snippet-tags" v-if="snippet.tags.length">
          <span
            v-for="tag in snippet.tags.slice(0, 3)"
            :key="tag"
            class="tag-small"
          >{{ tag }}</span>
        </div>
      </div>
      
      <div v-if="!snippets.length" class="empty-state">
        <p>暂无代码片段</p>
        <button class="btn btn-primary" @click="$emit('create')">创建第一个</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { LANGUAGES } from '../constants/languages'

defineProps({
  snippets: {
    type: Array,
    default: () => []
  },
  currentId: {
    type: String,
    default: null
  }
})

defineEmits(['select', 'create'])

const getLanguageLabel = (value) => {
  const lang = LANGUAGES.find(l => l.value === value)
  return lang ? lang.label : value
}

const formatDate = (timestamp) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  
  return date.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.snippet-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.list-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.snippet-items {
  flex: 1;
  overflow-y: auto;
}

.snippet-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.2s;
}

.snippet-item:hover {
  background: var(--bg-tertiary);
}

.snippet-item.active {
  background: var(--accent);
  color: white;
}

.snippet-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.snippet-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 12px;
}

.snippet-item.active .snippet-meta {
  opacity: 0.9;
}

.lang-badge {
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}

.snippet-item.active .lang-badge {
  background: rgba(255, 255, 255, 0.2);
}

.date {
  color: var(--text-secondary);
}

.snippet-item.active .date {
  color: rgba(255, 255, 255, 0.7);
}

.snippet-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.tag-small {
  background: var(--accent);
  color: white;
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 10px;
}

.snippet-item.active .tag-small {
  background: rgba(255, 255, 255, 0.3);
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-state p {
  margin-bottom: 16px;
}
</style>
