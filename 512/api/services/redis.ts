import Redis from 'ioredis';
import type { ThresholdRule, AlertRecord, MetricData, AlertFeedback } from '../types.js';
import { precompileRule, invalidateRuleCache, clearCache } from './expression-engine.js';

let redis: Redis | null = null;
let useMemory = false;

const rulesStore = new Map<string, string>();
const alertsStore = new Map<string, string>();
const metricsStore = new Map<string, string>();
const feedbacksStore = new Map<string, string>();
let ruleIdCounter = 100;
let alertIdCounter = 100;
let feedbackIdCounter = 100;

try {
  redis = new Redis({
    host: process.env.REDIS_HOST || 'localhost',
    port: Number(process.env.REDIS_PORT) || 6379,
    maxRetriesPerRequest: 1,
    retryStrategy: () => null,
    lazyConnect: true,
  });

  redis.on('error', (err) => {
    console.log('Redis connection failed, using in-memory fallback');
    useMemory = true;
    redis = null;
  });

  redis.on('connect', () => {
    console.log('Redis connected');
    useMemory = false;
  });
} catch {
  useMemory = true;
  redis = null;
}

export async function ensureConnection(): Promise<void> {
  if (redis && !useMemory) {
    try {
      await redis.ping();
    } catch {
      useMemory = true;
      redis = null;
    }
  }
}

export async function incrementId(key: string): Promise<number> {
  if (useMemory || !redis) {
    if (key === 'rule') return ++ruleIdCounter;
    if (key === 'alert') return ++alertIdCounter;
    if (key === 'feedback') return ++feedbackIdCounter;
    return Date.now();
  }
  try {
    return await redis.incr(`counter:${key}`);
  } catch {
    if (key === 'rule') return ++ruleIdCounter;
    if (key === 'alert') return ++alertIdCounter;
    if (key === 'feedback') return ++feedbackIdCounter;
    return Date.now();
  }
}

export async function saveRule(rule: ThresholdRule): Promise<void> {
  const data = JSON.stringify(rule);
  if (useMemory || !redis) {
    rulesStore.set(rule.id, data);
  } else {
    try {
      await redis.set(`rule:${rule.id}`, data);
    } catch {
      rulesStore.set(rule.id, data);
    }
  }
  precompileRule(rule);
}

export async function getRule(id: string): Promise<ThresholdRule | null> {
  if (useMemory || !redis) {
    const data = rulesStore.get(id);
    return data ? JSON.parse(data) : null;
  }
  try {
    const data = await redis.get(`rule:${id}`);
    return data ? JSON.parse(data) : null;
  } catch {
    const data = rulesStore.get(id);
    return data ? JSON.parse(data) : null;
  }
}

export async function getAllRules(): Promise<ThresholdRule[]> {
  let rules: ThresholdRule[];
  if (useMemory || !redis) {
    rules = Array.from(rulesStore.values()).map((v) => JSON.parse(v));
  } else {
    try {
      const keys = await redis.keys('rule:*');
      if (keys.length === 0) return [];
      const values = await redis.mget(...keys);
      rules = values.filter((v): v is string => v !== null).map((v) => JSON.parse(v));
    } catch {
      rules = Array.from(rulesStore.values()).map((v) => JSON.parse(v));
    }
  }
  for (const rule of rules) {
    precompileRule(rule);
  }
  return rules;
}

export async function deleteRule(id: string): Promise<boolean> {
  let result: boolean;
  if (useMemory || !redis) {
    result = rulesStore.delete(id);
  } else {
    try {
      const delResult = await redis.del(`rule:${id}`);
      result = delResult > 0;
    } catch {
      result = rulesStore.delete(id);
    }
  }
  if (result) {
    invalidateRuleCache(id);
  }
  return result;
}

