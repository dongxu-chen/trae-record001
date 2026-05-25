<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { X, GitMerge, Plus, Trash2, Settings, GripVertical, User, CheckCircle2, ArrowRight } from 'lucide-vue-next'
import { createWorkflowDefinition, createWorkflowStep, validateWorkflowDefinition } from '@/utils/workflowEngine'
import type { WorkflowDefinition, WorkflowStep, WorkflowCondition } from '@/types/advanced'
import { useDesignerStore } from '@/stores/designer'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const designerStore = useDesignerStore()

const workflow = ref<WorkflowDefinition | null>(null)
const selectedStepId = ref<string | null>(null)

watch(() => props.modelValue, (val) => {
  if (val) {
    workflow.value = createWorkflowDefinition('form_001', '默认审批流程', [
      createWorkflowStep('部门主管审批', 1, 'approval', { approver: '部门主管', approverRole: 'manager' }),
      createWorkflowStep('经理审批', 2, 'approval', { approver: '总监', approverRole: 'director' }),
      createWorkflowStep('完成', 3, 'auto')
    ])
    selectedStepId.value = workflow.value.steps[0]?.id || null
  }
})

function close() {
  emit('update:modelValue', false)
}

const selectedStep = computed(() => {
  return workflow.value?.steps.find(s => s.id === selectedStepId.value) || null
})

function selectStep(stepId: string) {
  selectedStepId.value = stepId
}

function addStep() {
  if (!workflow.value) return
  
  const newOrder = workflow.value.steps.length + 1
  const newStep = createWorkflowStep(`审批步骤 ${newOrder}`, newOrder, 'approval', {
    approver: '',
    approverRole: ''
  })
  
  workflow.value.steps.push(newStep)
  workflow.value.updatedAt = new Date().toISOString()
  selectedStepId.value = newStep.id
}

function deleteStep(stepId: string) {
  if (!workflow.value) return
  if (workflow.value.steps.length <= 1) return
  
  const index = workflow.value.steps.findIndex(s => s.id === stepId)
  if (index !== -1) {
    workflow.value.steps.splice(index, 1)
    workflow.value.steps.forEach((s, i) => s.order = i + 1)
    workflow.value.updatedAt = new Date().toISOString()
    
    if (selectedStepId.value === stepId) {
      selectedStepId.value = workflow.value.steps[Math.max(0, index - 1)]?.id || null
    }
  }
}

function updateStep(stepId: string, updates: Partial<WorkflowStep>) {
  if (!workflow.value) return
  
  const step = workflow.value.steps.find(s => s.id === stepId)
  if (step) {
    Object.assign(step, updates)
    workflow.value.updatedAt = new Date().toISOString()
  }
}

function getStepTypeIcon(type: string) {
  switch (type) {
    case 'approval': return User
    case 'auto': return CheckCircle2
    default: return Settings
  }
}

function getStepTypeText(type: string) {
  switch (type) {
    case 'approval': return '审批'
    case 'auto': return '自动'
    case 'notification': return '通知'
    default: return type
  }
}

const validation = computed(() => {
  if (!workflow.value) return { valid: true, errors: [] }
  return validateWorkflowDefinition(workflow.value)
})

const allFields = computed(() => {
  const fields: { name: string; label: string; type: string }[] = []
  designerStore.formSchema.tabs.forEach(tab => {
    tab.fields.forEach(f => {
      fields.push({ name: f.name, label: f.label, type: f.type })
    })
  })
  return fields
})

function addCondition(stepId: string) {
  if (!workflow.value) return
  
  const step = workflow.value.steps.find(s => s.id === stepId)
  if (step) {
    if (!step.conditions) {
      step.conditions = []
    }
    step.conditions.push({
      field: '',
      operator: '==',
      value: ''
    })
  }
}

function removeCondition(stepId: string, index: number) {
  if (!workflow.value) return
  
  const step = workflow.value.steps.find(s => s.id === stepId)
  if (step?.conditions) {
    step.conditions.splice(index, 1)
  }
}

function updateCondition(stepId: string, index: number, key: string, value: any) {
  if (!workflow.value) return
  
  const step = workflow.value.steps.find(s => s.id === stepId)
  if (step?.conditions?.[index]) {
    (step.conditions[index] as any)[key] = value
  }
}

