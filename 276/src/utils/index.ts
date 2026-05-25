import { format, formatDistanceToNow, isPast, isToday, isTomorrow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { TaskStatus, Priority } from '@/types';

export const formatDate = (date: string | Date | null): string => {
  if (!date) return '';
  return format(new Date(date), 'yyyy-MM-dd', { locale: zhCN });
};

export const formatDateTime = (date: string | Date | null): string => {
  if (!date) return '';
  return format(new Date(date), 'yyyy-MM-dd HH:mm', { locale: zhCN });
};

export const formatRelativeTime = (date: string | Date | null): string => {
  if (!date) return '';
  return formatDistanceToNow(new Date(date), { addSuffix: true, locale: zhCN });
};

export const getDueDateStatus = (dueDate: string | Date | null): 'overdue' | 'today' | 'tomorrow' | 'upcoming' | null => {
  if (!dueDate) return null;
  const date = new Date(dueDate);
  
  if (isPast(date) && !isToday(date)) return 'overdue';
  if (isToday(date)) return 'today';
  if (isTomorrow(date)) return 'tomorrow';
  return 'upcoming';
};

export const statusLabels: Record<TaskStatus, string> = {
  'todo': '待办',
  'in-progress': '进行中',
  'done': '已完成',
};

export const priorityLabels: Record<Priority, string> = {
  'low': '低',
  'medium': '中',
  'high': '高',
  'urgent': '紧急',
};

export const getStatusColor = (status: TaskStatus): string => {
  const colors: Record<TaskStatus, string> = {
    'todo': 'bg-gray-500',
    'in-progress': 'bg-amber-500',
    'done': 'bg-green-500',
  };
  return colors[status];
};

export const getPriorityColor = (priority: Priority): string => {
  const colors: Record<Priority, string> = {
    'low': 'bg-gray-400',
    'medium': 'bg-blue-500',
    'high': 'bg-orange-500',
    'urgent': 'bg-red-500',
  };
  return colors[priority];
};

export const getFieldLabel = (field: string): string => {
  const labels: Record<string, string> = {
    title: '标题',
    description: '描述',
    status: '状态',
    priority: '优先级',
    assignee: '负责人',
    tags: '标签',
    dueDate: '截止日期',
    startDate: '开始日期',
    subTasks: '子任务',
  };
  return labels[field] || field;
};

export const generateId = (): string => {
  return Math.random().toString(36).substring(2, 15);
};
