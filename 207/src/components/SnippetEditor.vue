<template>
  <div class="snippet-editor-wrapper" v-if="snippet">
    <div class="snippet-editor" :class="{ 'with-version-history': showVersionHistory }">
      <div class="editor-header">
        <div class="header-left">
          <input
            type="text"
            class="title-input"
            v-model="localTitle"
            @input="debouncedUpdate"
            placeholder="输入代码片段标题..."
          />
        </div>
        <div class="header-right">
          <select class="select" v-model="localLanguage" @change="updateSnippet">
            <option v-for="lang in LANGUAGES" :key="lang.value" :value="lang.value">
              {{ lang.label }}
            </option>
          </select>
          <button class="btn btn-secondary btn-sm" @click="showVersionHistory = !showVersionHistory">
            📜 历史 ({{ versionCount }})
          </button>
          <button class="btn btn-secondary btn-sm" @click="openShareModal">
            🔗 分享
          </button>
          <button class="btn btn-danger btn-sm" @click="confirmDelete">
            🗑️ 删除
          </button>
        </div>
      </div>

      <div class="tags-section">
        <span class="tags-label">标签:</span>
        <div class="tags-list">
          <span
            v-for="tag in localTags"
            :key="tag"
            class="tag"
          >
            {{ tag }}
            <span class="tag-remove" @click="removeTag(tag)">×</span>
          </span>
        </div>
        <input
          type="text"
          class="tag-input"
          v-model="newTag"
          @keydown.enter="addTag"
          placeholder="添加标签，回车确认"
        />
      </div>

      <div class="main-content">
        <div class="code-section">
          <div class="editor-container">
            <MonacoEditor
              v-model="localCode"
              :language="localLanguage"
              :theme="monacoTheme"
              @change="debouncedUpdate"
            />
          </div>
        </div>

        <div class="description-section">
          <MarkdownEditor
            v-model="localDescription"
            @change="debouncedUpdate"
          />
        </div>
      </div>

      <div class="editor-footer">
        <span class="save-status" :class="{ saved: isSaved }">
          {{ isSaved ? '✓ 已保存' : '正在保存...' }}
        </span>
        <span class="meta-info">
          创建于: {{ formatDate(snippet.createdAt) }}
        </span>
      </div>
    </div>

    <VersionHistory
      v-if="showVersionHistory"
      :snippet-id="snippet.id"
      :versions="snippet.versions || []"
      @close="showVersionHistory = false"
      @rollback="onRollback"
    />

    <ShareModal
      v-if="showShareModal"
      :snippet-id="snippet.id"
      :shared-snippets="sharedSnippets"
      @close="showShareModal = false"
    />
  </div>

  <div v-else class="empty-editor">
    <div class="empty-content">
      <h2>选择或创建代码片段</h2>
      <p>从左侧列表选择一个片段，或创建新的代码片段开始</p>
      <p class="shortcuts">快捷键: Ctrl+N 新建 | Ctrl+S 保存</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, defineExpose } from 'vue'
import { useStore } from 'vuex'
import MonacoEditor from './MonacoEditor.vue'
import MarkdownEditor from './MarkdownEditor.vue'
import VersionHistory from './VersionHistory.vue'
import ShareModal from './ShareModal.vue'
import { LANGUAGES } from '../constants/languages'