export async function saveAlert(alert: AlertRecord): Promise<void> {
  const data = JSON.stringify(alert);
  if (useMemory || !redis) {
    alertsStore.set(alert.id, data);
    return;
  }
  try {
    const multi = redis.multi();
    multi.set(`alert:${alert.id}`, data);
    multi.zadd('alerts:timeline', Date.parse(alert.createdAt), alert.id);
    await multi.exec();
  } catch {
    alertsStore.set(alert.id, data);
  }
}

export async function getAlerts(options: {
  page: number;
  pageSize: number;
  level?: string;
  metric?: string;
  startTime?: string;
  endTime?: string;
  acknowledged?: string;
}): Promise<{ data: AlertRecord[]; total: number }> {
  let allAlerts: AlertRecord[];

  if (useMemory || !redis) {
    allAlerts = Array.from(alertsStore.values()).map((v) => JSON.parse(v));
  } else {
    try {
      const keys = await redis.keys('alert:*');
      if (keys.length === 0) return { data: [], total: 0 };
      const values = await redis.mget(...keys);
      allAlerts = values.filter((v): v is string => v !== null).map((v) => JSON.parse(v));
    } catch {
      allAlerts = Array.from(alertsStore.values()).map((v) => JSON.parse(v));
    }
  }

  let filtered = allAlerts;

  if (options.level) {
    filtered = filtered.filter((a) => a.level === options.level);
  }
  if (options.metric) {
    filtered = filtered.filter((a) => a.metric === options.metric);
  }
  if (options.startTime) {
    const start = new Date(options.startTime).getTime();
    filtered = filtered.filter((a) => new Date(a.createdAt).getTime() >= start);
  }
  if (options.endTime) {
    const end = new Date(options.endTime).getTime();
    filtered = filtered.filter((a) => new Date(a.createdAt).getTime() <= end);
  }
  if (options.acknowledged !== undefined && options.acknowledged !== '') {
    const ack = options.acknowledged === 'true';
    filtered = filtered.filter((a) => a.acknowledged === ack);
  }

  filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

  const total = filtered.length;
  const start = (options.page - 1) * options.pageSize;
  const data = filtered.slice(start, start + options.pageSize);

  return { data, total };
}

export async function getAlertById(id: string): Promise<AlertRecord | null> {
  if (useMemory || !redis) {
    const data = alertsStore.get(id);
    return data ? JSON.parse(data) : null;
  }
  try {
    const data = await redis.get(`alert:${id}`);
    return data ? JSON.parse(data) : null;
  } catch {
    const data = alertsStore.get(id);
    return data ? JSON.parse(data) : null;
  }
}

export async function acknowledgeAlert(id: string): Promise<AlertRecord | null> {
  const alert = await getAlertById(id);
  if (!alert) return null;
  alert.acknowledged = true;
  await saveAlert(alert);
  return alert;
}

export async function saveMetricData(metric: MetricData): Promise<void> {
  const key = `metric:${metric.metric}`;
  const data = JSON.stringify(metric);
  if (useMemory || !redis) {
    const existing = metricsStore.get(key);
    const arr: MetricData[] = existing ? JSON.parse(existing) : [];
    arr.push(metric);
    if (arr.length > 500) arr.shift();
    metricsStore.set(key, JSON.stringify(arr));
    return;
  }
  try {
    const existing = await redis.get(key);
    const arr: MetricData[] = existing ? JSON.parse(existing) : [];
    arr.push(metric);
    if (arr.length > 500) arr.shift();
    await redis.set(key, JSON.stringify(arr));
  } catch {
    const existing = metricsStore.get(key);
    const arr: MetricData[] = existing ? JSON.parse(existing) : [];
    arr.push(metric);
    if (arr.length > 500) arr.shift();
    metricsStore.set(key, JSON.stringify(arr));
  }
}

export async function getRecentMetrics(metric: string, count: number = 60): Promise<MetricData[]> {
  if (useMemory || !redis) {
    const data = metricsStore.get(`metric:${metric}`);
    const arr: MetricData[] = data ? JSON.parse(data) : [];
    return arr.slice(-count);
  }
  try {
    const data = await redis.get(`metric:${metric}`);
    const arr: MetricData[] = data ? JSON.parse(data) : [];
    return arr.slice(-count);
  } catch {
    const data = metricsStore.get(`metric:${metric}`);
    const arr: MetricData[] = data ? JSON.parse(data) : [];
    return arr.slice(-count);
  }
}

