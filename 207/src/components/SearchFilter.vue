<template>
  <div class="search-filter">
    <div class="search-row">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input
          type="text"
          class="search-input"
          v-model="localSearch"
          @input="handleSearch"
          placeholder="搜索代码片段（标题、代码、标签）..."
        />
      </div>
    </div>
    
    <div class="tag-cloud-section">
      <div class="section-header">
        <span class="section-title">标签云</span>
        <button 
          v-if="selectedTags.length > 0"
          class="clear-btn"
          @click="clearTags"
        >
          清除筛选 ({{ selectedTags.length }})
        </button>
      </div>
      <div class="tag-cloud" v-if="tagStats.length > 0">
        <button
          v-for="item in tagStats"
          :key="item.tag"
          class="tag-cloud-item"
          :class="{ 
            active: selectedTags.includes(item.tag),
            size: getTagSize(item.count)
          }"
          :style="{ fontSize: getTagFontSize(item.count) + 'px' }"
          @click="toggleTag(item.tag)"
        >
          <span class="tag-name">{{ item.tag }}</span>
          <span class="tag-count">{{ item.count }}</span>
        </button>
      </div>
      <div v-else class="empty-tags">
        暂无标签，创建代码片段时可添加标签
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useStore } from 'vuex'

const props = defineProps({
  tagStats: {
    type: Array,
    default: () => []
  },
  selectedTags: {
    type: Array,
    default: () => []
  },
  searchQuery: {
    type: String,
    default: ''
  }
})

const store = useStore()
const localSearch = ref(props.searchQuery)

watch(() => props.searchQuery, (newVal) => {
  localSearch.value = newVal
})

const handleSearch = () => {
  store.commit('SET_SEARCH_QUERY', localSearch.value)
}

const toggleTag = (tag) => {
  store.commit('TOGGLE_TAG', tag)
}

const clearTags = () => {
  store.commit('CLEAR_TAGS')
}

const getTagSize = (count) => {
  if (count >= 10) return 'xl'
  if (count >= 5) return 'lg'
  if (count >= 3) return 'md'
  return 'sm'
}

const getTagFontSize = (count) => {
  const maxCount = Math.max(...props.tagStats.map(t => t.count), 1)
  const minSize = 12
  const maxSize = 18
  return minSize + (count / maxCount) * (maxSize - minSize)
}
</script>

<style scoped>
.search-filter {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
}

.search-row {
  width: 100%;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 14px;
  opacity: 0.5;
}

.search-input {
  width: 100%;
  padding: 10px 12px 10px 36px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: var(--accent);
}

.tag-cloud-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.clear-btn {
  padding: 2px 8px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.clear-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-cloud-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1.4;
}

.tag-cloud-item:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
}

.tag-cloud-item.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.tag-name {
  font-weight: 500;
}

.tag-count {
  font-size: 0.85em;
  opacity: 0.7;
}

.empty-tags {
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
  padding: 4px 0;
}
</style>
