import { evaluateRule } from './expression-engine.js';
import {
  getAllRules,
  saveAlert,
  getAlerts as getAlertsFromRedis,
  incrementId,
  getRecentMetrics,
} from './redis.js';
import type { ThresholdRule, AlertRecord } from '../types.js';

export async function evaluateMetric(
  metric: string,
  value: number,
): Promise<AlertRecord[]> {
  const rules = await getAllRules();
  const matchingRules = rules.filter(
    (r) => r.metric === metric && r.enabled,
  );

  const triggeredAlerts: AlertRecord[] = [];

  for (const rule of matchingRules) {
    const result = evaluateRule(rule, value);
    if (result.triggered) {
      const alert = await createAlertRecord(rule, metric, value, result.expression);
      triggeredAlerts.push(alert);
    }
  }

  return triggeredAlerts;
}

export async function createAlertRecord(
  rule: ThresholdRule,
  metric: string,
  triggerValue: number,
  expression: string,
): Promise<AlertRecord> {
  const id = `alert-${Date.now()}-${await incrementId('alert')}`;
  const now = new Date().toISOString();

  const recentMetrics = await getRecentMetrics(metric, 20);
  const seriesData = recentMetrics.map((m) => m.value);
  const xAxisLabels = recentMetrics.map((m) =>
    new Date(m.timestamp).toLocaleTimeString(),
  );

  const thresholdValue = rule.conditions[0]?.value ?? 0;

  const alert: AlertRecord = {
    id,
    ruleId: rule.id,
    ruleName: rule.name,
    metric,
    level: rule.level,
    triggerValue,
    thresholdValue,
    expression,
    message: `${rule.name}: ${metric} value ${triggerValue} ${rule.conditions[0]?.operator || '>'} ${thresholdValue}`,
    snapshot: {
      seriesData,
      timestamp: now,
      xAxisLabels,
    },
    createdAt: now,
    acknowledged: false,
  };

  await saveAlert(alert);
  return alert;
}

export async function getAlertHistory(query: {
  page: number;
  pageSize: number;
  level?: string;
  metric?: string;
  startTime?: string;
  endTime?: string;
  acknowledged?: string;
}): Promise<{ data: AlertRecord[]; total: number }> {
  return getAlertsFromRedis(query);
}
