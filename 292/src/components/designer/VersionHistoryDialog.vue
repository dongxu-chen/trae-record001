<script setup lang="ts">
import { ref, computed } from 'vue'
import { X, History, RotateCcw, GitBranch, FileText, Eye, ArrowRight } from 'lucide-vue-next'
import { useVersionStore } from '@/stores/versionControl'
import { useDesignerStore } from '@/stores/designer'
import type { FormVersion } from '@/types/advanced'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const versionStore = useVersionStore()
const designerStore = useDesignerStore()

const compareVersion1 = ref<string | null>(null)
const compareVersion2 = ref<string | null>(null)
const showRollbackConfirm = ref(false)
const rollbackVersion = ref<FormVersion | null>(null)
const rollbackReason = ref('')

const sortedVersions = computed(() => {
  return [...versionStore.versions].sort((a, b) => 
    new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  )
})

const comparisonResult = computed(() => {
  if (compareVersion1.value && compareVersion2.value) {
    return versionStore.compareVersions(compareVersion1.value, compareVersion2.value)
  }
  return null
})

function close() {
  emit('update:modelValue', false)
  compareVersion1.value = null
  compareVersion2.value = null
}

function getStatusBadge(status: string) {
  const badges: Record<string, { class: string; text: string }> = {
    draft: { class: 'bg-blue-100 text-blue-700', text: '草稿' },
    published: { class: 'bg-green-100 text-green-700', text: '已发布' },
    archived: { class: 'bg-slate-100 text-slate-600', text: '已归档' }
  }
  return badges[status] || badges.archived
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function startRollback(version: FormVersion) {
  rollbackVersion.value = version
  rollbackReason.value = ''
  showRollbackConfirm.value = true
}

function confirmRollback() {
  if (!rollbackVersion.value) return
  
  versionStore.rollbackToVersion(rollbackVersion.value.id, rollbackReason.value || '回滚到历史版本')
  
  const draftSchema = versionStore.getDraftSchema()
  if (draftSchema) {
    designerStore.loadSchema(draftSchema)
  }
  
  showRollbackConfirm.value = false
  rollbackVersion.value = null
}

function previewVersion(version: FormVersion) {
  designerStore.tempPreviewSchema = version.schema
}

function toggleCompare(versionId: string) {
  if (!compareVersion1.value) {
    compareVersion1.value = versionId
  } else if (!compareVersion2.value && compareVersion1.value !== versionId) {
    compareVersion2.value = versionId
  } else {
    compareVersion1.value = versionId
    compareVersion2.value = null
  }
}

function clearCompare() {
  compareVersion1.value = null
  compareVersion2.value = null
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
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-4xl mx-4 max-h-[80vh] overflow-hidden flex flex-col">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                <History class="text-primary-600" :size="20" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-slate-800">版本历史</h3>
                <p class="text-sm text-slate-500">共 {{ sortedVersions.length }} 个版本</p>
              </div>
            </div>
            <button
              class="p-2 rounded-lg hover:bg-slate-100 transition-colors"
              @click="close"
            >
              <X :size="20" class="text-slate-500" />
            </button>
          </div>

          <div v-if="comparisonResult" class="px-6 py-3 bg-primary-50 border-b border-primary-200 flex-shrink-0">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4 text-sm">
                <span class="font-medium text-primary-700">版本对比结果</span>
                <span class="text-green-600">新增: {{ comparisonResult.added.length }}</span>
                <span class="text-red-600">删除: {{ comparisonResult.removed.length }}</span>
                <span class="text-amber-600">修改: {{ comparisonResult.modified.length }}</span>
              </div>
              <button
                class="text-sm text-primary-600 hover:text-primary-700 font-medium"
                @click="clearCompare"
              >
                清除对比
              </button>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto">
            <div class="p-6 space-y-4">
              <div
                v-for="(version, index) in sortedVersions"
                :key="version.id"
                class="relative"
              >
                <div v-if="index < sortedVersions.length - 1" class="absolute left-5 top-14 w-0.5 h-full bg-slate-200"></div>
                
                <div
                  class="relative bg-white border rounded-xl p-4 transition-all hover:shadow-md"
                  :class="{
                    'border-primary-300 bg-primary-50': compareVersion1 === version.id || compareVersion2 === version.id,
                    'border-slate-200': compareVersion1 !== version.id && compareVersion2 !== version.id
                  }"
                >
                  <div class="flex items-start justify-between">
                    <div class="flex items-start gap-4">
                      <div class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                        :class="{
                          'bg-green-500': version.status === 'published',
                          'bg-blue-500': version.status === 'draft',
                          'bg-slate-400': version.status === 'archived'
                        }"
                      >
                        <GitBranch :size="18" class="text-white" />
                      </div>
                      <div>
                        <div class="flex items-center gap-2">
                          <h4 class="font-semibold text-slate-800">{{ version.name }}</h4>
                          <span
                            class="px-2 py-0.5 text-xs font-medium rounded-full"
                            :class="getStatusBadge(version.status).class"
                          >
                            {{ getStatusBadge(version.status).text }}
                          </span>
                        </div>
                        <p class="text-sm text-slate-500 mt-1">
                          {{ version.description }}
                        </p>
                        <div class="flex items-center gap-4 mt-2 text-xs text-slate-400">
                          <span>{{ formatDate(version.createdAt) }}</span>
                          <span>{{ version.createdBy }}</span>
                        </div>
                      </div>
                    </div>

                    <div class="flex items-center gap-2">
                      <button
                        class="p-2 rounded-lg hover:bg-slate-100 transition-colors text-slate-500 hover:text-slate-700"
                        @click="toggleCompare(version.id)"
                        title="选择对比"
                      >
                        <FileText :size="16" />
                      </button>
                      <button
                        v-if="version.status !== 'draft'"
                        class="p-2 rounded-lg hover:bg-slate-100 transition-colors text-slate-500 hover:text-slate-700"
                        @click="previewVersion(version)"
                        title="预览此版本"
                      >
                        <Eye :size="16" />
                      </button>
                      <button
                        v-if="version.status !== 'draft'"
                        class="p-2 rounded-lg hover:bg-amber-100 transition-colors text-amber-500 hover:text-amber-700"
                        @click="startRollback(version)"
                        title="回滚到此版本"
                      >
                        <RotateCcw :size="16" />
                      </button>
                    </div>
                  </div>

                  <div v-if="version.changelog && version.status !== 'draft'" class="mt-3 pt-3 border-t border-slate-100">
                    <p class="text-sm text-slate-600">
                      <span class="font-medium">更新说明：</span>
                      {{ version.changelog }}
                    </p>
                  </div>
                </div>
              </div>

              <div v-if="sortedVersions.length === 0" class="text-center py-12">
                <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <History :size="32" class="text-slate-400" />
                </div>
                <p class="text-slate-500">暂无版本历史</p>
              </div>
            </div>
          </div>

          <div v-if="compareVersion1 && !compareVersion2" class="px-6 py-3 bg-slate-50 border-t border-slate-200 flex-shrink-0">
            <p class="text-sm text-slate-600">
              <ArrowRight :size="14" class="inline mr-1" />
              请选择第二个版本进行对比
            </p>
          </div>
        </div>
      </div>
    </Transition>

    <Transition name="fade">
      <div
        v-if="showRollbackConfirm"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
        @click.self="showRollbackConfirm = false"
      >
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
          <div class="p-6">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                <RotateCcw class="text-amber-600" :size="20" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-slate-800">确认回滚</h3>
                <p class="text-sm text-slate-500">将回滚到 {{ rollbackVersion?.version }}</p>
              </div>
            </div>
            <p class="text-sm text-slate-600 mb-4">
              回滚后，当前草稿将被替换为选中版本的内容，已发布版本不受影响。
            </p>
            <div>
              <label class="block text-sm font-medium text-slate-700 mb-2">回滚原因</label>
              <input
                v-model="rollbackReason"
                type="text"
                class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                placeholder="可选：填写回滚原因"
              />
            </div>
          </div>
          <div class="flex items-center justify-end gap-3 px-6 py-4 bg-slate-50 border-t border-slate-200 rounded-b-xl">
            <button
              class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
              @click="showRollbackConfirm = false"
            >
              取消
            </button>
            <button
              class="px-4 py-2 text-sm font-medium text-white bg-amber-600 rounded-lg hover:bg-amber-500 transition-colors"
              @click="confirmRollback"
            >
              确认回滚
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