function saveWorkflow() {
  if (!validation.value.valid) {
    alert('请修复以下错误：\n' + validation.value.errors.join('\n'))
    return
  }
  close()
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
                <GitMerge class="text-primary-600" :size="20" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-slate-800">工作流设计</h3>
                <p class="text-sm text-slate-500">配置多级审批流程</p>
              </div>
            </div>
            <button
              class="p-2 rounded-lg hover:bg-slate-100 transition-colors"
              @click="close"
            >
              <X :size="20" class="text-slate-500" />
            </button>
          </div>

          <div v-if="!validation.valid" class="px-6 py-3 bg-red-50 border-b border-red-200 flex-shrink-0">
            <div class="flex items-start gap-2">
              <span class="text-red-600 font-medium text-sm">配置错误：</span>
              <ul class="text-sm text-red-600">
                <li v-for="(error, i) in validation.errors" :key="i">{{ error }}</li>
              </ul>
            </div>
          </div>

          <div class="flex-1 flex overflow-hidden">
            <div class="w-80 border-r border-slate-200 overflow-y-auto flex-shrink-0 bg-slate-50">
              <div class="p-4">
                <div class="flex items-center justify-between mb-4">
                  <h4 class="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    流程步骤
                  </h4>
                  <button
                    class="p-1.5 rounded-lg bg-primary-100 text-primary-600 hover:bg-primary-200 transition-colors"
                    @click="addStep"
                    title="添加步骤"
                  >
                    <Plus :size="16" />
                  </button>
                </div>

                <div class="relative">
                  <div
                    v-for="(step, index) in workflow?.steps"
                    :key="step.id"
                    class="relative mb-2"
                  >
                    <div
                      v-if="index < (workflow?.steps.length || 0) - 1"
                      class="absolute left-5 top-12 w-0.5 h-6 bg-slate-300"
                    ></div>
                    
                    <div
                      class="p-4 rounded-lg cursor-pointer transition-all border"
                      :class="selectedStepId === step.id 
                        ? 'bg-primary-50 border-primary-300 shadow-sm' 
                        : 'bg-white border-slate-200 hover:border-slate-300'"
                      @click="selectStep(step.id)"
                    >
                      <div class="flex items-start justify-between">
                        <div class="flex items-start gap-3">
                          <div 
                            class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                            :class="{
                              'bg-blue-500': step.type === 'approval',
                              'bg-green-500': step.type === 'auto',
                              'bg-amber-500': step.type === 'notification'
                            }"
                          >
                            <component :is="getStepTypeIcon(step.type)" :size="18" class="text-white" />
                          </div>
                          <div>
                            <div class="flex items-center gap-2">
                              <span class="text-xs text-slate-400">{{ index + 1 }}</span>
                              <p class="text-sm font-medium text-slate-700">{{ step.name }}</p>
                            </div>
                            <div class="flex items-center gap-2 mt-1">
                              <span 
                                class="px-2 py-0.5 text-xs rounded-full"
                                :class="{
                                  'bg-blue-100 text-blue-700': step.type === 'approval',
                                  'bg-green-100 text-green-700': step.type === 'auto',
                                  'bg-amber-100 text-amber-700': step.type === 'notification'
                                }"
                              >
                                {{ getStepTypeText(step.type) }}
                              </span>
                              <span v-if="step.approver" class="text-xs text-slate-400">
                                {{ step.approver }}
                              </span>
                            </div>
                            <div v-if="step.conditions && step.conditions.length > 0" class="mt-2">
                              <span class="text-xs text-slate-400">
                                条件: {{ step.conditions.length }} 个
                              </span>
                            </div>
                          </div>
                        </div>
                        <button
                          v-if="(workflow?.steps.length || 0) > 1"
                          class="p-1.5 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition-colors"
                          @click.stop="deleteStep(step.id)"
                        >
                          <Trash2 :size="14" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto p-6">
              <div v-if="selectedStep" class="space-y-6">
                <div>
                  <h4 class="font-medium text-slate-800 mb-4">步骤配置</h4>
                  
                  <div class="space-y-4">
                    <div>
                      <label class="block text-sm font-medium text-slate-700 mb-2">步骤名称</label>
                      <input
                        type="text"
                        :value="selectedStep.name"
                        class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        @change="updateStep(selectedStep.id, { name: ($event.target as HTMLInputElement).value })"
                      />
                    </div>

                    <div>
                      <label class="block text-sm font-medium text-slate-700 mb-2">步骤类型</label>
                      <select
                        :value="selectedStep.type"
                        class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                        @change="updateStep(selectedStep.id, { type: ($event.target as HTMLSelectElement).value as any })"
                      >
                        <option value="approval">审批节点</option>
                        <option value="auto">自动节点</option>
                        <option value="notification">通知节点</option>
                      </select>
                    </div>

                    <div v-if="selectedStep.type === 'approval'" class="grid grid-cols-2 gap-4">
                      <div>
                        <label class="block text-sm font-medium text-slate-700 mb-2">审批人</label>
                        <input
                          type="text"
                          :value="selectedStep.approver || ''"
                          placeholder="指定审批人"
                          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                          @change="updateStep(selectedStep.id, { approver: ($event.target as HTMLInputElement).value })"
                        />
                      </div>
                      <div>
                        <label class="block text-sm font-medium text-slate-700 mb-2">审批角色</label>
                        <input
                          type="text"
                          :value="selectedStep.approverRole || ''"
                          placeholder="按角色审批"
                          class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                          @change="updateStep(selectedStep.id, { approverRole: ($event.target as HTMLInputElement).value })"
                        />
                      </div>
                    </div>

                    <div v-if="selectedStep.type === 'approval'">
                      <label class="block text-sm font-medium text-slate-700 mb-2">审批方式</label>
                      <div class="flex gap-4">
                        <label class="flex items-center gap-2">
                          <input
                            type="radio"
                            :checked="selectedStep.approvalType === 'any'"
                            class="w-4 h-4 text-primary-600"
                            @change="updateStep(selectedStep.id, { approvalType: 'any' })"
                          />
                          <span class="text-sm text-slate-700">或签（任一审批人通过即可）</span>
                        </label>
                        <label class="flex items-center gap-2">
                          <input
                            type="radio"
                            :checked="selectedStep.approvalType === 'all'"
                            class="w-4 h-4 text-primary-600"
                            @change="updateStep(selectedStep.id, { approvalType: 'all' })"
                          />
                          <span class="text-sm text-slate-700">会签（所有审批人通过）</span>
                        </label>
                      </div>
                    </div>

                    <div>
                      <div class="flex items-center justify-between mb-3">
                        <label class="text-sm font-medium text-slate-700">进入条件</label>
                        <button
                          class="text-xs text-primary-600 hover:text-primary-700 font-medium"
                          @click="addCondition(selectedStep.id)"
                        >
                          + 添加条件
                        </button>
                      </div>
                      <div v-if="selectedStep.conditions && selectedStep.conditions.length > 0" class="space-y-3">
                        <div
                          v-for="(condition, idx) in selectedStep.conditions"
                          :key="idx"
                          class="flex items-center gap-3 p-3 bg-slate-50 rounded-lg"
                        >
                          <select
                            :value="condition.field"
                            class="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                            @change="updateCondition(selectedStep.id, idx, 'field', ($event.target as HTMLSelectElement).value)"
                          >
                            <option value="">选择字段</option>
                            <option v-for="field in allFields" :key="field.name" :value="field.name">
                              {{ field.label }}
                            </option>
                          </select>
                          <select
                            :value="condition.operator"
                            class="w-24 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                            @change="updateCondition(selectedStep.id, idx, 'operator', ($event.target as HTMLSelectElement).value)"
                          >
                            <option value="==">等于</option>
                            <option value="!=">不等于</option>
                            <option value=">">大于</option>
                            <option value="<">小于</option>
                            <option value="contains">包含</option>
                          </select>
                          <input
                            type="text"
                            :value="condition.value"
                            placeholder="值"
                            class="w-32 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                            @change="updateCondition(selectedStep.id, idx, 'value', ($event.target as HTMLInputElement).value)"
                          />
                          <button
                            class="p-1.5 rounded hover:bg-red-100 text-slate-400 hover:text-red-500"
                            @click="removeCondition(selectedStep.id, idx)"
                          >
                            <Trash2 :size="14" />
                          </button>
                        </div>
                      </div>
                      <p v-else class="text-sm text-slate-400">无条件进入此步骤</p>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="text-center py-12">
                <p class="text-slate-500">请选择一个步骤进行配置</p>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-between px-6 py-4 bg-slate-50 border-t border-slate-200 flex-shrink-0">
            <div class="text-sm text-slate-500">
              配置 <span class="font-medium text-slate-700">{{ workflow?.steps.length }}</span> 个流程步骤
            </div>
            <div class="flex items-center gap-3">
              <button
                class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                @click="close"
              >
                取消
              </button>
              <button
                class="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-500 transition-colors"
                @click="saveWorkflow"
              >
                保存配置
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
