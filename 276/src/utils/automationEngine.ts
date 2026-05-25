import { Task, AutomationRule, RuleCondition, RuleAction, TaskStatus, Priority } from '@/types';
import { differenceInDays, differenceInHours, isPast, addDays } from 'date-fns';

export const checkCondition = (task: Task, condition: RuleCondition): boolean => {
  const now = new Date();

  switch (condition.type) {
    case 'due_date_overdue':
      if (!task.dueDate) return false;
      return isPast(new Date(task.dueDate)) && task.status !== 'done';

    case 'due_date_approaching':
      if (!task.dueDate) return false;
      const daysUntilDue = differenceInDays(new Date(task.dueDate), now);
      const threshold = condition.value || 2;
      return daysUntilDue >= 0 && daysUntilDue <= threshold && task.status !== 'done';

    case 'in_progress_too_long':
      if (task.status !== 'in-progress') return false;
      const hoursInProgress = differenceInHours(now, new Date(task.updatedAt));
      const thresholdHours = condition.value || 48;
      return hoursInProgress >= thresholdHours;

    case 'priority_high_no_assignee':
      return (task.priority === 'high' || task.priority === 'urgent') && !task.assignee;

    case 'custom':
      return true;

    default:
      return false;
  }
};

export const checkAllConditions = (task: Task, conditions: RuleCondition[]): boolean => {
  if (conditions.length === 0) return false;
  return conditions.every(condition => checkCondition(task, condition));
};

export const executeAction = (task: Task, action: RuleAction): Partial<Task> => {
  const updates: Partial<Task> = {};

  switch (action.type) {
    case 'move_status':
      updates.status = action.value as TaskStatus;
      break;

    case 'change_priority':
      updates.priority = action.value as Priority;
      break;

    case 'add_tag':
      if (!task.tags.includes(action.value)) {
        updates.tags = [...task.tags, action.value];
      }
      break;

    case 'remove_tag':
      updates.tags = task.tags.filter(t => t !== action.value);
      break;

    case 'assign_to':
      updates.assignee = action.value;
      break;

    case 'notify':
      break;

    default:
      break;
  }

  return updates;
};

export const executeAllActions = (task: Task, actions: RuleAction[]): Partial<Task> => {
  let allUpdates: Partial<Task> = {};
  actions.forEach(action => {
    const updates = executeAction(task, action);
    allUpdates = { ...allUpdates, ...updates };
    if (updates.tags) {
      task = { ...task, ...updates };
    }
  });
  return allUpdates;
};

export const processTaskWithRules = (task: Task, rules: AutomationRule[]): { task: Task; updates: Partial<Task>; triggeredRules: string[] } => {
  const triggeredRules: string[] = [];
  let allUpdates: Partial<Task> = {};
  let updatedTask = { ...task };

  rules.forEach(rule => {
    if (!rule.enabled) return;
    
    if (checkAllConditions(updatedTask, rule.conditions)) {
      triggeredRules.push(rule._id);
      const updates = executeAllActions(updatedTask, rule.actions);
      allUpdates = { ...allUpdates, ...updates };
      updatedTask = { ...updatedTask, ...updates };
    }
  });

  return { task: updatedTask, updates: allUpdates, triggeredRules };
};

export const defaultRules: AutomationRule[] = [
  {
    _id: 'rule-1',
    name: '超时自动延期提醒',
    description: '任务截止日期已过但未完成，自动标记优先级为高',
    enabled: true,
    conditions: [{ type: 'due_date_overdue' }],
    actions: [
      { type: 'change_priority', value: 'high' },
      { type: 'add_tag', value: '已延期' },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    _id: 'rule-2',
    name: '即将到期提醒',
    description: '任务将在2天内到期，自动添加标签提醒',
    enabled: true,
    conditions: [{ type: 'due_date_approaching', value: 2 }],
    actions: [{ type: 'add_tag', value: '即将到期' }],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    _id: 'rule-3',
    name: '进行中超时预警',
    description: '任务进行中超过48小时，自动升级优先级',
    enabled: true,
    conditions: [{ type: 'in_progress_too_long', value: 48 }],
    actions: [
      { type: 'change_priority', value: 'high' },
      { type: 'add_tag', value: '进度缓慢' },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    _id: 'rule-4',
    name: '高优先级任务分配提醒',
    description: '高优先级任务未分配负责人，添加标签提醒',
    enabled: true,
    conditions: [{ type: 'priority_high_no_assignee' }],
    actions: [{ type: 'add_tag', value: '待分配' }],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

export const getConditionLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'due_date_overdue': '截止日期已过',
    'due_date_approaching': '截止日期即将到来',
    'in_progress_too_long': '进行中超时',
    'priority_high_no_assignee': '高优先级未分配',
    'custom': '自定义条件',
  };
  return labels[type] || type;
};

export const getActionLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'move_status': '移动状态',
    'change_priority': '修改优先级',
    'add_tag': '添加标签',
    'remove_tag': '移除标签',
    'assign_to': '分配给',
    'notify': '发送通知',
  };
  return labels[type] || type;
};
