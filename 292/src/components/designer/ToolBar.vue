<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Undo2, Redo2, Trash2, Eye, Code, Download, GitBranch, Upload, History, Printer, GitMerge } from 'lucide-vue-next'
import { useDesignerStore } from '@/stores/designer'
import { useVersionStore } from '@/stores/versionControl'
import { exportSchema } from '@/utils/schema'
import VersionHistoryDialog from './VersionHistoryDialog.vue'
import PublishDialog from './PublishDialog.vue'
import PrintTemplateDialog from './PrintTemplateDialog.vue'
import WorkflowDesignDialog from './WorkflowDesignDialog.vue'

const router = useRouter()
const store = useDesignerStore()
const versionStore = useVersionStore()

const showVersionHistory = ref(false)
const showPublishDialog = ref(false)
const showPrintTemplateDialog = ref(false)
const showWorkflowDesignDialog = ref(false)

function goToPreview() {
  router.push('/preview')
}

function goToSchema() {
  router.push('/schema')
}

function downloadSchema() {
  const schema = exportSchema(store.formSchema)
  const blob = new Blob([schema], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${store.formSchema.name || 'form'}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function handleClear() {
  if (confirm('确定要清空所有内容吗？此操作不可恢复。')) {
    store.clearAll()
  }
}
</script>

<template>
  <div class="toolbar flex items-center justify-between px-4 py-2 bg-slate-800 text-white">
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center font-bold text-sm">
          F
        </div>
        <div>
          <h1 class="text-sm font-semibold">低代码表单构建器</h1>
          <p class="text-xs text-slate-400">{{ store.formSchema.name }}</p>
        </div>
      </div>
    </div>

    <div class="flex items-center gap-1">
      <button
        class="p-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700"
        :disabled="!store.canUndo"
        @click="store.undo"
        title="撤销"
      >
        <Undo2 :size="18" />
      </button>
      <button
        class="p-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700"
        :disabled="!store.canRedo"
        @click="store.redo"
        title="重做"
      >
        <Redo2 :size="18" />
      </button>
      
      <div class="w-px h-5 bg-slate-600 mx-2"></div>
      
      <button
        class="p-2 rounded-lg transition-colors hover:bg-red-600/20 text-red-400 hover:text-red-300"
        @click="handleClear"
        title="清空"
      >
        <Trash2 :size="18" />
      </button>
      
      <div class="w-px h-5 bg-slate-600 mx-2"></div>
      
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors hover:bg-slate-700"
        @click="goToPreview"
        title="预览表单"
      >
        <Eye :size="18" />
        <span class="text-sm">预览</span>
      </button>
      
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors hover:bg-slate-700"
        @click="goToSchema"
        title="查看Schema"
      >
        <Code :size="18" />
        <span class="text-sm">Schema</span>
      </button>
      
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors hover:bg-slate-700"
        @click="downloadSchema"
        title="导出JSON"
      >
        <Download :size="18" />
        <span class="text-sm">导出</span>
      </button>
      
      <div class="w-px h-5 bg-slate-600 mx-2"></div>
      
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors hover:bg-slate-700"
        @click="showVersionHistory = true"
        title="版本历史"
      >
        <History :size="18" />
        <span class="text-sm">历史</span>
      </button>
      
      <button
        v-if="versionStore.hasPublished"
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors hover:bg-slate-700"
        title="已发布版本"
      >
        <GitBranch :size="18" />
        <span class="text-sm">{{ versionStore.publishedVersion?.version }}</span>
      </button>
      
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors bg-primary-600 hover:bg-primary-500"
        @click="showPublishDialog = true"
        title="发布版本"
      >
        <Upload :size="18" />
        <span class="text-sm">发布</span>
      </button>
      
      <div class="w-px h-5 bg-slate-600 mx-2"></div>
      
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors hover:bg-slate-700"
        @click="showPrintTemplateDialog = true"
        title="打印模板"
      >
        <Printer :size="18" />
        <span class="text-sm">打印</span>
      </button>
      
      <button
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors hover:bg-slate-700"
        @click="showWorkflowDesignDialog = true"
        title="工作流配置"
      >
        <GitMerge :size="18" />
        <span class="text-sm">流程</span>
      </button>
    </div>
  </div>
  
  <PublishDialog v-model="showPublishDialog" />
  <VersionHistoryDialog v-model="showVersionHistory" />
  <PrintTemplateDialog v-model="showPrintTemplateDialog" />
  <WorkflowDesignDialog v-model="showWorkflowDesignDialog" />
</template>
