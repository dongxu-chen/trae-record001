<script setup lang="ts">
import { ref, computed, watch, reactive, nextTick } from 'vue'
import type { FormSchema, FormField, ConditionalExpression } from '@/types/form'
import { useDesignerStore } from '@/stores/designer'
import { evaluateExpression } from '@/utils/formulaEngine'
import { checkDependencies } from '@/utils/dependencyChecker'

const props = defineProps<{
  schema?: FormSchema
}>()

const store = useDesignerStore()
const formData = reactive<Record<string, any>>({})
const errors = reactive<Record<string, string>>({})
const formulaErrors = reactive<Record<string, string>>({})
const activeTabIndex = ref(0)
const isCalculating = ref(false)

const schema = computed(() => props.schema || store.formSchema)

const currentTab = computed(() => schema.value.tabs[activeTabIndex.value])

const hasCircularDependency = computed(() => {
  const result = checkDependencies(schema.value)
  return result.hasCircularDependency
})

function initFormData() {
  Object.keys(formData).forEach(key => delete formData[key])
  Object.keys(errors).forEach(key => delete errors[key])
  Object.keys(formulaErrors).forEach(key => delete formulaErrors[key])
  
  schema.value.tabs.forEach(tab => {
    tab.fields.forEach(field => {
      if (field.defaultValue !== undefined) {
        formData[field.name] = field.defaultValue
      }
    })
  })
  
  nextTick(() => calculateAllFormulas())
}

watch(() => schema.value, () => {
  initFormData()
}, { immediate: true, deep: true })

function evaluateCondition(condition: ConditionalExpression | undefined): boolean {
  if (!condition) return true
  
  const fieldValue = formData[condition.field]
  const compareValue = condition.value
  
  switch (condition.operator) {
    case '==':
      return fieldValue == compareValue
    case '!=':
      return fieldValue != compareValue
    case '>':
      return fieldValue > compareValue
    case '<':
      return fieldValue < compareValue
    case '>=':
      return fieldValue >= compareValue
    case '<=':
      return fieldValue <= compareValue
    case 'contains':
      return String(fieldValue || '').includes(String(compareValue))
    default:
      return true
  }
}

function isFieldVisible(field: FormField): boolean {
  if (!field.conditional?.show) return true
  return evaluateCondition(field.conditional.show)
}

function isFieldDisabled(field: FormField): boolean {
  if (!field.conditional?.disable) return false
  return evaluateCondition(field.conditional.disable)
}

function calculateAllFormulas() {
  if (isCalculating.value) return
  isCalculating.value = true
  
  const topologicalOrder = getCalculationOrder()
  
  let hasChanges = true
  let iterations = 0
  const maxIterations = 10
  
  while (hasChanges && iterations < maxIterations) {
    hasChanges = false
    iterations++
    
    topologicalOrder.forEach(fieldName => {
      const field = findFieldByName(fieldName)
      if (field?.formula?.expression && isFieldVisible(field)) {
        const result = evaluateExpression(field.formula.expression, formData, schema.value)
        if (result.error) {
          formulaErrors[field.name] = result.error
        } else {
          delete formulaErrors[field.name]
          if (result.result !== formData[field.name]) {
            formData[field.name] = result.result
            hasChanges = true
          }
        }
      }
    })
  }
  
  isCalculating.value = false
}

function getCalculationOrder(): string[] {
  const dependencyGraph = new Map<string, string[]>()
  const allFields: string[] = []
  
  schema.value.tabs.forEach(tab => {
    tab.fields.forEach(field => {
      allFields.push(field.name)
      if (field.formula?.expression) {
        const deps = extractFieldDependencies(field.formula.expression)
        dependencyGraph.set(field.name, deps)
      } else {
        dependencyGraph.set(field.name, [])
      }
    })
  })
  
  const inDegree = new Map<string, number>()
  allFields.forEach(name => inDegree.set(name, 0))
  
  dependencyGraph.forEach((deps) => {
    deps.forEach(dep => {
      if (inDegree.has(dep)) {
        inDegree.set(dep, (inDegree.get(dep) || 0) + 1)
      }
    })
  })
  
  const queue: string[] = []
  inDegree.forEach((degree, name) => {
    if (degree === 0) queue.push(name)
  })
  
  const result: string[] = []
  while (queue.length > 0) {
    const node = queue.shift()!
    result.push(node)
    
    dependencyGraph.forEach((deps, name) => {
      if (deps.includes(node)) {
        const newDegree = (inDegree.get(name) || 0) - 1
        inDegree.set(name, newDegree)
        if (newDegree === 0) queue.push(name)
      }
    })
  }
  
  return result
}

