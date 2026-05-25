<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, CheckCircle2 } from 'lucide-vue-next'
import FormRenderer from '@/components/renderer/FormRenderer.vue'

const router = useRouter()
const submitted = ref(false)
const submittedData = ref<Record<string, any> | null>(null)
const formRendererRef = ref<InstanceType<typeof FormRenderer> | null>(null)

function handleSubmit(data: Record<string, any>) {
  submittedData.value = data
  submitted.value = true
}

function goBack() {
  router.push('/')
}

function resetForm() {
  submitted.value = false
  submittedData.value = null
}
</script>

<template>
  <div class="preview-page min-h-screen bg-slate-100">
    <div class="bg-white border-b border-slate-200 px-6 py-4">
      <div class="max-w-3xl mx-auto flex items-center justify-between">
        <button
          class="flex items-center gap-2 text-slate-600 hover:text-slate-800 transition-colors"
          @click="goBack"
        >
          <ArrowLeft :size="18" />
          <span class="text-sm font-medium">返回设计器</span>
        </button>
        <h1 class="text-lg font-semibold text-slate-800">表单预览</h1>
        <div class="w-24"></div>
      </div>
    </div>

    <div class="max-w-3xl mx-auto p-6">
      <div v-if="!submitted" class="bg-white rounded-xl shadow-sm p-8">
        <FormRenderer ref="formRendererRef" @submit="handleSubmit" />
      </div>

      <div v-else class="bg-white rounded-xl shadow-sm p-8">
        <div class="text-center py-8">
          <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 :size="32" class="text-green-500" />
          </div>
          <h2 class="text-xl font-semibold text-slate-800 mb-2">表单提交成功</h2>
          <p class="text-slate-500 mb-6">以下是您提交的数据</p>
        </div>

        <div class="bg-slate-50 rounded-lg p-6 mb-6">
          <div class="space-y-3">
            <div
              v-for="(value, key) in submittedData"
              :key="key"
              class="flex justify-between items-start py-2 border-b border-slate-200 last:border-0"
            >
              <span class="text-sm text-slate-600">{{ key }}</span>
              <span class="text-sm font-medium text-slate-800 text-right">
                {{ Array.isArray(value) ? value.join(', ') : (value ?? '-') }}
              </span>
            </div>
          </div>
        </div>

        <div class="flex justify-center gap-3">
          <button
            class="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
            @click="goBack"
          >
            返回编辑
          </button>
          <button
            class="px-4 py-2 bg-primary-500 text-white rounded-lg text-sm font-medium hover:bg-primary-600 transition-colors"
            @click="resetForm"
          >
            重新填写
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
