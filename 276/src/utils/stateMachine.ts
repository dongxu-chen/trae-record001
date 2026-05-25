import { TaskStatus } from '@/types';

export type StateTransition = {
  from: TaskStatus;
  to: TaskStatus;
  allowed: boolean;
  reason?: string;
};

export const STATE_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  'todo': ['in-progress'],
  'in-progress': ['todo', 'done'],
  'done': ['in-progress'],
};

export const canTransition = (from: TaskStatus, to: TaskStatus): boolean => {
  return STATE_TRANSITIONS[from]?.includes(to) ?? false;
};

export const getValidTransitions = (from: TaskStatus): TaskStatus[] => {
  return STATE_TRANSITIONS[from] ?? [];
};

export const getTransitionBlockedReason = (from: TaskStatus, to: TaskStatus): string | null => {
  if (canTransition(from, to)) {
    return null;
  }

  const fromLabel = getStatusChineseLabel(from);
  const toLabel = getStatusChineseLabel(to);

  const validNext = getValidTransitions(from).map(getStatusChineseLabel);
  
  if (validNext.length === 0) {
    return `${fromLabel} 状态无法进行任何流转`;
  }
  
  return `${fromLabel} 只能流转到 ${validNext.join('、')}，不能直接流转到 ${toLabel}`;
};

export const getStatusChineseLabel = (status: TaskStatus): string => {
  const labels: Record<TaskStatus, string> = {
    'todo': '待办',
    'in-progress': '进行中',
    'done': '已完成',
  };
  return labels[status];
};

export const getStatusFlowDescription = (): string => {
  return '待办 → 进行中 → 已完成';
};
