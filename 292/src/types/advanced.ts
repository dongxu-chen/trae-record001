import type { FormSchema } from './form'

export type VersionStatus = 'draft' | 'published' | 'archived'

export interface FormVersion {
  id: string
  version: string
  name: string
  description: string
  schema: FormSchema
  status: VersionStatus
  createdAt: string
  createdBy: string
  changelog: string
  isCurrent: boolean
}

export interface PrintTemplate {
  id: string
  name: string
  description: string
  isDefault: boolean
  layout: PrintLayout
  header: PrintSection
  footer: PrintSection
  sections: PrintSection[]
  pageSetup: PageSetup
  createdAt: string
  updatedAt: string
}

export type PrintLayout = 'single-column' | 'two-column' | 'tabbed'

export interface PrintSection {
  id: string
  name: string
  title?: string
  visible: boolean
  fields: PrintField[]
  style?: SectionStyle
}

export interface PrintField {
  fieldId: string
  fieldName: string
  label: string
  width: 'full' | 'half' | 'third' | 'quarter'
  visible: boolean
  showLabel: boolean
  style?: FieldStyle
}

export interface SectionStyle {
  backgroundColor?: string
  borderColor?: string
  padding?: string
  marginTop?: string
  marginBottom?: string
}

export interface FieldStyle {
  fontWeight?: 'normal' | 'bold'
  fontSize?: 'small' | 'medium' | 'large'
  color?: string
}

export interface PageSetup {
  paperSize: 'A4' | 'Letter' | 'Legal'
  orientation: 'portrait' | 'landscape'
  marginTop: number
  marginBottom: number
  marginLeft: number
  marginRight: number
  showPageNumbers: boolean
  showWatermark: boolean
  watermarkText?: string
}

export type WorkflowStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'completed'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected'

export interface WorkflowDefinition {
  id: string
  formId: string
  name: string
  description: string
  steps: WorkflowStep[]
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface WorkflowStep {
  id: string
  name: string
  order: number
  type: 'approval' | 'auto' | 'notification'
  approver?: string
  approverRole?: string
  approvalType: 'any' | 'all'
  conditions?: WorkflowCondition[]
  autoAction?: string
  notificationTemplate?: string
}

export interface WorkflowCondition {
  field: string
  operator: '==' | '!=' | '>' | '<' | '>=' | '<=' | 'contains'
  value: any
}

export interface WorkflowInstance {
  id: string
  formId: string
  formVersion: string
  workflowId: string
  data: Record<string, any>
  status: WorkflowStatus
  currentStep: number
  approvals: ApprovalRecord[]
  createdAt: string
  createdBy: string
  submittedAt?: string
  completedAt?: string
}

export interface ApprovalRecord {
  stepId: string
  stepName: string
  approver: string
  status: ApprovalStatus
  comment?: string
  approvedAt?: string
  rejectedAt?: string
  attachments?: string[]
}

export interface PrintOptions {
  includeHeader: boolean
  includeFooter: boolean
  includeSections: string[]
  scale: number
  showEmptyFields: boolean
  watermark?: string
}

export interface WorkflowAction {
  type: 'submit' | 'approve' | 'reject' | 'recall' | 'complete'
  comment?: string
  approver?: string
  nextStep?: string
}
