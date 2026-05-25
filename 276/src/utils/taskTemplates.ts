import { Task, TaskTemplate, Priority } from '@/types';
import { addDays } from 'date-fns';

export const createTemplateFromTask = (task: Task, templateName: string, description: string): TaskTemplate => {
  return {
    _id: `template-${Date.now()}`,
    name: templateName,
    description,
    title: task.title,
    taskDescription: task.description || '',
    priority: task.priority,
    assignee: task.assignee || '',
    tags: [...task.tags],
    dueDays: task.dueDate 
      ? Math.max(1, Math.ceil((new Date(task.dueDate).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)))
      : 7,
    subTasks: task.subTasks.map(st => st.title),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
};

export const createTaskFromTemplate = (template: TaskTemplate, boardId: string, overrides?: Partial<Task>): Task => {
  const now = new Date();
  const dueDate = addDays(now, template.dueDays);

  return {
    _id: `task-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    boardId,
    title: overrides?.title || template.title,
    description: overrides?.description || template.taskDescription,
    status: 'todo',
    priority: overrides?.priority || template.priority,
    assignee: overrides?.assignee || template.assignee || '',
    tags: overrides?.tags || [...template.tags],
    dueDate: dueDate.toISOString(),
    startDate: now.toISOString(),
    subTasks: template.subTasks.map((title, index) => ({
      _id: `subtask-${Date.now()}-${index}`,
      title,
      completed: false,
    })),
    comments: [],
    history: [],
    operationLogs: [],
    order: 0,
    createdAt: now.toISOString(),
    updatedAt: now.toISOString(),
  };
};

export const defaultTemplates: TaskTemplate[] = [
  {
    _id: 'template-default-1',
    name: '功能开发',
    description: '标准功能开发流程模板',
    title: '【功能开发】',
    taskDescription: '请详细描述功能需求和验收标准',
    priority: 'medium',
    assignee: '',
    tags: ['开发', '功能'],
    dueDays: 7,
    subTasks: [
      '需求分析和设计',
      '代码开发',
      '单元测试',
      '代码审查',
      '联调测试',
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    _id: 'template-default-2',
    name: 'Bug 修复',
    description: 'Bug 修复标准流程模板',
    title: '【Bug修复】',
    taskDescription: '请详细描述Bug现象、复现步骤和预期结果',
    priority: 'high',
    assignee: '',
    tags: ['Bug', '修复'],
    dueDays: 3,
    subTasks: [
      '问题复现和定位',
      '修复代码开发',
      '验证测试',
      '代码审查合并',
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    _id: 'template-default-3',
    name: '需求调研',
    description: '需求调研和分析模板',
    title: '【需求调研】',
    taskDescription: '请描述调研目标和范围',
    priority: 'medium',
    assignee: '',
    tags: ['调研', '需求'],
    dueDays: 5,
    subTasks: [
      '收集用户需求',
      '竞品分析',
      '技术可行性分析',
      '输出调研报告',
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    _id: 'template-default-4',
    name: '代码审查',
    description: '代码审查任务模板',
    title: '【代码审查】',
    taskDescription: '请关联需要审查的PR或分支',
    priority: 'medium',
    assignee: '',
    tags: ['Code Review', '审查'],
    dueDays: 2,
    subTasks: [
      '代码风格检查',
      '业务逻辑审查',
      '安全性检查',
      '性能评估',
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    _id: 'template-default-5',
    name: '文档编写',
    description: '技术文档编写模板',
    title: '【文档编写】',
    taskDescription: '请描述文档类型和内容要求',
    priority: 'low',
    assignee: '',
    tags: ['文档', '技术'],
    dueDays: 3,
    subTasks: [
      '大纲编写',
      '内容撰写',
      '配图和示例',
      '审核发布',
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];
