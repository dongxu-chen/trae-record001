<script setup lang="ts">
import { ref, computed } from 'vue'
import { ArrowLeft, Check, X, Clock, User, MessageSquare, Send, RotateCcw } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { createWorkflowInstance, executeWorkflowAction, getWorkflowStatusText, getApprovalStatusText, canApprove, canRecall, canEdit } from '@/utils/workflowEngine'
import { createWorkflowDefinition, createWorkflowStep } from '@/utils/workflowEngine'
import type { WorkflowInstance, WorkflowAction } from '@/types/advanced'

const router = useRouter()

const sampleWorkflow = createWorkflowDefinition('form_001', '请假审批流程', [
  createWorkflowStep('部门主管审批', 1, 'approval', { approver: '张三', approverRole: 'manager' }),
  createWorkflowStep('人事审批', 2, 'approval', { approver: '李四', approverRole: 'hr' }),
  createWorkflowStep('完成', 3, 'auto')
])

const sampleFormData = {
  name: '王五',
  department: '技术部',
  startDate: '2024-01-15',
  endDate: '2024-01-17',
  reason: '年假申请',
  days: 3
}

const instance = ref<WorkflowInstance>(createWorkflowInstance(sampleWorkflow, sampleFormData, '王五'))
const approvalComment = ref('')
const showApproveDialog = ref(false)
const showRejectDialog = ref(false)
const currentUserId = ref('张三')

const currentStatusText = computed(() => getWorkflowStatusText(instance.value.status))

const statusColor = computed(() => {
  const colors: Record<string, string> = {
    draft: 'bg-slate-100 text-slate-700',
    submitted: 'bg-blue-100 text-blue-700',
    approved: 'bg-green-100 text-green-700',
    rejected: 'bg-red-100 text-red-700',
    completed: 'bg-green-100 text-green-700'
  }
  return colors[instance.value.status] || colors.draft
})

const currentStep = computed(() => {
  if (instance.value.currentStep >= 0 && instance.value.currentStep < sampleWorkflow.steps.length) {
    return sampleWorkflow.steps[instance.value.currentStep]
  }
  return null
})

const sortedApprovals = computed(() => {
  return [...instance.value.approvals].sort((a, b) => {
    const timeA = a.approvedAt || a.rejectedAt || ''
    const timeB = b.approvedAt || b.rejectedAt || ''
    if (!timeA && !timeB) return 0
    if (!timeA) return 1
    if (!timeB) return -1
    return new Date(timeA).getTime() - new Date(timeB).getTime()
  })
})

function getStepStatus(stepOrder: number): 'completed' | 'current' | 'pending' {
  const currentIndex = instance.value.currentStep
  if (stepOrder - 1 < currentIndex) return 'completed'
  if (stepOrder - 1 === currentIndex) return 'current'
  return 'pending'
}

function handleSubmit() {
  const action: WorkflowAction = { type: 'submit' }
  instance.value = executeWorkflowAction(instance.value, sampleWorkflow, action, currentUserId.value)
}

function handleApprove() {
  const action: WorkflowAction = { 
    type: 'approve', 
    comment: approvalComment.value 
  }
  instance.value = executeWorkflowAction(instance.value, sampleWorkflow, action, currentUserId.value)
  approvalComment.value = ''
  showApproveDialog.value = false
}

function handleReject() {
  const action: WorkflowAction = { 
    type: 'reject', 
    comment: approvalComment.value 
  }
  instance.value = executeWorkflowAction(instance.value, sampleWorkflow, action, currentUserId.value)
  approvalComment.value = ''
  showRejectDialog.value = false
}

function handleRecall() {
  const action: WorkflowAction = { type: 'recall' }
  instance.value = executeWorkflowAction(instance.value, sampleWorkflow, action, currentUserId.value)
}

function goBack() {
  router.back()
}

