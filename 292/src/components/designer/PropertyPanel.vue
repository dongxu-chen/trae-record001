<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Settings, ShieldCheck, Calculator, Eye, AlertTriangle, FunctionSquare, ChevronDown, ChevronUp } from 'lucide-vue-next'
import { useDesignerStore } from '@/stores/designer'
import type { ValidationRule } from '@/types/form'
import { functionDefinitions } from '@/utils/formulaEngine'
import { validateFieldDependencies, checkDependencies } from '@/utils/dependencyChecker'

const store = useDesignerStore()
const activeTab = ref('basic')
const showFunctionList = ref(false)
const formulaInput = ref('')
const dependencyError = ref<string | null>(null)
const conditionalDependencyError = ref<string | null>(null)

const field = computed(() => store.selectedField)

const tabs = [
  { key: 'basic', label: '基础属性', icon: Settings },
  { key: 'validation', label: '数据校验', icon: ShieldCheck },
  { key: 'formula', label: '公式计算', icon: Calculator },
  { key: 'conditional', label: '条件显隐', icon: Eye }
]

watch(() => field.value?.formula?.expression, (expr) => {
  formulaInput.value = expr || ''
  dependencyError.value = null
}, { immediate: true })

function checkFormulaDependencies() {
  if (!field.value || !formulaInput.value) {
    dependencyError.value = null
    return true
  }
  
  const result = validateFieldDependencies(
    store.formSchema,
    field.value.name,
    formulaInput.value
  )
  
  if (!result.valid) {
    dependencyError.value = result.error
    return false
  }
  
  dependencyError.value = null
  return true
}

function applyFormula() {
  if (!field.value) return
  
  if (!checkFormulaDependencies()) {
    return
  }
  
  updateField({ 
    formula: formulaInput.value 
      ? { expression: formulaInput.value, dependencies: [] } 
      : undefined 
  })
}

function insertFunction(funcName: string) {
  const func = functionDefinitions.find(f => f.name === funcName)
  if (func) {
    formulaInput.value += `${funcName}()`
    showFunctionList.value = false
  }
}

const allFieldsByName = computed(() => {
  const fields: { name: string; label: string }[] = []
  store.formSchema.tabs.forEach(tab => {
    tab.fields.forEach(f => {
      if (f.name !== field.value?.name) {
        fields.push({ name: f.name, label: f.label })
      }
    })
  })
  return fields
})

function updateField(updates: Record<string, any>) {
  if (field.value) {
    store.updateField(field.value.id, updates)
  }
}

function toggleRequired() {
  if (field.value) {
    updateField({ required: !field.value.required })
  }
}

function addValidation() {
  if (field.value) {
    const validation = field.value.validation || []
    updateField({
      validation: [
        ...validation,
        { type: 'required', message: '此字段为必填项' }
      ]
    })
  }
}

function removeValidation(index: number) {
  if (field.value?.validation) {
    const validation = [...field.value.validation]
    validation.splice(index, 1)
    updateField({ validation })
  }
}

function updateValidation(index: number, rule: Partial<ValidationRule>) {
  if (field.value?.validation) {
    const validation = [...field.value.validation]
    validation[index] = { ...validation[index], ...rule }
    updateField({ validation })
  }
}

const allFields = computed(() => {
  const fields: { id: string; label: string }[] = []
  store.formSchema.tabs.forEach(tab => {
    tab.fields.forEach(f => {
      if (f.id !== field.value?.id) {
        fields.push({ id: f.id, label: f.label })
      }
    })
  })
  return fields
})

function toggleConditional(type: 'show' | 'disable') {
  if (!field.value) return
  
  const conditional = field.value.conditional || {}
  if (conditional[type]) {
    const newConditional = { ...conditional }
    delete newConditional[type]
    updateField({ conditional: newConditional })
  } else {
    const firstField = allFields.value[0]
    updateField({
      conditional: {
        ...conditional,
        [type]: {
          field: firstField?.id || '',
          operator: '==',
          value: ''
        }
      }
    })
  }
}

function updateConditional(type: 'show' | 'disable', key: string, value: any) {
  if (!field.value?.conditional) return
  
  const conditional = { ...field.value.conditional }
  if (conditional[type]) {
    conditional[type] = { ...conditional[type], [key]: value }
    updateField({ conditional })
  }
}

