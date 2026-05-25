<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { X, Printer, Settings, Eye, FileText, LayoutGrid, Plus, Trash2, GripVertical } from 'lucide-vue-next'
import { useDesignerStore } from '@/stores/designer'
import { createDefaultPrintTemplate, printForm } from '@/utils/printTemplate'
import type { PrintTemplate, PrintSection, PrintField } from '@/types/advanced'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const designerStore = useDesignerStore()

const activeTab = ref<'sections' | 'settings'>('sections')
const template = ref<PrintTemplate | null>(null)
const selectedSectionId = ref<string | null>(null)
const showPreview = ref(false)

watch(() => props.modelValue, (val) => {
  if (val) {
    template.value = createDefaultPrintTemplate(designerStore.formSchema)
    if (template.value?.sections[0]) {
      selectedSectionId.value = template.value.sections[0].id
    }
    activeTab.value = 'sections'
    showPreview.value = false
  }
})

function close() {
  emit('update:modelValue', false)
}

const selectedSection = computed(() => {
  return template.value?.sections.find(s => s.id === selectedSectionId.value) || null
})

function selectSection(sectionId: string) {
  selectedSectionId.value = sectionId
}

function toggleSectionVisibility(sectionId: string) {
  if (!template.value) return
  const section = template.value.sections.find(s => s.id === sectionId)
  if (section) {
    section.visible = !section.visible
  }
}

function toggleFieldVisibility(sectionId: string, fieldName: string) {
  if (!template.value) return
  const section = template.value.sections.find(s => s.id === sectionId)
  if (section) {
    const field = section.fields.find(f => f.fieldName === fieldName)
    if (field) {
      field.visible = !field.visible
    }
  }
}

function updateFieldWidth(sectionId: string, fieldName: string, width: 'full' | 'half') {
  if (!template.value) return
  const section = template.value.sections.find(s => s.id === sectionId)
  if (section) {
    const field = section.fields.find(f => f.fieldName === fieldName)
    if (field) {
      field.width = width
    }
  }
}

function updatePageSetup(key: string, value: any) {
  if (!template.value) return
  (template.value.pageSetup as any)[key] = value
}

function handlePrint() {
  if (!template.value) return
  
  const sampleData: Record<string, any> = {}
  designerStore.formSchema.tabs.forEach(tab => {
    tab.fields.forEach(f => {
      sampleData[f.name] = getSampleValue(f.type)
    })
  })
  
  printForm(template.value, sampleData, { showEmptyFields: true })
}

function getSampleValue(type: string): any {
  const samples: Record<string, any> = {
    text: '示例文本内容',
    textarea: '这是一段示例的多行文本内容，用于展示打印效果。',
    number: 12345,
    date: '2024-01-15',
    select: '选项A',
    radio: '选项B',
    checkbox: ['选项1', '选项2'],
    email: 'example@test.com',
    phone: '13800138000'
  }
  return samples[type] || ''
}

