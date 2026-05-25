<script setup lang="ts">
import { computed } from 'vue'
import { Trash2, GripVertical } from 'lucide-vue-next'
import type { FormField } from '@/types/form'
import { useDesignerStore } from '@/stores/designer'

const props = defineProps<{
  field: FormField
}>()

const store = useDesignerStore()

const isSelected = computed(() => store.selectedFieldId === props.field.id)

function handleClick(e: MouseEvent) {
  e.stopPropagation()
  store.selectField(props.field.id)
}

function handleDelete(e: MouseEvent) {
  e.stopPropagation()
  store.deleteField(props.field.id)
}

const fieldTypeLabels: Record<string, string> = {
  input: '单行输入',
  textarea: '多行输入',
  number: '数字输入',
  select: '下拉选择',
  radio: '单选框',
  checkbox: '多选框',
  switch: '开关',
  date: '日期选择',
  time: '时间选择',
  rate: '评分',
  slider: '滑块',
  divider: '分割线',
  text: '静态文本'
}
</script>

<template>
  <div
    class="designer-field relative group cursor-pointer transition-all duration-200"
    :class="{ 'ring-2 ring-primary-500 ring-offset-2 rounded-lg': isSelected }"
    @click="handleClick"
  >
    <div class="flex items-center gap-2 p-3 bg-white border border-slate-200 rounded-lg hover:border-primary-400 hover:shadow-sm">
      <div class="cursor-move text-slate-400 hover:text-slate-600">
        <GripVertical :size="16" />
      </div>
      
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <span class="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded">
            {{ fieldTypeLabels[field.type] }}
          </span>
          <span class="text-xs text-slate-400">{{ field.name }}</span>
        </div>
        <div class="font-medium text-slate-700 truncate mt-1">
          {{ field.label }}
          <span v-if="field.required" class="text-red-500 ml-1">*</span>
        </div>
        <div v-if="field.placeholder" class="text-sm text-slate-400 truncate mt-0.5">
          {{ field.placeholder }}
        </div>
      </div>

      <button
        class="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded transition-all"
        @click="handleDelete"
      >
        <Trash2 :size="16" />
      </button>
    </div>

    <div v-if="isSelected" class="absolute -top-1 -right-1 -left-1 -bottom-1 pointer-events-none border-2 border-primary-500 rounded-lg"></div>
  </div>
</template>

<style scoped>
.designer-field {
  user-select: none;
}
</style>