function updateConditionalWithCheck(type: 'show' | 'disable', key: string, value: any) {
  if (!field.value) return
  
  if (key === 'field') {
    const tempConditional = { ...(field.value.conditional || {}) }
    if (tempConditional[type]) {
      tempConditional[type] = { ...tempConditional[type], field: value }
    }
    
    const tempSchema = JSON.parse(JSON.stringify(store.formSchema))
    for (const tab of tempSchema.tabs) {
      const f = tab.fields.find((f: any) => f.id === field.value!.id)
      if (f) {
        f.conditional = tempConditional
        break
      }
    }
    
    const result = checkDependencies(tempSchema)
    
    if (result.hasCircularDependency) {
      conditionalDependencyError.value = `检测到循环依赖: ${result.circularDependencies[0].path.join(' → ')}`
      return
    }
  }
  
  conditionalDependencyError.value = null
  updateConditional(type, key, value)
}
</script>

<template>
  <div class="property-panel h-full flex flex-col bg-white border-l border-slate-200">
    <div class="p-4 border-b border-slate-200">
      <h2 class="font-semibold text-slate-800">属性配置</h2>
      <p v-if="!field" class="text-xs text-slate-500 mt-1">请选择一个组件</p>
    </div>

    <div v-if="field" class="flex-1 flex flex-col overflow-hidden">
      <div class="flex border-b border-slate-200">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="flex-1 px-1 py-2 text-xs font-medium transition-colors"
          :class="activeTab === tab.key 
            ? 'text-primary-600 border-b-2 border-primary-500 bg-primary-50' 
            : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'"
          @click="activeTab = tab.key"
        >
          <component :is="tab.icon" :size="14" class="mx-auto mb-0.5" />
          {{ tab.label }}
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-4 space-y-4">
        <div v-if="activeTab === 'basic'" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-slate-700 mb-1">字段名称</label>
            <input
              type="text"
              :value="field.label"
              @input="updateField({ label: ($event.target as HTMLInputElement).value })"
              class="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          
          <div>
            <label class="block text-xs font-medium text-slate-700 mb-1">字段标识</label>
            <input
              type="text"
              :value="field.name"
              @input="updateField({ name: ($event.target as HTMLInputElement).value })"
              class="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div v-if="field.type !== 'divider' && field.type !== 'text' && field.type !== 'switch'">
            <label class="block text-xs font-medium text-slate-700 mb-1">占位文本</label>
            <input
              type="text"
              :value="field.placeholder || ''"
              @input="updateField({ placeholder: ($event.target as HTMLInputElement).value })"
              class="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div v-if="field.type !== 'divider' && field.type !== 'text'">
            <label class="block text-xs font-medium text-slate-700 mb-1">默认值</label>
            <input
              type="text"
              :value="field.defaultValue ?? ''"
              @input="updateField({ defaultValue: ($event.target as HTMLInputElement).value })"
              class="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div v-if="field.type !== 'divider' && field.type !== 'text'" class="flex items-center justify-between">
            <span class="text-xs font-medium text-slate-700">必填字段</span>
            <button
              class="relative w-10 h-6 rounded-full transition-colors"
              :class="field.required ? 'bg-primary-500' : 'bg-slate-300'"
              @click="toggleRequired"
            >
              <span
                class="absolute top-1 w-4 h-4 bg-white rounded-full transition-transform shadow"
                :class="field.required ? 'translate-x-5' : 'translate-x-1'"
              ></span>
            </button>
          </div>
        </div>

        <div v-if="activeTab === 'validation'" class="space-y-4">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-slate-700">校验规则</span>
            <button
              class="text-xs text-primary-600 hover:text-primary-700"
              @click="addValidation"
            >
              + 添加规则
            </button>
          </div>

          <div v-if="!field.validation?.length" class="text-center py-8 text-slate-400 text-sm">
            暂无校验规则
          </div>

          <div
            v-for="(rule, index) in field.validation || []"
            :key="index"
            class="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2"
          >
            <div class="flex items-center justify-between">
              <select
                :value="rule.type"
                @change="updateValidation(index, { type: ($event.target as HTMLSelectElement).value as any })"
                class="px-2 py-1 text-sm border border-slate-300 rounded"
              >
                <option value="required">必填</option>
                <option value="min">最小值</option>
                <option value="max">最大值</option>
                <option value="email">邮箱格式</option>
                <option value="pattern">正则表达式</option>
              </select>
              <button
                class="text-red-500 hover:text-red-600 text-xs"
                @click="removeValidation(index)"
              >
                删除
              </button>
            </div>
            
            <div v-if="rule.type === 'min' || rule.type === 'max'">
              <input
                type="number"
                :value="rule.value"
                @input="updateValidation(index, { value: Number(($event.target as HTMLInputElement).value) })"
                class="w-full px-2 py-1 text-sm border border-slate-300 rounded"
                :placeholder="rule.type === 'min' ? '最小值' : '最大值'"
              />
            </div>
            
            <div v-if="rule.type === 'pattern'">
              <input
                type="text"
                :value="rule.value || ''"
                @input="updateValidation(index, { value: ($event.target as HTMLInputElement).value })"
                class="w-full px-2 py-1 text-sm border border-slate-300 rounded"
                placeholder="正则表达式"
              />
            </div>
            
            <input
              type="text"
              :value="rule.message"
              @input="updateValidation(index, { message: ($event.target as HTMLInputElement).value })"
              class="w-full px-2 py-1 text-sm border border-slate-300 rounded"
              placeholder="错误提示信息"
            />
          </div>
        </div>

        <div v-if="activeTab === 'formula'" class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-slate-700 mb-1">计算公式</label>
            <textarea
              v-model="formulaInput"
              @blur="checkFormulaDependencies"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono"
              :class="dependencyError ? 'border-red-300' : 'border-slate-300'"
              rows="4"
              placeholder="例如: SUM(field_a, field_b) * 2"
            ></textarea>
          </div>

          <div v-if="dependencyError" class="p-3 bg-red-50 border border-red-200 rounded-lg">
            <div class="flex items-start gap-2">
              <AlertTriangle :size="16" class="text-red-500 flex-shrink-0 mt-0.5" />
              <p class="text-xs text-red-600">{{ dependencyError }}</p>
            </div>
          </div>

          <div class="flex gap-2">
            <button
              class="flex-1 px-3 py-2 text-sm bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              :disabled="!!dependencyError"
              @click="applyFormula"
            >
              应用公式
            </button>
            <button
              class="flex items-center gap-1 px-3 py-2 text-sm border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
              @click="showFunctionList = !showFunctionList"
            >
              <FunctionSquare :size="16" />
              <component :is="showFunctionList ? ChevronUp : ChevronDown" :size="16" />
            </button>
          </div>

          <div v-if="showFunctionList" class="border border-slate-200 rounded-lg overflow-hidden">
            <div class="max-h-48 overflow-y-auto">
              <div
                v-for="func in functionDefinitions"
                :key="func.name"
                class="px-3 py-2 hover:bg-slate-50 cursor-pointer border-b border-slate-100 last:border-0"
                @click="insertFunction(func.name)"
              >
                <div class="text-sm font-medium text-slate-700">{{ func.name }}()</div>
                <div class="text-xs text-slate-500">{{ func.description }}</div>
                <div class="text-xs text-primary-500 font-mono mt-1">{{ func.example }}</div>
              </div>
            </div>
          </div>

          <div v-if="allFieldsByName.length > 0" class="p-3 bg-slate-50 rounded-lg">
            <p class="text-xs font-medium text-slate-700 mb-2">可用字段</p>
            <div class="flex flex-wrap gap-1">
              <button
                v-for="f in allFieldsByName"
                :key="f.name"
                class="px-2 py-1 text-xs bg-white border border-slate-200 rounded hover:bg-primary-50 hover:border-primary-300 transition-colors"
                @click="formulaInput += f.name"
                :title="f.label"
              >
                {{ f.name }}
              </button>
            </div>
          </div>

          <p class="text-xs text-slate-500">
            <strong>支持函数：</strong>SUM、AVG、MAX、MIN、IF、ROUND、ABS、FLOOR、CEIL、POW、SQRT、LEN、CONCAT、LEFT、RIGHT、MID、LOWER、UPPER、TRIM、AND、OR、NOT、TODAY、YEAR、MONTH、DAY
          </p>
        </div>

        <div v-if="activeTab === 'conditional'" class="space-y-4">
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-700">条件显示</span>
              <button
                class="relative w-10 h-6 rounded-full transition-colors"
                :class="field.conditional?.show ? 'bg-primary-500' : 'bg-slate-300'"
                @click="toggleConditional('show')"
              >
                <span
                  class="absolute top-1 w-4 h-4 bg-white rounded-full transition-transform shadow"
                  :class="field.conditional?.show ? 'translate-x-5' : 'translate-x-1'"
                ></span>
              </button>
            </div>
            
            <div v-if="field.conditional?.show" class="p-3 bg-slate-50 rounded-lg space-y-2">
              <select
                :value="field.conditional.show.field"
                @change="updateConditionalWithCheck('show', 'field', ($event.target as HTMLSelectElement).value)"
                class="w-full px-2 py-1 text-sm border border-slate-300 rounded"
              >
                <option v-for="f in allFieldsByName" :key="f.name" :value="f.name">
                  {{ f.label }} ({{ f.name }})
                </option>
              </select>
              <select
                :value="field.conditional.show.operator"
                @change="updateConditional('show', 'operator', ($event.target as HTMLSelectElement).value)"
                class="w-full px-2 py-1 text-sm border border-slate-300 rounded"
              >
                <option value="==">等于</option>
                <option value="!=">不等于</option>
                <option value=">">大于</option>
                <option value="<">小于</option>
                <option value="contains">包含</option>
              </select>
              <input
                type="text"
                :value="field.conditional.show.value"
                @input="updateConditional('show', 'value', ($event.target as HTMLInputElement).value)"
                class="w-full px-2 py-1 text-sm border border-slate-300 rounded"
                placeholder="值"
              />
            </div>
          </div>

          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-slate-700">条件禁用</span>
              <button
                class="relative w-10 h-6 rounded-full transition-colors"
                :class="field.conditional?.disable ? 'bg-primary-500' : 'bg-slate-300'"
                @click="toggleConditional('disable')"
              >
                <span
                  class="absolute top-1 w-4 h-4 bg-white rounded-full transition-transform shadow"
                  :class="field.conditional?.disable ? 'translate-x-5' : 'translate-x-1'"
                ></span>
              </button>
            </div>
            
            <div v-if="field.conditional?.disable" class="p-3 bg-slate-50 rounded-lg space-y-2">
              <select
                :value="field.conditional.disable.field"
                @change="updateConditionalWithCheck('disable', 'field', ($event.target as HTMLSelectElement).value)"
                class="w-full px-2 py-1 text-sm border border-slate-300 rounded"
              >
                <option v-for="f in allFieldsByName" :key="f.name" :value="f.name">
                  {{ f.label }} ({{ f.name }})
                </option>
              </select>
              <select
                :value="field.conditional.disable.operator"
                @change="updateConditional('disable', 'operator', ($event.target as HTMLSelectElement).value)"
                class="w-full px-2 py-1 text-sm border border-slate-300 rounded"
              >
                <option value="==">等于</option>
                <option value="!=">不等于</option>
                <option value=">">大于</option>
                <option value="<">小于</option>
                <option value="contains">包含</option>
              </select>
              <input
                type="text"
                :value="field.conditional.disable.value"
                @input="updateConditional('disable', 'value', ($event.target as HTMLInputElement).value)"
                class="w-full px-2 py-1 text-sm border border-slate-300 rounded"
                placeholder="值"
              />
            </div>
          </div>

          <div v-if="conditionalDependencyError" class="p-3 bg-red-50 border border-red-200 rounded-lg">
            <div class="flex items-start gap-2">
              <AlertTriangle :size="16" class="text-red-500 flex-shrink-0 mt-0.5" />
              <p class="text-xs text-red-600">{{ conditionalDependencyError }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex-1 flex items-center justify-center text-slate-400">
      <div class="text-center">
        <Settings :size="32" class="mx-auto mb-2 opacity-50" />
        <p class="text-sm">选择组件以编辑属性</p>
      </div>
    </div>
  </div>
</template>
