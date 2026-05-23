<template>
  <div class="markdown-editor">
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <span class="editor-label">📝 备注</span>
      </div>
      <div class="toolbar-right">
        <button
          class="mode-btn"
          :class="{ active: mode === 'edit' }"
          @click="mode = 'edit'"
        >
          ✏️ 编辑
        </button>
        <button
          class="mode-btn"
          :class="{ active: mode === 'preview' }"
          @click="mode = 'preview'"
        >
          👁️ 预览
        </button>
        <button
          class="mode-btn"
          :class="{ active: mode === 'split' }"
          @click="mode = 'split'"
        >
          📖 分屏
        </button>
      </div>
    </div>

    <div class="editor-content" :class="mode">
      <div v-if="mode !== 'preview'" class="edit-pane">
        <textarea
          ref="textareaRef"
          v-model="localContent"
          class="markdown-textarea"
          placeholder="支持 Markdown 语法...&#10;&#10;# 标题&#10;**粗体** *斜体*&#10;- 列表项&#10;`代码`"
          @input="handleInput"
        ></textarea>
      </div>

      <div v-if="mode !== 'edit'" class="preview-pane">
        <div class="markdown-preview" v-html="renderedHtml"></div>
        <div v-if="!localContent.trim()" class="empty-preview">
          <p>暂无备注内容</p>
          <p class="hint">点击"编辑"开始添加 Markdown 备注</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const mode = ref('edit')
const localContent = ref(props.modelValue)
const textareaRef = ref(null)

watch(() => props.modelValue, (newVal) => {
  if (newVal !== localContent.value) {
    localContent.value = newVal
  }
})

const renderedHtml = computed(() => {
  return simpleMarkdown(localContent.value)
})

const handleInput = () => {
  emit('update:modelValue', localContent.value)
  emit('change', localContent.value)
}

const simpleMarkdown = (text) => {
  if (!text) return ''
  
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>')
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>')
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>')
  
  html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')
  html = html.replace(/___(.*?)___/g, '<strong><em>$1</em></strong>')
  html = html.replace(/__(.*?)__/g, '<strong>$1</strong>')
  html = html.replace(/_(.*?)_/g, '<em>$1</em>')
  
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  
  html = html.replace(/^\s*[-*+]\s+(.*$)/gim, '<li>$1</li>')
  html = html.replace(/^\s*(\d+)\.\s+(.*$)/gim, '<li>$2</li>')
  
  html = html.replace(/^\s*>\s+(.*$)/gim, '<blockquote>$1</blockquote>')
  
  html = html.replace(/---/g, '<hr>')
  
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
  
  const lines = html.split('\n')
  let inList = false
  let result = []
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line.startsWith('<li>')) {
      if (!inList) {
        result.push('<ul>')
        inList = true
      }
    } else if (inList && !line.startsWith('<li>')) {
      result.push('</ul>')
      inList = false
    }
    if (line.trim() && !line.startsWith('<h') && !line.startsWith('<li') && !line.startsWith('<ul') && !line.startsWith('</ul') && !line.startsWith('<blockquote') && !line.startsWith('</blockquote') && !line.startsWith('<hr')) {
      result.push(`<p>${line}</p>`)
    } else {
      result.push(line)
    }
  }
  if (inList) result.push('</ul>')
  
  return result.join('\n')
}
</script>

<style scoped>
.markdown-editor {
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border);
}

.editor-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.toolbar-right {
  display: flex;
  gap: 4px;
}

.mode-btn {
  padding: 4px 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.mode-btn.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.editor-content {
  display: flex;
  min-height: 120px;
  max-height: 250px;
}

.editor-content.edit .edit-pane {
  width: 100%;
}

.editor-content.preview .preview-pane {
  width: 100%;
}

.editor-content.split .edit-pane,
.editor-content.split .preview-pane {
  width: 50%;
}

.editor-content.split .edit-pane {
  border-right: 1px solid var(--border);
}

.edit-pane {
  display: flex;
  flex-direction: column;
}

.markdown-textarea {
  flex: 1;
  width: 100%;
  padding: 12px;
  border: none;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: none;
  outline: none;
}

.markdown-textarea::placeholder {
  color: var(--text-secondary);
  opacity: 0.6;
}

.preview-pane {
  overflow-y: auto;
  background: var(--bg-primary);
}

.markdown-preview {
  padding: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary);
}

.markdown-preview :deep(h1) {
  font-size: 20px;
  font-weight: 600;
  margin: 12px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border);
}

.markdown-preview :deep(h2) {
  font-size: 17px;
  font-weight: 600;
  margin: 10px 0 6px;
}

.markdown-preview :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  margin: 8px 0 4px;
}

.markdown-preview :deep(p) {
  margin: 6px 0;
}

.markdown-preview :deep(strong) {
  font-weight: 600;
}

.markdown-preview :deep(em) {
  font-style: italic;
}

.markdown-preview :deep(code) {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: var(--accent);
}

.markdown-preview :deep(ul) {
  margin: 6px 0;
  padding-left: 24px;
}

.markdown-preview :deep(li) {
  margin: 2px 0;
}

.markdown-preview :deep(blockquote) {
  margin: 8px 0;
  padding: 8px 12px;
  border-left: 3px solid var(--accent);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-style: italic;
}

.markdown-preview :deep(a) {
  color: var(--accent);
  text-decoration: none;
}

.markdown-preview :deep(a:hover) {
  text-decoration: underline;
}

.markdown-preview :deep(hr) {
  border: none;
  height: 1px;
  background: var(--border);
  margin: 12px 0;
}

.empty-preview {
  padding: 30px 20px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-preview p {
  margin: 4px 0;
}

.empty-preview .hint {
  font-size: 12px;
  opacity: 0.7;
}
</style>
