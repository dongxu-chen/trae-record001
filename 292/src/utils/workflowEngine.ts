import type {
  WorkflowDefinition,
  WorkflowInstance,
  WorkflowStep,
  WorkflowCondition,
  ApprovalRecord,
  WorkflowStatus,
  ApprovalStatus,
  WorkflowAction
} from '@/types/advanced'

function generateId(): string {
  return 'wf_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 6)
}

export function createWorkflowDefinition(
  formId: string,
  name: string,
  steps: WorkflowStep[] = []
): WorkflowDefinition {
  return {
    id: generateId(),
    formId,
    name,
    description: '',
    steps: steps.sort((a, b) => a.order - b.order),
    isActive: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  }
}

export function createWorkflowStep(
  name: string,
  order: number,
  type: 'approval' | 'auto' | 'notification' = 'approval',
  options: Partial<WorkflowStep> = {}
): WorkflowStep {
  return {
    id: generateId(),
    name,
    order,
    type,
    approvalType: 'any',
    ...options
  }
}

export function evaluateCondition(
  condition: WorkflowCondition,
  data: Record<string, any>
): boolean {
  const value = data[condition.field]
  const compareValue = condition.value

  switch (condition.operator) {
    case '==':
      return value == compareValue
    case '!=':
      return value != compareValue
    case '>':
      return value > compareValue
    case '<':
      return value < compareValue
    case '>=':
      return value >= compareValue
    case '<=':
      return value <= compareValue
    case 'contains':
      return String(value || '').includes(String(compareValue))
    default:
      return true
  }
}

export function evaluateConditions(
  conditions: WorkflowCondition[] | undefined,
  data: Record<string, any>
): boolean {
  if (!conditions || conditions.length === 0) return true
  return conditions.every(c => evaluateCondition(c, data))
}

export function getNextSteps(
  workflow: WorkflowDefinition,
  currentStepId: string,
  data: Record<string, any>
): WorkflowStep[] {
  const currentIndex = workflow.steps.findIndex(s => s.id === currentStepId)
  if (currentIndex === -1) return []

  const nextSteps: WorkflowStep[] = []
  
  for (let i = currentIndex + 1; i < workflow.steps.length; i++) {
    const step = workflow.steps[i]
    if (evaluateConditions(step.conditions, data)) {
      nextSteps.push(step)
      if (step.type !== 'auto') break
    }
  }

  return nextSteps
}

export function createWorkflowInstance(
  workflow: WorkflowDefinition,
  formData: Record<string, any>,
  createdBy: string
): WorkflowInstance {
  const firstStep = workflow.steps.find(s => 
    evaluateConditions(s.conditions, formData) && s.type === 'approval'
  )

  const initialApprovals: ApprovalRecord[] = firstStep ? [{
    stepId: firstStep.id,
    stepName: firstStep.name,
    approver: firstStep.approver || '',
    status: 'pending'
  }] : []

  return {
    id: generateId(),
    formId: workflow.formId,
    formVersion: '1.0.0',
    workflowId: workflow.id,
    data: { ...formData },
    status: firstStep ? 'submitted' : 'draft',
    currentStep: firstStep ? 0 : -1,
    approvals: initialApprovals,
    createdAt: new Date().toISOString(),
    createdBy,
    submittedAt: firstStep ? new Date().toISOString() : undefined
  }
}

export function executeWorkflowAction(
  instance: WorkflowInstance,
  workflow: WorkflowDefinition,
  action: WorkflowAction,
  actor: string
): WorkflowInstance {
  const newInstance: WorkflowInstance = {
    ...instance,
    approvals: [...instance.approvals]
  }

  switch (action.type) {
    case 'submit':
      return handleSubmit(newInstance, workflow, action, actor)
    
    case 'approve':
      return handleApprove(newInstance, workflow, action, actor)
    
    case 'reject':
      return handleReject(newInstance, action, actor)
    
    case 'recall':
      return handleRecall(newInstance)
    
    case 'complete':
      return handleComplete(newInstance)
    
    default:
      return instance
  }
}

function handleSubmit(
  instance: WorkflowInstance,
  workflow: WorkflowDefinition,
  action: WorkflowAction,
  actor: string
): WorkflowInstance {
  const firstApprovalStep = workflow.steps.find(s => 
    evaluateConditions(s.conditions, instance.data) && s.type === 'approval'
  )

  if (!firstApprovalStep) {
    return {
      ...instance,
      status: 'completed',
      currentStep: workflow.steps.length,
      completedAt: new Date().toISOString()
    }
  }

  const approvals: ApprovalRecord[] = [{
    stepId: firstApprovalStep.id,
    stepName: firstApprovalStep.name,
    approver: action.approver || firstApprovalStep.approver || '',
    status: 'pending'
  }]

  return {
    ...instance,
    status: 'submitted',
    currentStep: workflow.steps.indexOf(firstApprovalStep),
    approvals,
    submittedAt: new Date().toISOString()
  }
}