const props = defineProps({
  snippet: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['delete'])

const store = useStore()

const localTitle = ref('')
const localCode = ref('')
const localLanguage = ref('javascript')
const localTags = ref([])
const localDescription = ref('')
const newTag = ref('')
const isSaved = ref(true)
const showVersionHistory = ref(false)
const showShareModal = ref(false)

let saveTimer = null

const monacoTheme = computed(() => {
  return store.state.theme === 'dark' ? 'vs-dark' : 'vs'
})

const versionCount = computed(() => {
  return props.snippet?.versions?.length || 0
})

const sharedSnippets = computed(() => {
  return store.state.sharedSnippets
})

const initLocalState = () => {
  if (props.snippet) {
    localTitle.value = props.snippet.title
    localCode.value = props.snippet.code
    localLanguage.value = props.snippet.language
    localTags.value = [...props.snippet.tags]
    localDescription.value = props.snippet.description || ''
    isSaved.value = true
  }
}

const updateSnippet = (createVersion = true) => {
  if (!props.snippet) return
  
  store.dispatch('updateSnippet', {
    id: props.snippet.id,
    data: {
      title: localTitle.value,
      code: localCode.value,
      language: localLanguage.value,
      tags: localTags.value,
      description: localDescription.value
    },
    createVersion
  })
  isSaved.value = true
}

const debouncedUpdate = () => {
  isSaved.value = false
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(updateSnippet, 500)
}

const forceSave = () => {
  if (saveTimer) clearTimeout(saveTimer)
  updateSnippet(true)
}

const addTag = () => {
  const tag = newTag.value.trim()
  if (tag && !localTags.value.includes(tag)) {
    localTags.value.push(tag)
    newTag.value = ''
    updateSnippet(false)
  }
}

const removeTag = (tag) => {
  localTags.value = localTags.value.filter(t => t !== tag)
  updateSnippet(false)
}

const confirmDelete = () => {
  if (confirm('确定要删除这个代码片段吗？此操作不可撤销。')) {
    emit('delete', props.snippet.id)
  }
}

const openShareModal = () => {
  showShareModal.value = true
}

const onRollback = () => {
  initLocalState()
}

const formatDate = (timestamp) => {
  return new Date(timestamp).toLocaleString('zh-CN')
}

watch(() => props.snippet, () => {
  if (saveTimer) clearTimeout(saveTimer)
  showVersionHistory.value = false
  showShareModal.value = false
  initLocalState()
}, { immediate: true })

onUnmounted(() => {
  if (saveTimer) clearTimeout(saveTimer)
})

defineExpose({
  forceSave
})
</script>

<style scoped>
.snippet-editor-wrapper {
  display: flex;
  height: 100%;
  background: var(--bg-primary);
}

.snippet-editor {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  transition: width 0.3s;
}

.snippet-editor.with-version-history {
  width: calc(100% - 350px);
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  gap: 16px;
}

.header-left {
  flex: 1;
  min-width: 0;
}

.title-input {
  width: 100%;
  font-size: 18px;
  font-weight: 600;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: transparent;
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.2s;
}

.title-input:hover,
.title-input:focus {
  border-color: var(--border);
  background: var(--bg-tertiary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.tags-section {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
}

.tags-label {
  font-size: 14px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.tags-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  background: var(--accent);
  color: white;
  border-radius: 12px;
  font-size: 12px;
}

.tag-remove {
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  opacity: 0.7;
}

.tag-remove:hover {
  opacity: 1;
}

.tag-input {
  width: 150px;
  padding: 4px 8px;
  border: 1px dashed var(--border);
  border-radius: 4px;
  background: transparent;
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
}

.tag-input:focus {
  border-style: solid;
  border-color: var(--accent);
}

.main-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.code-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.editor-container {
  flex: 1;
  overflow: hidden;
  min-height: 200px;
}

.description-section {
  border-top: 1px solid var(--border);
  padding: 12px 16px;
  background: var(--bg-secondary);
  max-height: 250px;
  overflow: hidden;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.save-status.saved {
  color: var(--success);
}

.empty-editor {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: var(--bg-primary);
}

.empty-content {
  text-align: center;
  color: var(--text-secondary);
}

.empty-content h2 {
  font-size: 24px;
  margin-bottom: 12px;
}

.empty-content p {
  font-size: 14px;
  margin-bottom: 8px;
}

.empty-content .shortcuts {
  font-size: 12px;
  opacity: 0.7;
}
</style>
