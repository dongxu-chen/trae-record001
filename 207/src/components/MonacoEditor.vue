<template>
  <div class="monaco-wrapper">
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
      <span class="loading-text">正在加载编辑器...</span>
    </div>
    <div ref="editorContainer" class="monaco-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as monaco from 'monaco-editor'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  language: {
    type: String,
    default: 'javascript'
  },
  theme: {
    type: String,
    default: 'vs-dark'
  },
  readOnly: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const editorContainer = ref(null)
const loading = ref(true)
let editor = null
let isInternalChange = false

const initEditor = () => {
  if (!editorContainer.value) return

  try {
    editor = monaco.editor.create(editorContainer.value, {
      value: props.modelValue,
      language: props.language,
      theme: props.theme,
      readOnly: props.readOnly,
      fontSize: 14,
      fontFamily: 'Consolas, "Courier New", monospace',
      minimap: { enabled: true },
      scrollBeyondLastLine: false,
      automaticLayout: true,
      tabSize: 2,
      wordWrap: 'on',
      lineNumbers: 'on',
      renderLineHighlight: 'all',
      cursorBlinking: 'smooth',
      smoothScrolling: true,
      padding: { top: 10, bottom: 10 }
    })

    editor.onDidChangeModelContent(() => {
      if (!isInternalChange) {
        const value = editor.getValue()
        emit('update:modelValue', value)
        emit('change', value)
      }
    })

    setTimeout(() => {
      loading.value = false
    }, 300)
  } catch (error) {
    console.error('Monaco Editor 加载失败:', error)
    loading.value = false
  }
}

watch(() => props.modelValue, (newValue) => {
  if (editor && editor.getValue() !== newValue) {
    isInternalChange = true
    editor.setValue(newValue || '')
    isInternalChange = false
  }
})

watch(() => props.language, (newLanguage) => {
  if (editor) {
    loading.value = true
    const model = editor.getModel()
    if (model) {
      monaco.editor.setModelLanguage(model, newLanguage)
    }
    setTimeout(() => {
      loading.value = false
    }, 200)
  }
})

watch(() => props.theme, (newTheme) => {
  if (editor) {
    monaco.editor.setTheme(newTheme)
  }
})

onMounted(() => {
  nextTick(() => {
    initEditor()
  })
})

onUnmounted(() => {
  if (editor) {
    editor.dispose()
    editor = null
  }
})
</script>

<style scoped>
.monaco-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
}

.monaco-container {
  width: 100%;
  height: 100%;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  z-index: 10;
  gap: 12px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-text {
  font-size: 14px;
  color: var(--text-secondary);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