export async function saveFeedback(feedback: AlertFeedback): Promise<void> {
  const data = JSON.stringify(feedback);
  if (useMemory || !redis) {
    feedbacksStore.set(feedback.id, data);
    return;
  }
  try {
    await redis.set(`feedback:${feedback.id}`, data);
  } catch {
    feedbacksStore.set(feedback.id, data);
  }
}

export async function getFeedbacksByRule(ruleId: string): Promise<AlertFeedback[]> {
  let allFeedbacks: AlertFeedback[];
  if (useMemory || !redis) {
    allFeedbacks = Array.from(feedbacksStore.values()).map((v) => JSON.parse(v));
  } else {
    try {
      const keys = await redis.keys('feedback:*');
      if (keys.length === 0) return [];
      const values = await redis.mget(...keys);
      allFeedbacks = values.filter((v): v is string => v !== null).map((v) => JSON.parse(v));
    } catch {
      allFeedbacks = Array.from(feedbacksStore.values()).map((v) => JSON.parse(v));
    }
  }
  return allFeedbacks.filter((f) => f.ruleId === ruleId);
}

export async function getFeedbacksByAlert(alertId: string): Promise<AlertFeedback[]> {
  let allFeedbacks: AlertFeedback[];
  if (useMemory || !redis) {
    allFeedbacks = Array.from(feedbacksStore.values()).map((v) => JSON.parse(v));
  } else {
    try {
      const keys = await redis.keys('feedback:*');
      if (keys.length === 0) return [];
      const values = await redis.mget(...keys);
      allFeedbacks = values.filter((v): v is string => v !== null).map((v) => JSON.parse(v));
    } catch {
      allFeedbacks = Array.from(feedbacksStore.values()).map((v) => JSON.parse(v));
    }
  }
  return allFeedbacks.filter((f) => f.alertId === alertId);
}

export async function seedInitialRules(): Promise<void> {
  const existing = await getAllRules();
  if (existing.length > 0) return;

  const now = new Date().toISOString();
  const rules: ThresholdRule[] = [
    {
      id: 'rule-1',
      name: 'CPU High Warning',
      metric: 'CPU',
      conditions: [{ field: 'value', operator: '>', value: 70 }],
      level: 'warning',
      enabled: true,
      createdAt: now,
      updatedAt: now,
    },
    {
      id: 'rule-2',
      name: 'CPU Critical',
      metric: 'CPU',
      conditions: [{ field: 'value', operator: '>', value: 90 }],
      level: 'critical',
      enabled: true,
      createdAt: now,
      updatedAt: now,
    },
    {
      id: 'rule-3',
      name: 'Memory Warning',
      metric: 'Memory',
      conditions: [{ field: 'value', operator: '>', value: 75 }],
      level: 'warning',
      enabled: true,
      createdAt: now,
      updatedAt: now,
    },
    {
      id: 'rule-4',
      name: 'Memory Critical',
      metric: 'Memory',
      conditions: [{ field: 'value', operator: '>', value: 90 }],
      level: 'critical',
      enabled: true,
      createdAt: now,
      updatedAt: now,
    },
    {
      id: 'rule-5',
      name: 'Error Rate Alert',
      metric: 'ErrorRate',
      conditions: [{ field: 'value', operator: '>', value: 5 }],
      level: 'danger',
      enabled: true,
      createdAt: now,
      updatedAt: now,
    },
    {
      id: 'rule-6',
      name: 'Latency Alert',
      metric: 'Latency',
      conditions: [{ field: 'value', operator: '>', value: 200 }],
      level: 'warning',
      enabled: true,
      createdAt: now,
      updatedAt: now,
    },
  ];

  for (const rule of rules) {
    await saveRule(rule);
  }
  console.log('Seeded initial rules');
}
