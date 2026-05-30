import { ChangeSubscription, ChangeNotification, ChangeType, RiskLevel } from '@/types';

const MOCK_SUBSCRIPTIONS: ChangeSubscription[] = [
  {
    id: 'sub-001',
    fieldId: 'field-user-user_id',
    fieldName: 'user_id',
    subscriberEmail: 'zhangsan@company.com',
    subscriberName: '张三',
    changeTypes: ['delete', 'type_change', 'rename'],
    notifyOnRiskLevel: ['high', 'critical'],
    isActive: true,
    createdAt: '2026-05-15T10:00:00Z',
    lastNotifiedAt: '2026-05-20T08:00:00Z',
  },
  {
    id: 'sub-002',
    fieldId: 'field-order-amount',
    fieldName: 'amount',
    subscriberEmail: 'lisi@company.com',
    subscriberName: '李四',
    changeTypes: ['delete', 'type_change', 'constraint_change'],
    notifyOnRiskLevel: ['medium', 'high', 'critical'],
    isActive: true,
    createdAt: '2026-05-18T14:00:00Z',
  },
  {
    id: 'sub-003',
    fieldId: 'field-order-amount',
    fieldName: 'amount',
    subscriberEmail: 'wangwu@company.com',
    subscriberName: '王五',
    changeTypes: ['delete', 'rename'],
    notifyOnRiskLevel: ['high', 'critical'],
    isActive: true,
    createdAt: '2026-05-20T09:00:00Z',
    lastNotifiedAt: '2026-05-25T16:00:00Z',
  },
];

const MOCK_NOTIFICATIONS: ChangeNotification[] = [
  {
    id: 'notif-001',
    subscriptionId: 'sub-001',
    fieldId: 'field-user-user_id',
    fieldName: 'user_id',
    changeType: 'type_change',
    changeDescription: 'user_id字段类型从INT变更为BIGINT',
    riskLevel: 'high',
    notifiedEmails: ['zhangsan@company.com'],
    notifiedAt: '2026-05-20T08:00:00Z',
    status: 'sent',
  },
  {
    id: 'notif-002',
    subscriptionId: 'sub-003',
    fieldId: 'field-order-amount',
    fieldName: 'amount',
    changeDescription: 'amount字段拟增加非空约束',
    changeType: 'constraint_change',
    riskLevel: 'medium',
    notifiedEmails: ['wangwu@company.com'],
    notifiedAt: '2026-05-25T16:00:00Z',
    status: 'sent',
  },
];

let subscriptions = [...MOCK_SUBSCRIPTIONS];
let notifications = [...MOCK_NOTIFICATIONS];

export const getSubscriptions = (fieldId?: string): ChangeSubscription[] => {
  if (fieldId) {
    return subscriptions.filter(s => s.fieldId === fieldId && s.isActive);
  }
  return subscriptions.filter(s => s.isActive);
};

export const addSubscription = (sub: Omit<ChangeSubscription, 'id' | 'createdAt'>): ChangeSubscription => {
  const newSub: ChangeSubscription = {
    ...sub,
    id: `sub-${Date.now()}`,
    createdAt: new Date().toISOString(),
  };
  subscriptions = [...subscriptions, newSub];
  return newSub;
};

export const removeSubscription = (id: string): void => {
  subscriptions = subscriptions.map(s =>
    s.id === id ? { ...s, isActive: false } : s
  );
};

export const updateSubscription = (id: string, updates: Partial<ChangeSubscription>): ChangeSubscription | undefined => {
  subscriptions = subscriptions.map(s =>
    s.id === id ? { ...s, ...updates } : s
  );
  return subscriptions.find(s => s.id === id);
};

export const notifyChange = (
  fieldId: string,
  fieldName: string,
  changeType: ChangeType,
  changeDescription: string,
  riskLevel: RiskLevel
): ChangeNotification[] => {
  const matchedSubs = subscriptions.filter(s =>
    s.fieldId === fieldId &&
    s.isActive &&
    s.changeTypes.includes(changeType) &&
    s.notifyOnRiskLevel.includes(riskLevel)
  );

  const newNotifications: ChangeNotification[] = matchedSubs.map(sub => ({
    id: `notif-${Date.now()}-${sub.id}`,
    subscriptionId: sub.id,
    fieldId,
    fieldName,
    changeType,
    changeDescription,
    riskLevel,
    notifiedEmails: [sub.subscriberEmail],
    notifiedAt: new Date().toISOString(),
    status: 'sent' as const,
  }));

  notifications = [...notifications, ...newNotifications];

  subscriptions = subscriptions.map(s => {
    const notif = newNotifications.find(n => n.subscriptionId === s.id);
    if (notif) {
      return { ...s, lastNotifiedAt: notif.notifiedAt };
    }
    return s;
  });

  return newNotifications;
};

export const getNotifications = (fieldId?: string): ChangeNotification[] => {
  if (fieldId) {
    return notifications.filter(n => n.fieldId === fieldId);
  }
  return notifications;
};

export const getDownstreamOwners = (analysisResult: { downstreamList: { etlTasks: { owner: string }[]; reports: { owner: string }[] } }): Array<{ name: string; email: string; role: string }> => {
  const owners = new Map<string, { name: string; email: string; role: string }>();

  analysisResult.downstreamList.etlTasks.forEach(task => {
    if (!owners.has(task.owner)) {
      owners.set(task.owner, {
        name: task.owner,
        email: `${task.owner.toLowerCase().replace(/\s/g, '')}@company.com`,
        role: 'ETL负责人',
      });
    }
  });

  analysisResult.downstreamList.reports.forEach(report => {
    if (!owners.has(report.owner)) {
      owners.set(report.owner, {
        name: report.owner,
        email: `${report.owner.toLowerCase().replace(/\s/g, '')}@company.com`,
        role: '报表负责人',
      });
    }
  });

  return Array.from(owners.values());
};

export const getChangeTypeLabel = (type: ChangeType): string => {
  const labels: Record<ChangeType, string> = {
    delete: '字段删除',
    type_change: '类型变更',
    rename: '字段重命名',
    constraint_change: '约束变更',
    default_change: '默认值变更',
  };
  return labels[type];
};

export const getChangeTypeIcon = (type: ChangeType): string => {
  const icons: Record<ChangeType, string> = {
    delete: '🗑️',
    type_change: '🔄',
    rename: '✏️',
    constraint_change: '🔒',
    default_change: '⚙️',
  };
  return icons[type];
};
