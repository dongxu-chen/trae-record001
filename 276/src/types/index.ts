export type TaskStatus = 'todo' | 'in-progress' | 'done';
export type Priority = 'low' | 'medium' | 'high' | 'urgent';
export type OperationType =
  | 'create'
  | 'update'
  | 'delete'
  | 'status_change'
  | 'subtask_add'
  | 'subtask_remove'
  | 'subtask_complete'
  | 'comment_add'
  | 'comment_remove';

export type RuleConditionType = 'due_date_overdue' | 'due_date_approaching' | 'in_progress_too_long' | 'priority_high_no_assignee' | 'custom';
export type RuleActionType = 'move_status' | 'change_priority' | 'add_tag' | 'remove_tag' | 'assign_to' | 'notify';

export interface RuleCondition {
  type: RuleConditionType;
  value?: any;
}

export interface RuleAction {
  type: RuleActionType;
  value: any;
}

export interface AutomationRule {
  _id: string;
  name: string;
  description: string;
  enabled: boolean;
  conditions: RuleCondition[];
  actions: RuleAction[];
  createdAt: string;
  updatedAt: string;
}

export interface WorkloadStats {
  assignee: string;
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  todoTasks: number;
  completionRate: number;
  averageCompletionTime: number;
  points: number;
}

export interface TaskTemplate {
  _id: string;
  name: string;
  description: string;
  title: string;
  taskDescription: string;
  priority: Priority;
  assignee: string;
  tags: string[];
  dueDays: number;
  subTasks: string[];
  createdAt: string;
  updatedAt: string;
}

export interface Board {
  _id: string;
  name: string;
  description: string;
  createdAt: string;
  updatedAt: string;
}

export interface SubTask {
  _id: string;
  title: string;
  completed: boolean;
  createdAt: string;
}

export interface Comment {
  _id: string;
  content: string;
  author: string;
  createdAt: string;
}

export interface TaskSnapshot {
  title: string;
  description: string;
  status: TaskStatus;
  priority: Priority;
  assignee: string;
  tags: string[];
  dueDate: string | null;
  startDate: string | null;
  subTasks: SubTask[];
}

export interface OperationLog {
  _id: string;
  operation: OperationType;
  operator: string;
  timestamp: string;
  description: string;
  changes?: {
    field: string;
    oldValue: any;
    newValue: any;
  }[];
  snapshotBefore?: TaskSnapshot;
  snapshotAfter?: TaskSnapshot;
}

export interface HistoryEntry {
  _id: string;
  field: string;
  oldValue: any;
  newValue: any;
  changedBy: string;
  changedAt: string;
}

export interface Task {
  _id: string;
  boardId: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: Priority;
  assignee: string;
  tags: string[];
  dueDate: string | null;
  startDate: string | null;
  order: number;
  subTasks: SubTask[];
  comments: Comment[];
  history: HistoryEntry[];
  operationLogs: OperationLog[];
  createdAt: string;
  updatedAt: string;
}

export interface TaskFilters {
  assignee: string;
  tags: string[];
  priority: Priority | '';
}