function formatDate(dateStr?: string) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <div class="bg-white border-b border-slate-200">
      <div class="max-w-6xl mx-auto px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <button
              class="p-2 rounded-lg hover:bg-slate-100 transition-colors"
              @click="goBack"
            >
              <ArrowLeft :size="20" class="text-slate-600" />
            </button>
            <div>
              <h1 class="text-xl font-semibold text-slate-800">请假审批</h1>
              <p class="text-sm text-slate-500">审批编号: {{ instance.id }}</p>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <span
              class="px-3 py-1.5 rounded-full text-sm font-medium"
              :class="statusColor"
            >
              {{ currentStatusText }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="max-w-6xl mx-auto px-6 py-6">
      <div class="grid grid-cols-3 gap-6">
        <div class="col-span-2 space-y-6">
          <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-800 mb-4">审批流程</h2>
            <div class="relative">
              <div class="flex items-start">
                <div
                  v-for="(step, index) in sampleWorkflow.steps"
                  :key="step.id"
                  class="flex-1 relative"
                >
                  <div v-if="index < sampleWorkflow.steps.length - 1" class="absolute top-4 left-8 right-0 h-0.5"
                    :class="{
                      'bg-green-500': getStepStatus(step.order) === 'completed',
                      'bg-slate-200': getStepStatus(step.order) !== 'completed'
                    }"
                  ></div>
                  <div class="relative z-10">
                    <div
                      class="w-8 h-8 rounded-full flex items-center justify-center mx-auto mb-2"
                      :class="{
                        'bg-green-500': getStepStatus(step.order) === 'completed',
                        'bg-blue-500 ring-4 ring-blue-100': getStepStatus(step.order) === 'current',
                        'bg-slate-200': getStepStatus(step.order) === 'pending'
                      }"
                    >
                      <Check v-if="getStepStatus(step.order) === 'completed'" :size="16" class="text-white" />
                      <Clock v-else-if="getStepStatus(step.order) === 'current'" :size="16" class="text-white" />
                      <span v-else class="text-xs text-slate-500 font-medium">{{ step.order }}</span>
                    </div>
                    <p class="text-center text-sm font-medium text-slate-700">{{ step.name }}</p>
                    <p v-if="step.approver" class="text-center text-xs text-slate-400 mt-1">{{ step.approver }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-800 mb-4">表单数据</h2>
            <div class="grid grid-cols-2 gap-6">
              <div v-for="(value, key) in sampleFormData" :key="key" class="flex items-start gap-3">
                <span class="text-sm text-slate-500 min-w-[80px]">{{ key }}：</span>
                <span class="text-sm text-slate-800">{{ value }}</span>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-800 mb-4">审批记录</h2>
            <div class="space-y-4">
              <div
                v-for="(approval, index) in sortedApprovals"
                :key="approval.stepId"
                class="relative pl-8"
              >
                <div v-if="index < sortedApprovals.length - 1" class="absolute left-3 top-8 w-0.5 h-full bg-slate-200"></div>
                <div class="absolute left-0 top-1 w-6 h-6 rounded-full flex items-center justify-center"
                  :class="{
                    'bg-green-100': approval.status === 'approved',
                    'bg-red-100': approval.status === 'rejected',
                    'bg-blue-100': approval.status === 'pending'
                  }"
                >
                  <Check v-if="approval.status === 'approved'" :size="14" class="text-green-600" />
                  <X v-else-if="approval.status === 'rejected'" :size="14" class="text-red-600" />
                  <Clock v-else :size="14" class="text-blue-600" />
                </div>
                <div class="p-4 bg-slate-50 rounded-lg">
                  <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                      <User :size="16" class="text-slate-400" />
                      <span class="text-sm font-medium text-slate-700">{{ approval.approver || '待审批' }}</span>
                    </div>
                    <span
                      class="px-2 py-0.5 text-xs rounded-full"
                      :class="{
                        'bg-green-100 text-green-700': approval.status === 'approved',
                        'bg-red-100 text-red-700': approval.status === 'rejected',
                        'bg-blue-100 text-blue-700': approval.status === 'pending'
                      }"
                    >
                      {{ getApprovalStatusText(approval.status) }}
                    </span>
                  </div>
                  <p class="text-sm text-slate-600 mb-1">{{ approval.stepName }}</p>
                  <p v-if="approval.comment" class="text-sm text-slate-500 flex items-center gap-2">
                    <MessageSquare :size="14" />
                    {{ approval.comment }}
                  </p>
                  <p v-if="approval.approvedAt || approval.rejectedAt" class="text-xs text-slate-400 mt-2">
                    {{ formatDate(approval.approvedAt || approval.rejectedAt) }}
                  </p>
                </div>
              </div>

              <div v-if="sortedApprovals.length === 0" class="text-center py-8">
                <p class="text-slate-500">暂无审批记录</p>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-800 mb-4">操作</h2>
            <div class="space-y-3">
              <button
                v-if="instance.status === 'draft'"
                class="w-full py-2.5 px-4 bg-primary-600 text-white rounded-lg hover:bg-primary-500 transition-colors flex items-center justify-center gap-2"
                @click="handleSubmit"
              >
                <Send :size="18" />
                提交审批
              </button>

              <button
                v-if="canApprove(instance, currentUserId)"
                class="w-full py-2.5 px-4 bg-green-600 text-white rounded-lg hover:bg-green-500 transition-colors flex items-center justify-center gap-2"
                @click="showApproveDialog = true"
              >
                <Check :size="18" />
                审批通过
              </button>

              <button
                v-if="canApprove(instance, currentUserId)"
                class="w-full py-2.5 px-4 bg-red-600 text-white rounded-lg hover:bg-red-500 transition-colors flex items-center justify-center gap-2"
                @click="showRejectDialog = true"
              >
                <X :size="18" />
                审批驳回
              </button>

              <button
                v-if="canRecall(instance, currentUserId)"
                class="w-full py-2.5 px-4 bg-amber-600 text-white rounded-lg hover:bg-amber-500 transition-colors flex items-center justify-center gap-2"
                @click="handleRecall"
              >
                <RotateCcw :size="18" />
                撤回申请
              </button>

              <button
                v-if="canEdit(instance, currentUserId)"
                class="w-full py-2.5 px-4 bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"
              >
                编辑表单
              </button>

              <div v-if="instance.status === 'completed'" class="text-center py-4">
                <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Check :size="32" class="text-green-600" />
                </div>
                <p class="text-slate-700 font-medium">审批已完成</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
            <h3 class="text-sm font-semibold text-slate-800 mb-3">申请信息</h3>
            <div class="space-y-3 text-sm">
              <div class="flex justify-between">
                <span class="text-slate-500">申请人</span>
                <span class="text-slate-700">{{ instance.createdBy }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-500">提交时间</span>
                <span class="text-slate-700">{{ formatDate(instance.submittedAt) }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-500">创建时间</span>
                <span class="text-slate-700">{{ formatDate(instance.createdAt) }}</span>
              </div>
              <div v-if="instance.completedAt" class="flex justify-between">
                <span class="text-slate-500">完成时间</span>
                <span class="text-slate-700">{{ formatDate(instance.completedAt) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="showApproveDialog"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          @click.self="showApproveDialog = false"
        >
          <div class="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
            <div class="p-6">
              <h3 class="text-lg font-semibold text-slate-800 mb-4">审批通过</h3>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-2">审批意见（可选）</label>
                <textarea
                  v-model="approvalComment"
                  class="w-full h-24 px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 resize-none"
                  placeholder="请输入审批意见..."
                ></textarea>
              </div>
            </div>
            <div class="flex items-center justify-end gap-3 px-6 py-4 bg-slate-50 border-t border-slate-200 rounded-b-xl">
              <button
                class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                @click="showApproveDialog = false"
              >
                取消
              </button>
              <button
                class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-500 transition-colors"
                @click="handleApprove"
              >
                确认通过
              </button>
            </div>
          </div>
        </div>
      </Transition>

      <Transition name="fade">
        <div
          v-if="showRejectDialog"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          @click.self="showRejectDialog = false"
        >
          <div class="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
            <div class="p-6">
              <h3 class="text-lg font-semibold text-slate-800 mb-4">审批驳回</h3>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-2">驳回原因</label>
                <textarea
                  v-model="approvalComment"
                  class="w-full h-24 px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 resize-none"
                  placeholder="请输入驳回原因..."
                ></textarea>
              </div>
            </div>
            <div class="flex items-center justify-end gap-3 px-6 py-4 bg-slate-50 border-t border-slate-200 rounded-b-xl">
              <button
                class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                @click="showRejectDialog = false"
              >
                取消
              </button>
              <button
                class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-500 transition-colors"
                @click="handleReject"
              >
                确认驳回
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
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
