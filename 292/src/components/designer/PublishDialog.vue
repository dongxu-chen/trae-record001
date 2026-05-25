<script setup lang="ts">
import { ref, watch } from 'vue'
import { X, Upload, AlertCircle } from 'lucide-vue-next'
import { useVersionStore } from '@/stores/versionControl'
import { useDesignerStore } from '@/stores/designer'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const versionStore = useVersionStore()
const designerStore = useDesignerStore()

const changelog = ref('')
const isPublishing = ref(false)

watch(() => props.modelValue, (val) => {
  if (val) {
    changelog.value = ''
    isPublishing.value = false
  }
})

function close() {
  emit('update:modelValue', false)
}

async function handlePublish() {
  if (!changelog.value.trim()) {
    alert('请填写版本更新说明')
    return
  }

  isPublishing.value = true
  
  versionStore.updateDraft(designerStore.formSchema)
  versionStore.publishVersion(changelog.value)
  
  setTimeout(() => {
    isPublishing.value = false
    close()
  }, 500)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="close"
      >
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                <Upload class="text-primary-600" :size="20" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-slate-800">发布新版本</h3>
                <p class="text-sm text-slate-500">发布后将创建新的正式版本</p>
              </div>
            </div>
            <button
              class="p-2 rounded-lg hover:bg-slate-100 transition-colors"
              @click="close"
            >
              <X :size="20" class="text-slate-500" />
            </button>
          </div>

          <div class="p-6">
            <div class="mb-4 p-4 bg-amber-50 rounded-lg border border-amber-200">
              <div class="flex items-start gap-3">
                <AlertCircle class="text-amber-600 flex-shrink-0 mt-0.5" :size="18" />
                <div class="text-sm text-amber-800">
                  <p class="font-medium">发布提示</p>
                  <p class="mt-1">发布后当前草稿将成为正式版本，同时会自动创建新的草稿供后续编辑。</p>
                </div>
              </div>
            </div>

            <div class="mb-4">
              <label class="block text-sm font-medium text-slate-700 mb-2">
                当前版本信息
              </label>
              <div class="grid grid-cols-2 gap-4">
                <div class="p-3 bg-slate-50 rounded-lg">
                  <p class="text-xs text-slate-500">当前版本</p>
                  <p class="text-sm font-semibold text-slate-800">
                    {{ versionStore.publishedVersion?.version || '未发布' }}
                  </p>
                </div>
                <div class="p-3 bg-slate-50 rounded-lg">
                  <p class="text-xs text-slate-500">新版本号</p>
                  <p class="text-sm font-semibold text-primary-600">
                    {{ versionStore.publishedVersion 
                      ? versionStore.publishedVersion.version.split('.').map((v, i) => 
                          i === 2 ? Number(v) + 1 : v
                        ).join('.')
                      : '1.0.0' 
                    }}
                  </p>
                </div>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">
                版本更新说明 <span class="text-red-500">*</span>
              </label>
              <textarea
                v-model="changelog"
                class="w-full h-32 px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
                placeholder="请描述本次更新的内容..."
              ></textarea>
            </div>
          </div>

          <div class="flex items-center justify-end gap-3 px-6 py-4 bg-slate-50 border-t border-slate-200">
            <button
              class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
              @click="close"
            >
              取消
            </button>
            <button
              class="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              :disabled="!changelog.trim() || isPublishing"
              @click="handlePublish"
            >
              <Upload :size="16" />
              <span>{{ isPublishing ? '发布中...' : '确认发布' }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
