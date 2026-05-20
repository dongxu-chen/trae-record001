<template>
  <div class="control-panel">
    <div class="panel-top">
      <button class="btn" @click="$emit('toggleMode')">
        {{ viewMode === 'double' ? '📖 双页' : '📜 卷轴' }}
      </button>
      
      <div class="zoom-controls">
        <button class="btn btn-small" @click="$emit('zoomOut')">−</button>
        <span class="zoom-value">{{ Math.round(zoom * 100) }}%</span>
        <button class="btn btn-small" @click="$emit('zoomIn')">+</button>
        <button class="btn btn-small" @click="$emit('resetZoom')">↺</button>
      </div>
      
      <button 
        class="btn bookmark-btn" 
        :class="{ active: isBookmarked }"
        @click="$emit('toggleBookmark')"
      >
        {{ isBookmarked ? '⭐' : '☆' }}
      </button>
      
      <button class="btn sync-btn" @click="$emit('syncBookmarks')" title="同步书签">
        🔄
      </button>
    </div>
    
    <div class="panel-bottom">
      <button class="btn nav-btn" @click="$emit('prev')" :disabled="currentPage <= 1">
        ◀ 上一页
      </button>
      
      <div class="page-controls">
        <input 
          type="number" 
          :value="currentPage" 
          @input="handlePageInput"
          min="1" 
          :max="totalPages"
          class="page-input"
        >
        <span class="page-separator">/</span>
        <span class="total-pages">{{ totalPages }}</span>
      </div>
      
      <button class="btn nav-btn" @click="$emit('next')" :disabled="currentPage >= totalPages">
        下一页 ▶
      </button>
    </div>
    
    <div v-if="bookmarks.length > 0" class="bookmarks-list">
      <span class="bookmarks-label">书签:</span>
      <button 
        v-for="page in bookmarks" 
        :key="page"
        class="bookmark-item"
        @click="$emit('goTo', page)"
      >
        {{ page }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentPage: Number,
  totalPages: Number,
  viewMode: String,
  zoom: Number,
  bookmarks: Array
})

const emit = defineEmits([
  'prev',
  'next',
  'goTo',
  'toggleMode',
  'zoomIn',
  'zoomOut',
  'resetZoom',
  'toggleBookmark'
])

const isBookmarked = computed(() => {
  return props.bookmarks.includes(props.currentPage)
})

function handlePageInput(e) {
  const page = parseInt(e.target.value)
  if (page >= 1 && page <= props.totalPages) {
    emit('goTo', page)
  }
}
</script>

<style scoped>
.control-panel {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.7), transparent);
  padding: 20px;
  padding-top: 60px;
  z-index: 50;
}

.panel-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.panel-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.btn {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.btn:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.4);
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-small {
  padding: 6px 12px;
  font-size: 16px;
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(0, 0, 0, 0.3);
  padding: 5px 10px;
  border-radius: 8px;
}

.zoom-value {
  min-width: 50px;
  text-align: center;
  font-size: 13px;
  color: #ccc;
}

.bookmark-btn {
  font-size: 20px;
  padding: 8px 16px;
}

.bookmark-btn.active {
  background: rgba(255, 200, 0, 0.3);
  border-color: rgba(255, 200, 0, 0.5);
}

.sync-btn {
  font-size: 18px;
  padding: 8px 12px;
  margin-left: 8px;
}

.nav-btn {
  min-width: 100px;
  font-weight: 500;
}

.page-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(0, 0, 0, 0.3);
  padding: 8px 15px;
  border-radius: 8px;
}

.page-input {
  width: 60px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  padding: 5px 10px;
  border-radius: 4px;
  text-align: center;
  font-size: 14px;
}

.page-input:focus {
  outline: none;
  border-color: #007aff;
}

.page-separator {
  color: #888;
}

.total-pages {
  color: #ccc;
  min-width: 30px;
}

.bookmarks-list {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 15px;
  flex-wrap: wrap;
}

.bookmarks-label {
  color: #888;
  font-size: 13px;
}

.bookmark-item {
  background: rgba(255, 200, 0, 0.2);
  border: 1px solid rgba(255, 200, 0, 0.4);
  color: #ffd700;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.bookmark-item:hover {
  background: rgba(255, 200, 0, 0.4);
}
</style>
