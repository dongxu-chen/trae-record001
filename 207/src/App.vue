<template>
  <div class="app">
    <header class="app-header">
      <div class="header-left">
        <h1 class="app-title">📝 代码片段管理器</h1>
        <span class="snippet-count">{{ snippets.length }} 个片段</span>
      </div>
      <div class="header-right">
        <div class="keyboard-hints">
          <span class="hint">Ctrl+N 新建</span>
          <span class="hint">Ctrl+S 保存</span>
        </div>
        <button class="btn btn-secondary" @click="exportSnippets">
          📤 导出JSON
        </button>
        <button class="btn btn-secondary theme-toggle" @click="toggleTheme">
          {{ theme === 'dark' ? '☀️ 亮色' : '🌙 暗色' }}
        </button>
      </div>
    </header>

    <SearchFilter
      :tag-stats="tagStats"
      :selected-tags="selectedTags"
      :search-query="searchQuery"
    />

    <div class="main-content">
      <aside class="sidebar">
        <SnippetList
          :snippets="filteredSnippets"
          :current-id="currentSnippetId"
          @select="selectSnippet"
          @create="createSnippet"
        />
      </aside>
      <main class="content">
        <SnippetEditor
          :snippet="currentSnippet"
          @delete="deleteSnippet"
          ref="editorRef"
        />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useStore } from 'vuex'
import SearchFilter from './components/SearchFilter.vue'
import SnippetList from './components/SnippetList.vue'
import SnippetEditor from './components/SnippetEditor.vue'

const store = useStore()
const editorRef = ref(null)

const snippets = computed(() => store.state.snippets)
const filteredSnippets = computed(() => store.getters.filteredSnippets)
const tagStats = computed(() => store.getters.tagStats)
const currentSnippet = computed(() => store.getters.currentSnippet)
const currentSnippetId = computed(() => store.state.currentSnippetId)
const selectedTags = computed(() => store.state.selectedTags)
const searchQuery = computed(() => store.state.searchQuery)
const theme = computed(() => store.state.theme)

const toggleTheme = () => {
  const newTheme = theme.value === 'dark' ? 'light' : 'dark'
  store.commit('SET_THEME', newTheme)
}

const createSnippet = () => {
  store.dispatch('createSnippet', {
    title: '未命名片段',
    code: '// 在这里编写你的代码\n',
    language: 'javascript',
    tags: []
  })
}

const selectSnippet = (id) => {
  store.commit('SET_CURRENT_SNIPPET', id)
}

const deleteSnippet = (id) => {
  store.dispatch('deleteSnippet', id)
}

const exportSnippets = () => {
  store.dispatch('exportSnippets')
}

const handleKeydown = (e) => {
  if (e.ctrlKey || e.metaKey) {
    switch (e.key.toLowerCase()) {
      case 'n':
        e.preventDefault()
        createSnippet()
        break
      case 's':
        e.preventDefault()
        if (currentSnippet.value) {
          editorRef.value?.forceSave?.()
        }
        break
    }
  }
}

onMounted(() => {
  store.commit('SET_THEME', theme.value)
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.app-title {
  font-size: 20px;
  font-weight: 600;
}

.snippet-count {
  font-size: 13px;
  color: var(--text-secondary);
  padding: 4px 10px;
  background: var(--bg-tertiary);
  border-radius: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.keyboard-hints {
  display: flex;
  gap: 8px;
  margin-right: 8px;
}

.hint {
  font-size: 11px;
  color: var(--text-secondary);
  padding: 2px 6px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  border: 1px solid var(--border);
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.content {
  flex: 1;
  overflow: hidden;
}

@media (max-width: 768px) {
  .sidebar {
    width: 240px;
  }
  
  .app-title {
    font-size: 16px;
  }
  
  .snippet-count, .keyboard-hints {
    display: none;
  }
}
</style>
