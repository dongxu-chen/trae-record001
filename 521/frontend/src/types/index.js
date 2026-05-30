export const TaskTypes = {
  SHELL: 'SHELL',
  PYTHON: 'PYTHON',
  HTTP: 'HTTP',
  DATA_SYNC: 'DATA_SYNC',
  EMAIL: 'EMAIL'
};

export const TaskTypeLabels = {
  [TaskTypes.SHELL]: 'Shell命令',
  [TaskTypes.PYTHON]: 'Python脚本',
  [TaskTypes.HTTP]: 'HTTP请求',
  [TaskTypes.DATA_SYNC]: '数据同步',
  [TaskTypes.EMAIL]: '邮件通知'
};

export const TaskStatus = {
  PENDING: 'PENDING',
  RUNNING: 'RUNNING',
  SUCCESS: 'SUCCESS',
  FAILED: 'FAILED',
  CANCELLED: 'CANCELLED'
};

export const WorkflowStatus = {
  DRAFT: 'DRAFT',
  PUBLISHED: 'PUBLISHED'
};

export const TriggerTypes = {
  CRON: 'CRON',
  EVENT: 'EVENT',
  WEBHOOK: 'WEBHOOK',
  MANUAL: 'MANUAL'
};

export const TriggerTypeLabels = {
  [TriggerTypes.CRON]: '定时触发',
  [TriggerTypes.EVENT]: '事件触发',
  [TriggerTypes.WEBHOOK]: 'WebHook触发',
  [TriggerTypes.MANUAL]: '手动触发'
};

export const StatusColors = {
  [TaskStatus.PENDING]: '#d9d9d9',
  [TaskStatus.RUNNING]: '#faad14',
  [TaskStatus.SUCCESS]: '#52c41a',
  [TaskStatus.FAILED]: '#ff4d4f',
  [TaskStatus.CANCELLED]: '#8c8c8c'
};