function handleApprove(
  instance: WorkflowInstance,
  workflow: WorkflowDefinition,
  action: WorkflowAction,
  actor: string
): WorkflowInstance {
  const currentApprovalIndex = instance.approvals.findIndex(
    a => a.status === 'pending'
  )
  
  if (currentApprovalIndex === -1) return instance

  const currentApproval = instance.approvals[currentApprovalIndex]
  
  const newApprovals = [...instance.approvals]
  newApprovals[currentApprovalIndex] = {
    ...currentApproval,
    status: 'approved',
    approver: actor,
    comment: action.comment,
    approvedAt: new Date().toISOString()
  }

  const currentStep = workflow.steps.find(s => s.id === currentApproval.stepId)
  if (!currentStep) {
    return { ...instance, approvals: newApprovals }
  }

  const nextSteps = getNextSteps(workflow, currentStep.id, instance.data)

  if (nextSteps.length === 0) {
    return {
      ...instance,
      approvals: newApprovals,
      status: 'completed',
      currentStep: workflow.steps.length,
      completedAt: new Date().toISOString()
    }
  }

  const nextApprovalStep = nextSteps.find(s => s.type === 'approval')
  
  if (nextApprovalStep) {
    newApprovals.push({
      stepId: nextApprovalStep.id,
      stepName: nextApprovalStep.name,
      approver: action.nextStep || nextApprovalStep.approver || '',
      status: 'pending'
    })

    return {
      ...instance,
      approvals: newApprovals,
      currentStep: workflow.steps.indexOf(nextApprovalStep)
    }
  }

  return { ...instance, approvals: newApprovals }
}

function handleReject(
  instance: WorkflowInstance,
  action: WorkflowAction,
  actor: string
): WorkflowInstance {
  const currentApprovalIndex = instance.approvals.findIndex(
    a => a.status === 'pending'
  )
  
  if (currentApprovalIndex === -1) return instance

  const currentApproval = instance.approvals[currentApprovalIndex]
  
  const newApprovals = [...instance.approvals]
  newApprovals[currentApprovalIndex] = {
    ...currentApproval,
    status: 'rejected',
    approver: actor,
    comment: action.comment,
    rejectedAt: new Date().toISOString()
  }

  return {
    ...instance,
    approvals: newApprovals,
    status: 'rejected'
  }
}

function handleRecall(instance: WorkflowInstance): WorkflowInstance {
  return {
    ...instance,
    status: 'draft',
    currentStep: -1,
    approvals: instance.approvals.map(a => 
      a.status === 'pending' ? { ...a, status: 'rejected' } : a
    )
  }
}

function handleComplete(instance: WorkflowInstance): WorkflowInstance {
  return {
    ...instance,
    status: 'completed',
    completedAt: new Date().toISOString()
  }
}

export function getApprovalHistory(
  instance: WorkflowInstance
): ApprovalRecord[] {
  return [...instance.approvals].sort((a, b) => {
    const timeA = a.approvedAt || a.rejectedAt || ''
    const timeB = b.approvedAt || b.rejectedAt || ''
    return new Date(timeA).getTime() - new Date(timeB).getTime()
  })
}

export function getPendingApprovals(
  instances: WorkflowInstance[],
  approver: string
): WorkflowInstance[] {
  return instances.filter(instance => {
    const pendingApproval = instance.approvals.find(a => a.status === 'pending')
    return pendingApproval?.approver === approver
  })
}

export function canApprove(
  instance: WorkflowInstance,
  userId: string
): boolean {
  if (instance.status !== 'submitted') return false
  
  const pendingApproval = instance.approvals.find(a => a.status === 'pending')
  return pendingApproval?.approver === userId
}

export function canRecall(
  instance: WorkflowInstance,
  userId: string
): boolean {
  return instance.status === 'submitted' && instance.createdBy === userId
}

export function canEdit(
  instance: WorkflowInstance,
  userId: string
): boolean {
  return (instance.status === 'draft' || instance.status === 'rejected') 
    && instance.createdBy === userId
}

export function getWorkflowStatusText(status: WorkflowStatus): string {
  const statusMap: Record<WorkflowStatus, string> = {
    draft: '草稿',
    submitted: '审批中',
    approved: '已通过',
    rejected: '已驳回',
    completed: '已完成'
  }
  return statusMap[status] || status
}

export function getApprovalStatusText(status: ApprovalStatus): string {
  const statusMap: Record<ApprovalStatus, string> = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已驳回'
  }
  return statusMap[status] || status
}

export function validateWorkflowDefinition(workflow: WorkflowDefinition): {
  valid: boolean
  errors: string[]
} {
  const errors: string[] = []

  if (!workflow.name.trim()) {
    errors.push('流程名称不能为空')
  }

  if (workflow.steps.length === 0) {
    errors.push('流程至少需要一个步骤')
  }

  const stepNames = new Set<string>()
  workflow.steps.forEach((step, index) => {
    if (!step.name.trim()) {
      errors.push(`步骤 ${index + 1} 名称不能为空`)
    }
    if (stepNames.has(step.name)) {
      errors.push(`步骤名称重复: ${step.name}`)
    }
    stepNames.add(step.name)

    if (step.type === 'approval' && !step.approver && !step.approverRole) {
      errors.push(`步骤 "${step.name}" 需要指定审批人或审批角色`)
    }
  })

  return {
    valid: errors.length === 0,
    errors
  }
}
