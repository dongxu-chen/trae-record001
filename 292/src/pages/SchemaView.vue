<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Copy, Check, Download, FileArchive, FileJson } from 'lucide-vue-next'
import { useDesignerStore } from '@/stores/designer'
import { exportSchema } from '@/utils/schema'
import { compressSchema, type CompressionResult } from '@/utils/schemaCompressor'

const router = useRouter()
const store = useDesignerStore()
const copied = ref(false)
const useCompressed = ref(false)

const compressionResult = computed<CompressionResult | null>(() => {
  try {
    return compressSchema(store.formSchema)
  } catch (e) {
    return null
  }
})

const schemaJson = computed(() => {
  if (useCompressed.value && compressionResult.value) {
    return JSON.stringify(compressionResult.value.compressed, null, 2)
  }
  return exportSchema(store.formSchema)
})

const fileSize = computed(() => {
  return new Blob([schemaJson.value]).size
})

function goBack() {
  router.push('/')
}

function copySchema() {
  navigator.clipboard.writeText(schemaJson.value)
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 2000)
}

function downloadSchema() {
  const blob = new Blob([schemaJson.value], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${store.formSchema.name || 'form'}${useCompressed.value ? '.compressed' : ''}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <div class="schema-page min-h-screen bg-slate-100">
    <div class="bg-white border-b border-slate-200 px-6 py-4">
      <div class="max-w-4xl mx-auto flex items-center justify-between">
        <button
          class="flex items-center gap-2 text-slate-600 hover:text-slate-800 transition-colors"
          @click="goBack"
        >
          <ArrowLeft :size="18" />
          <span class="text-sm font-medium">返回设计器</span>
        </button>
        <h1 class="text-lg font-semibold text-slate-800">JSON Schema</h1>
        <div class="flex items-center gap-2">
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            @click="copySchema"
          >
            <component :is="copied ? Check : Copy" :size="16" />
            {{ copied ? '已复制' : '复制' }}
          </button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 bg-primary-500 text-white rounded-lg text-sm font-medium hover:bg-primary-600 transition-colors"
            @click="downloadSchema"
          >
            <Download :size="16" />
            下载
          </button>
        </div>
      </div>
    </div>

    <div class="max-w-4xl mx-auto p-6">
      <div class="bg-white rounded-xl p-4 shadow-sm mb-4">
        <div class="flex flex-wrap items-center gap-4">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium text-slate-700">Schema格式：</span>
            <div class="flex bg-slate-100 rounded-lg p-0.5">
              <button
                class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
                :class="!useCompressed ? 'bg-white shadow text-primary-600' : 'text-slate-600 hover:text-slate-800'"
                @click="useCompressed = false"
              >
                <FileJson :size="14" />
                标准格式
              </button>
              <button
                class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
                :class="useCompressed ? 'bg-white shadow text-primary-600' : 'text-slate-600 hover:text-slate-800'"
                @click="useCompressed = true"
              >
                <FileArchive :size="14" />
                压缩格式
              </button>
            </div>
          </div>
          <div class="flex-1"></div>
          <div class="text-sm text-slate-600">
            <span class="text-slate-500">文件大小：</span>
            <span class="font-mono font-medium">{{ formatSize(fileSize) }}</span>
          </div>
        </div>

        <div v-if="compressionResult" class="mt-3 pt-3 border-t border-slate-100">
          <div class="flex flex-wrap items-center gap-4 text-xs">
            <div class="flex items-center gap-2">
              <span class="text-slate-500">原始大小：</span>
              <span class="font-mono text-slate-700">{{ formatSize(compressionResult.originalSize) }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-slate-500">压缩大小：</span>
              <span class="font-mono text-slate-700">{{ formatSize(compressionResult.compressedSize) }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-slate-500">压缩率：</span>
              <span class="font-mono" :class="compressionResult.compressionRatio > 0 ? 'text-green-600' : 'text-slate-500'">
                {{ compressionResult.compressionRatio > 0 ? `-${compressionResult.compressionRatio}%` : '-' }}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-slate-500">去重统计：</span>
              <span class="text-slate-700">
                校验规则{{ compressionResult.stats.validationDeduplications }}个 · 
                选项集合{{ compressionResult.stats.optionSetDeduplications }}个 · 
                字段模板{{ compressionResult.stats.fieldTemplateDeduplications }}个 · 
                公式模板{{ compressionResult.stats.formulaDeduplications }}个
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-slate-900 rounded-xl overflow-hidden shadow-lg">
        <div class="flex items-center justify-between px-4 py-3 bg-slate-800 border-b border-slate-700">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 rounded-full bg-red-500"></div>
            <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div class="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <span class="text-xs text-slate-400">
            {{ useCompressed ? 'form-schema.compressed.json' : 'form-schema.json' }}
          </span>
          <div class="w-16"></div>
        </div>
        <pre class="p-6 text-sm text-slate-300 overflow-auto max-h-[calc(100vh-300px)] font-mono leading-relaxed">{{ schemaJson }}</pre>
      </div>

      <div class="mt-6 bg-white rounded-xl p-6 shadow-sm">
        <h3 class="font-semibold text-slate-800 mb-4">Schema 结构说明</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div class="p-4 bg-slate-50 rounded-lg">
            <div class="font-medium text-slate-700 mb-2">表单信息</div>
            <ul class="space-y-1 text-slate-500">
              <li><code class="text-xs bg-slate-200 px-1 rounded">id</code> - 表单唯一标识</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">name</code> - 表单名称</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">description</code> - 表单描述</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">version</code> - 版本号</li>
            </ul>
          </div>
          <div class="p-4 bg-slate-50 rounded-lg">
            <div class="font-medium text-slate-700 mb-2">页签结构</div>
            <ul class="space-y-1 text-slate-500">
              <li><code class="text-xs bg-slate-200 px-1 rounded">tabs</code> - 页签数组</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">tabs[].id</code> - 页签ID</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">tabs[].name</code> - 页签名称</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">tabs[].fields</code> - 字段数组</li>
            </ul>
          </div>
          <div class="p-4 bg-slate-50 rounded-lg">
            <div class="font-medium text-slate-700 mb-2">字段配置</div>
            <ul class="space-y-1 text-slate-500">
              <li><code class="text-xs bg-slate-200 px-1 rounded">type</code> - 字段类型</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">name</code> - 字段标识</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">label</code> - 字段标签</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">required</code> - 是否必填</li>
            </ul>
          </div>
          <div class="p-4 bg-slate-50 rounded-lg">
            <div class="font-medium text-slate-700 mb-2">高级配置</div>
            <ul class="space-y-1 text-slate-500">
              <li><code class="text-xs bg-slate-200 px-1 rounded">validation</code> - 校验规则</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">formula</code> - 公式计算</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">conditional</code> - 条件显隐</li>
              <li><code class="text-xs bg-slate-200 px-1 rounded">props</code> - 扩展属性</li>
            </ul>
          </div>
        </div>

        <div class="mt-4 p-4 bg-primary-50 rounded-lg border border-primary-100">
          <div class="font-medium text-primary-700 mb-2">压缩格式说明</div>
          <p class="text-xs text-primary-600 mb-2">
            压缩格式通过引用去重减少冗余：相同的校验规则、选项集合、公式模板会被提取到definitions中复用
          </p>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div><code class="bg-primary-100 text-primary-700 px-1 rounded">$ref</code> - 字段模板引用</div>
            <div><code class="bg-primary-100 text-primary-700 px-1 rounded">$validationRef</code> - 校验规则引用</div>
            <div><code class="bg-primary-100 text-primary-700 px-1 rounded">$optionsRef</code> - 选项集合引用</div>
            <div><code class="bg-primary-100 text-primary-700 px-1 rounded">$formulaRef</code> - 公式模板引用</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