function toggleShowLabel(sectionId: string, fieldName: string) {
  if (!template.value) return
  const section = template.value.sections.find(s => s.id === sectionId)
  if (section) {
    const field = section.fields.find(f => f.fieldName === fieldName)
    if (field) {
      field.showLabel = !field.showLabel
    }
  }
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
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-5xl mx-4 max-h-[85vh] overflow-hidden flex flex-col">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200 flex-shrink-0">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                <Printer class="text-primary-600" :size="20" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-slate-800">打印模板设计</h3>
                <p class="text-sm text-slate-500">自定义表单打印样式</p>
              </div>
            </div>
            <button
              class="p-2 rounded-lg hover:bg-slate-100 transition-colors"
              @click="close"
            >
              <X :size="20" class="text-slate-500" />
            </button>
          </div>

          <div class="flex border-b border-slate-200 px-4 flex-shrink-0">
            <button
              class="px-4 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'sections' 
                ? 'border-primary-500 text-primary-600' 
                : 'border-transparent text-slate-500 hover:text-slate-700'"
              @click="activeTab = 'sections'"
            >
              <LayoutGrid :size="16" class="inline mr-1.5" />
              内容布局
            </button>
            <button
              class="px-4 py-3 text-sm font-medium border-b-2 transition-colors"
              :class="activeTab === 'settings' 
                ? 'border-primary-500 text-primary-600' 
                : 'border-transparent text-slate-500 hover:text-slate-700'"
              @click="activeTab = 'settings'"
            >
              <Settings :size="16" class="inline mr-1.5" />
              页面设置
            </button>
          </div>

          <div class="flex-1 flex overflow-hidden">
            <div v-if="activeTab === 'sections'" class="flex-1 flex">
              <div class="w-64 border-r border-slate-200 overflow-y-auto flex-shrink-0">
                <div class="p-4">
                  <h4 class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                    打印分区
                  </h4>
                  <div class="space-y-2">
                    <div
                      v-for="section in template?.sections"
                      :key="section.id"
                      class="p-3 rounded-lg cursor-pointer transition-all border"
                      :class="selectedSectionId === section.id 
                        ? 'bg-primary-50 border-primary-300' 
                        : 'bg-white border-slate-200 hover:border-slate-300'"
                      @click="selectSection(section.id)"
                    >
                      <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                          <GripVertical :size="14" class="text-slate-400" />
                          <span class="text-sm font-medium text-slate-700">{{ section.name }}</span>
                        </div>
                        <button
                          class="p-1 rounded hover:bg-white/50"
                          @click.stop="toggleSectionVisibility(section.id)"
                        >
                          <Eye 
                            :size="14" 
                            :class="section.visible ? 'text-slate-500' : 'text-slate-300'" 
                          />
                        </button>
                      </div>
                      <p class="text-xs text-slate-400 mt-1 ml-6">
                        {{ section.fields.filter(f => f.visible).length }} 个可见字段
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div class="flex-1 overflow-y-auto p-6">
                <div v-if="selectedSection" class="space-y-4">
                  <div class="flex items-center justify-between">
                    <h4 class="font-medium text-slate-800">{{ selectedSection.name }}</h4>
                    <span class="text-sm text-slate-500">
                      共 {{ selectedSection.fields.length }} 个字段
                    </span>
                  </div>

                  <div class="space-y-3">
                    <div
                      v-for="field in selectedSection.fields"
                      :key="field.fieldName"
                      class="p-4 bg-slate-50 rounded-lg border border-slate-200"
                    >
                      <div class="flex items-center justify-between">
                        <div class="flex items-center gap-3">
                          <button
                            class="p-1.5 rounded hover:bg-white transition-colors"
                            @click="toggleFieldVisibility(selectedSection.id, field.fieldName)"
                          >
                            <Eye 
                              :size="16" 
                              :class="field.visible ? 'text-slate-600' : 'text-slate-300'" 
                            />
                          </button>
                          <div>
                            <p class="text-sm font-medium text-slate-700">{{ field.label }}</p>
                            <p class="text-xs text-slate-400">{{ field.fieldName }}</p>
                          </div>
                        </div>
                        <div class="flex items-center gap-2">
                          <div class="flex bg-white rounded-lg border border-slate-200 overflow-hidden">
                            <button
                              class="px-3 py-1.5 text-xs font-medium transition-colors"
                              :class="field.width === 'half' 
                                ? 'bg-primary-500 text-white' 
                                : 'text-slate-600 hover:bg-slate-100'"
                              @click="updateFieldWidth(selectedSection.id, field.fieldName, 'half')"
                            >
                              半宽
                            </button>
                            <button
                              class="px-3 py-1.5 text-xs font-medium transition-colors"
                              :class="field.width === 'full' 
                                ? 'bg-primary-500 text-white' 
                                : 'text-slate-600 hover:bg-slate-100'"
                              @click="updateFieldWidth(selectedSection.id, field.fieldName, 'full')"
                            >
                              全宽
                            </button>
                          </div>
                          <button
                            class="p-1.5 rounded hover:bg-white transition-colors"
                            @click="toggleShowLabel(selectedSection.id, field.fieldName)"
                            :class="field.showLabel ? 'text-slate-600' : 'text-slate-300'"
                            title="显示标签"
                          >
                            <FileText :size="16" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-else class="text-center py-12">
                  <p class="text-slate-500">请选择一个分区</p>
                </div>
              </div>
            </div>

            <div v-if="activeTab === 'settings'" class="flex-1 overflow-y-auto p-6">
              <div class="max-w-lg">
                <h4 class="font-medium text-slate-800 mb-4">页面设置</h4>
                
                <div class="space-y-6">
                  <div class="grid grid-cols-2 gap-4">
                    <div>
                      <label class="block text-sm font-medium text-slate-700 mb-2">纸张大小</label>
                      <select
                        :value="template?.pageSetup.paperSize"
                        class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        @change="updatePageSetup('paperSize', ($event.target as HTMLSelectElement).value)"
                      >
                        <option value="A4">A4</option>
                        <option value="A3">A3</option>
                        <option value="Letter">Letter</option>
                        <option value="Legal">Legal</option>
                      </select>
                    </div>
                    <div>
                      <label class="block text-sm font-medium text-slate-700 mb-2">方向</label>
                      <select
                        :value="template?.pageSetup.orientation"
                        class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        @change="updatePageSetup('orientation', ($event.target as HTMLSelectElement).value)"
                      >
                        <option value="portrait">纵向</option>
                        <option value="landscape">横向</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-slate-700 mb-3">边距 (mm)</label>
                    <div class="grid grid-cols-4 gap-3">
                      <div>
                        <label class="block text-xs text-slate-500 mb-1">上</label>
                        <input
                          type="number"
                          :value="template?.pageSetup.marginTop"
                          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                          @change="updatePageSetup('marginTop', Number(($event.target as HTMLInputElement).value))"
                        />
                      </div>
                      <div>
                        <label class="block text-xs text-slate-500 mb-1">下</label>
                        <input
                          type="number"
                          :value="template?.pageSetup.marginBottom"
                          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                          @change="updatePageSetup('marginBottom', Number(($event.target as HTMLInputElement).value))"
                        />
                      </div>
                      <div>
                        <label class="block text-xs text-slate-500 mb-1">左</label>
                        <input
                          type="number"
                          :value="template?.pageSetup.marginLeft"
                          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                          @change="updatePageSetup('marginLeft', Number(($event.target as HTMLInputElement).value))"
                        />
                      </div>
                      <div>
                        <label class="block text-xs text-slate-500 mb-1">右</label>
                        <input
                          type="number"
                          :value="template?.pageSetup.marginRight"
                          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                          @change="updatePageSetup('marginRight', Number(($event.target as HTMLInputElement).value))"
                        />
                      </div>
                    </div>
                  </div>

                  <div class="space-y-3">
                    <label class="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <span class="text-sm text-slate-700">显示页码</span>
                      <input
                        type="checkbox"
                        :checked="template?.pageSetup.showPageNumbers"
                        class="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                        @change="updatePageSetup('showPageNumbers', ($event.target as HTMLInputElement).checked)"
                      />
                    </label>
                    <label class="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                      <span class="text-sm text-slate-700">显示水印</span>
                      <input
                        type="checkbox"
                        :checked="template?.pageSetup.showWatermark"
                        class="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                        @change="updatePageSetup('showWatermark', ($event.target as HTMLInputElement).checked)"
                      />
                    </label>
                    <div v-if="template?.pageSetup.showWatermark">
                      <label class="block text-sm font-medium text-slate-700 mb-2">水印文字</label>
                      <input
                        type="text"
                        :value="template?.pageSetup.watermarkText"
                        placeholder="请输入水印文字"
                        class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        @change="updatePageSetup('watermarkText', ($event.target as HTMLInputElement).value)"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-between px-6 py-4 bg-slate-50 border-t border-slate-200 flex-shrink-0">
            <div class="text-sm text-slate-500">
              修改将实时反映在打印效果中
            </div>
            <div class="flex items-center gap-3">
              <button
                class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                @click="close"
              >
                取消
              </button>
              <button
                class="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-500 transition-colors flex items-center gap-2"
                @click="handlePrint"
              >
                <Printer :size="16" />
                预览并打印
              </button>
            </div>
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