function extractFieldDependencies(expression: string): string[] {
  const deps: string[] = []
  const fieldNames = new Set<string>()
  
  schema.value.tabs.forEach(tab => {
    tab.fields.forEach(f => fieldNames.add(f.name))
  })
  
  Array.from(fieldNames).sort((a, b) => b.length - a.length).forEach(name => {
    if (new RegExp(`\\b${name}\\b`).test(expression)) {
      deps.push(name)
    }
  })
  
  return deps
}

function findFieldByName(name: string): FormField | null {
  for (const tab of schema.value.tabs) {
    const field = tab.fields.find(f => f.name === name)
    if (field) return field
  }
  return null
}

watch(formData, () => {
  if (!isCalculating.value) {
    nextTick(() => calculateAllFormulas())
  }
}, { deep: true })

function validateField(field: FormField): string | null {
  const value = formData[field.name]
  
  if (field.required && (value === undefined || value === '' || value === null)) {
    return `${field.label}为必填项`
  }
  
  if (field.validation) {
    for (const rule of field.validation) {
      switch (rule.type) {
        case 'required':
          if (value === undefined || value === '' || value === null) {
            return rule.message
          }
          break
        case 'email':
          if (value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
            return rule.message
          }
          break
        case 'min':
          if (value !== undefined && value !== '' && Number(value) < rule.value) {
            return rule.message
          }
          break
        case 'max':
          if (value !== undefined && value !== '' && Number(value) > rule.value) {
            return rule.message
          }
          break
        case 'pattern':
          if (value && rule.value && !new RegExp(rule.value).test(value)) {
            return rule.message
          }
          break
      }
    }
  }
  
  return null
}

function validateForm(): boolean {
  let isValid = true
  
  schema.value.tabs.forEach(tab => {
    tab.fields.forEach(field => {
      const error = validateField(field)
      if (error) {
        errors[field.name] = error
        isValid = false
      } else {
        delete errors[field.name]
      }
    })
  })
  
  return isValid
}

function handleSubmit() {
  if (validateForm()) {
    emit('submit', { ...formData })
  }
}

function handleFieldChange(field: FormField, value: any) {
  formData[field.name] = value
  delete errors[field.name]
}

const emit = defineEmits<{
  submit: [data: Record<string, any>]
}>()

defineExpose({
  formData,
  validateForm,
  errors
})
</script>

<template>
  <div class="form-renderer">
    <div v-if="schema.tabs.length > 1" class="flex border-b border-slate-200 mb-6">
      <button
        v-for="(tab, index) in schema.tabs"
        :key="tab.id"
        class="px-4 py-2 text-sm font-medium transition-colors"
        :class="activeTabIndex === index 
          ? 'text-primary-600 border-b-2 border-primary-500' 
          : 'text-slate-500 hover:text-slate-700'"
        @click="activeTabIndex = index"
      >
        {{ tab.name }}
      </button>
    </div>

    <div v-if="currentTab" class="space-y-5">
      <template v-for="field in currentTab.fields" :key="field.id">
        <div
          v-if="isFieldVisible(field)"
          class="form-field"
        >
          <label v-if="field.type !== 'divider' && field.type !== 'text'" class="block text-sm font-medium text-slate-700 mb-1.5">
            {{ field.label }}
            <span v-if="field.required" class="text-red-500 ml-0.5">*</span>
          </label>

          <div v-if="field.type === 'input'">
            <input
              type="text"
              :value="formData[field.name] || ''"
              :placeholder="field.placeholder"
              :disabled="isFieldDisabled(field)"
              @input="handleFieldChange(field, ($event.target as HTMLInputElement).value)"
              class="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
              :class="errors[field.name] ? 'border-red-300' : 'border-slate-300'"
            />
          </div>

          <div v-else-if="field.type === 'textarea'">
            <textarea
              :value="formData[field.name] || ''"
              :placeholder="field.placeholder"
              :disabled="isFieldDisabled(field)"
              :rows="field.props?.rows || 4"
              @input="handleFieldChange(field, ($event.target as HTMLTextAreaElement).value)"
              class="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none transition-all"
              :class="errors[field.name] ? 'border-red-300' : 'border-slate-300'"
            ></textarea>
          </div>

          <div v-else-if="field.type === 'number'">
            <input
              type="number"
              :value="formData[field.name] || ''"
              :placeholder="field.placeholder"
              :disabled="isFieldDisabled(field)"
              :min="field.props?.min"
              :max="field.props?.max"
              @input="handleFieldChange(field, Number(($event.target as HTMLInputElement).value))"
              class="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
              :class="errors[field.name] ? 'border-red-300' : 'border-slate-300'"
            />
          </div>

          <div v-else-if="field.type === 'select'">
            <select
              :value="formData[field.name] || ''"
              :disabled="isFieldDisabled(field)"
              @change="handleFieldChange(field, ($event.target as HTMLSelectElement).value)"
              class="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all bg-white"
              :class="errors[field.name] ? 'border-red-300' : 'border-slate-300'"
            >
              <option value="">{{ field.placeholder || '请选择' }}</option>
              <option v-for="opt in field.props?.options" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div v-else-if="field.type === 'radio'" class="flex flex-wrap gap-4">
            <label
              v-for="opt in field.props?.options"
              :key="opt.value"
              class="flex items-center gap-2 cursor-pointer"
            >
              <input
                type="radio"
                :value="opt.value"
                :checked="formData[field.name] === opt.value"
                :disabled="isFieldDisabled(field)"
                @change="handleFieldChange(field, opt.value)"
                class="w-4 h-4 text-primary-600"
              />
              <span class="text-sm text-slate-700">{{ opt.label }}</span>
            </label>
          </div>

          <div v-else-if="field.type === 'checkbox'" class="flex flex-wrap gap-4">
            <label
              v-for="opt in field.props?.options"
              :key="opt.value"
              class="flex items-center gap-2 cursor-pointer"
            >
              <input
                type="checkbox"
                :checked="(formData[field.name] || []).includes(opt.value)"
                :disabled="isFieldDisabled(field)"
                @change="(e) => {
                  const arr = formData[field.name] || []
                  const checked = (e.target as HTMLInputElement).checked
                  if (checked) {
                    handleFieldChange(field, [...arr, opt.value])
                  } else {
                    handleFieldChange(field, arr.filter((v: string) => v !== opt.value))
                  }
                }"
                class="w-4 h-4 text-primary-600 rounded"
              />
              <span class="text-sm text-slate-700">{{ opt.label }}</span>
            </label>
          </div>

          <div v-else-if="field.type === 'switch'" class="flex items-center justify-between">
            <span class="text-sm text-slate-700">{{ field.label }}</span>
            <button
              class="relative w-11 h-6 rounded-full transition-colors"
              :class="formData[field.name] ? 'bg-primary-500' : 'bg-slate-300'"
              :disabled="isFieldDisabled(field)"
              @click="handleFieldChange(field, !formData[field.name])"
            >
              <span
                class="absolute top-1 w-4 h-4 bg-white rounded-full transition-transform shadow"
                :class="formData[field.name] ? 'translate-x-6' : 'translate-x-1'"
              ></span>
            </button>
          </div>

          <div v-else-if="field.type === 'date'">
            <input
              type="date"
              :value="formData[field.name] || ''"
              :disabled="isFieldDisabled(field)"
              @input="handleFieldChange(field, ($event.target as HTMLInputElement).value)"
              class="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
              :class="errors[field.name] ? 'border-red-300' : 'border-slate-300'"
            />
          </div>

          <div v-else-if="field.type === 'time'">
            <input
              type="time"
              :value="formData[field.name] || ''"
              :disabled="isFieldDisabled(field)"
              @input="handleFieldChange(field, ($event.target as HTMLInputElement).value)"
              class="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
              :class="errors[field.name] ? 'border-red-300' : 'border-slate-300'"
            />
          </div>

          <div v-else-if="field.type === 'rate'" class="flex gap-1">
            <button
              v-for="i in (field.props?.max || 5)"
              :key="i"
              type="button"
              class="text-2xl transition-colors"
              :class="i <= (formData[field.name] || 0) ? 'text-yellow-400' : 'text-slate-300'"
              :disabled="isFieldDisabled(field)"
              @click="handleFieldChange(field, i)"
            >
              ★
            </button>
          </div>

          <div v-else-if="field.type === 'slider'">
            <input
              type="range"
              :min="field.props?.min || 0"
              :max="field.props?.max || 100"
              :value="formData[field.name] || (field.props?.min || 0)"
              :disabled="isFieldDisabled(field)"
              @input="handleFieldChange(field, Number(($event.target as HTMLInputElement).value))"
              class="w-full accent-primary-500"
            />
            <div class="text-sm text-slate-500 text-right">{{ formData[field.name] || (field.props?.min || 0) }}</div>
          </div>

          <div v-else-if="field.type === 'divider'" class="py-2">
            <div class="flex items-center gap-3">
              <div class="flex-1 h-px bg-slate-200"></div>
              <span v-if="field.props?.text" class="text-sm text-slate-500">{{ field.props.text }}</span>
              <div class="flex-1 h-px bg-slate-200"></div>
            </div>
          </div>

          <div v-else-if="field.type === 'text'" class="text-sm text-slate-600">
            {{ field.props?.content }}
          </div>

          <p v-if="errors[field.name]" class="mt-1 text-xs text-red-500">
            {{ errors[field.name] }}
          </p>
        </div>
      </template>
    </div>

    <div class="mt-8 flex justify-end">
      <button
        type="button"
        class="px-6 py-2.5 bg-primary-500 text-white rounded-lg font-medium hover:bg-primary-600 transition-colors shadow-sm"
        @click="handleSubmit"
      >
        提交表单
      </button>
    </div>
  </div>
</template>
