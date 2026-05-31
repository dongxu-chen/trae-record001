import { db } from './init.js';
import { v4 as uuidv4 } from 'uuid';
import type {
  DataQualityRule,
  RuleTemplate,
  ScheduledTask,
  TaskExecution,
  QualityIssue,
  OverviewStats,
  TrendDataPoint,
  TrendDataWithThreshold,
} from '../../shared/types.js';

function computeDynamicThreshold(
  data: Array<{ date: string; value: number }>,
  cutoffDate: string,
  isQualityScore: boolean
): TrendDataWithThreshold[] {
  const historicalData = data.filter(d => d.date < cutoffDate);
  const displayData = data.filter(d => d.date >= cutoffDate);

  if (historicalData.length < 2) {
    return displayData.map(d => ({
      date: d.date,
      value: d.value,
      upper: isQualityScore ? 100 : d.value * 1.5,
      lower: isQualityScore ? 60 : 0,
      baseline: d.value,
      isAnomaly: false,
    }));
  }

  const values = historicalData.map(d => d.value);
  const mean = values.reduce((a, b) => a + b, 0) / values.length;

  const diffs: number[] = [];
  for (let i = 1; i < values.length; i++) {
    if (values[i - 1] !== 0) {
      diffs.push((values[i] - values[i - 1]) / Math.abs(values[i - 1]));
    }
  }

  const avgDiffRate = diffs.length > 0 ? diffs.reduce((a, b) => a + b, 0) / diffs.length : 0;
  const diffStdDev = diffs.length > 1
    ? Math.sqrt(diffs.reduce((s, d) => s + Math.pow(d - avgDiffRate, 2), 0) / (diffs.length - 1))
    : 0.1;

  const bandMultiplier = 1.5;

  return displayData.map(d => {
    const dynamicMargin = (mean * (avgDiffRate + bandMultiplier * diffStdDev));
    const upper = isQualityScore
      ? Math.min(100, mean + Math.abs(dynamicMargin))
      : mean + Math.abs(dynamicMargin);
    const lower = isQualityScore
      ? Math.max(0, mean - Math.abs(dynamicMargin))
      : Math.max(0, mean - Math.abs(dynamicMargin));

    const isAnomaly = d.value > upper || d.value < lower;

    return {
      date: d.date,
      value: d.value,
      upper: Math.round(upper * 100) / 100,
      lower: Math.round(lower * 100) / 100,
      baseline: Math.round(mean * 100) / 100,
      isAnomaly,
    };
  });
}

function parseJson<T>(str: string | null): T | null {
  if (!str) return null;
  try {
    return JSON.parse(str) as T;
  } catch {
    return null;
  }
}

function formatDate(date: Date | string | null): string | undefined {
  if (!date) return undefined;
  return new Date(date).toISOString();
}

export const ruleTemplatesRepository = {
  getAll(): RuleTemplate[] {
    const rows = db.prepare('SELECT * FROM rule_templates').all() as Array<{
      id: string;
      name: string;
      description: string;
      type: string;
      default_config: string;
    }>;
    return rows.map(row => ({
      id: row.id,
      name: row.name,
      description: row.description,
      type: row.type as RuleTemplate['type'],
      defaultConfig: parseJson(row.default_config) || {},
    }));
  },
};

export const rulesRepository = {
  getAll(): DataQualityRule[] {
    const rows = db.prepare('SELECT * FROM data_quality_rules ORDER BY created_at DESC').all() as Array<{
      id: string;
      name: string;
      description: string;
      type: string;
      data_source: string;
      table_name: string;
      column_name: string;
      config: string;
      enabled: number;
      created_at: string;
      updated_at: string;
    }>;
    return rows.map(row => ({
      id: row.id,
      name: row.name,
      description: row.description,
      type: row.type as DataQualityRule['type'],
      dataSource: row.data_source,
      tableName: row.table_name,
      columnName: row.column_name,
      config: parseJson(row.config) || {},
      enabled: row.enabled === 1,
      createdAt: formatDate(row.created_at)!,
      updatedAt: formatDate(row.updated_at)!,
    }));
  },

  getById(id: string): DataQualityRule | null {
    const row = db.prepare('SELECT * FROM data_quality_rules WHERE id = ?').get(id) as {
      id: string;
      name: string;
      description: string;
      type: string;
      data_source: string;
      table_name: string;
      column_name: string;
      config: string;
      enabled: number;
      created_at: string;
      updated_at: string;
    } | undefined;
    if (!row) return null;
    return {
      id: row.id,
      name: row.name,
      description: row.description,
      type: row.type as DataQualityRule['type'],
      dataSource: row.data_source,
      tableName: row.table_name,
      columnName: row.column_name,
      config: parseJson(row.config) || {},
      enabled: row.enabled === 1,
      createdAt: formatDate(row.created_at)!,
      updatedAt: formatDate(row.updated_at)!,
    };
  },

  create(rule: Omit<DataQualityRule, 'id' | 'createdAt' | 'updatedAt'>): DataQualityRule {
    const id = uuidv4();
    const now = new Date().toISOString();
    db.prepare(`
      INSERT INTO data_quality_rules (id, name, description, type, data_source, table_name, column_name, config, enabled, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      rule.name,
      rule.description,
      rule.type,
      rule.dataSource,
      rule.tableName,
      rule.columnName,
      JSON.stringify(rule.config),
      rule.enabled ? 1 : 0,
      now,
      now
    );
    return { ...rule, id, createdAt: now, updatedAt: now };
  },

  update(id: string, rule: Partial<Omit<DataQualityRule, 'id' | 'createdAt'>>): DataQualityRule | null {
    const existing = this.getById(id);
    if (!existing) return null;

    const updated = { ...existing, ...rule, updatedAt: new Date().toISOString() };
    db.prepare(`
      UPDATE data_quality_rules
      SET name = ?, description = ?, type = ?, data_source = ?, table_name = ?, column_name = ?, config = ?, enabled = ?, updated_at = ?
      WHERE id = ?
    `).run(
      updated.name,
      updated.description,
      updated.type,
      updated.dataSource,
      updated.tableName,
      updated.columnName,
      JSON.stringify(updated.config),
      updated.enabled ? 1 : 0,
      updated.updatedAt,
      id
    );
    return updated;
  },

  delete(id: string): boolean {
    const result = db.prepare('DELETE FROM data_quality_rules WHERE id = ?').run(id);
    return result.changes > 0;
  },
};

export const tasksRepository = {
  getAll(): ScheduledTask[] {
    const rows = db.prepare(`
      SELECT st.*, GROUP_CONCAT(str.rule_id) as rule_ids
      FROM scheduled_tasks st
      LEFT JOIN scheduled_task_rules str ON st.id = str.task_id
      GROUP BY st.id
      ORDER BY st.created_at DESC
    `).all() as Array<{
      id: string;
      name: string;
      cron_expression: string;
      enabled: number;
      last_run_at: string | null;
      next_run_at: string | null;
      created_at: string;
      updated_at: string;
      rule_ids: string | null;
    }>;
    return rows.map(row => ({
      id: row.id,
      name: row.name,
      ruleIds: row.rule_ids ? row.rule_ids.split(',') : [],
      cronExpression: row.cron_expression,
      enabled: row.enabled === 1,
      lastRunAt: formatDate(row.last_run_at),
      nextRunAt: formatDate(row.next_run_at),
      createdAt: formatDate(row.created_at)!,
      updatedAt: formatDate(row.updated_at)!,
    }));
  },

  getById(id: string): ScheduledTask | null {
    const row = db.prepare(`
      SELECT st.*, GROUP_CONCAT(str.rule_id) as rule_ids
      FROM scheduled_tasks st
      LEFT JOIN scheduled_task_rules str ON st.id = str.task_id
      WHERE st.id = ?
      GROUP BY st.id
    `).get(id) as {
      id: string;
      name: string;
      cron_expression: string;
      enabled: number;
      last_run_at: string | null;
      next_run_at: string | null;
      created_at: string;
      updated_at: string;
      rule_ids: string | null;
    } | undefined;
    if (!row) return null;
    return {
      id: row.id,
      name: row.name,
      ruleIds: row.rule_ids ? row.rule_ids.split(',') : [],
      cronExpression: row.cron_expression,
      enabled: row.enabled === 1,
      lastRunAt: formatDate(row.last_run_at),
      nextRunAt: formatDate(row.next_run_at),
      createdAt: formatDate(row.created_at)!,
      updatedAt: formatDate(row.updated_at)!,
    };
  },

  create(task: Omit<ScheduledTask, 'id' | 'createdAt' | 'updatedAt'>): ScheduledTask {
    const id = uuidv4();
    const now = new Date().toISOString();
    db.prepare(`
      INSERT INTO scheduled_tasks (id, name, cron_expression, enabled, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `).run(id, task.name, task.cronExpression, task.enabled ? 1 : 0, now, now);

    const insertRule = db.prepare('INSERT INTO scheduled_task_rules (task_id, rule_id) VALUES (?, ?)');
    task.ruleIds.forEach(ruleId => {
      insertRule.run(id, ruleId);
    });

    return { ...task, id, createdAt: now, updatedAt: now };
  },

  update(id: string, task: Partial<Omit<ScheduledTask, 'id' | 'createdAt'>>): ScheduledTask | null {
    const existing = this.getById(id);
    if (!existing) return null;

    const updated = { ...existing, ...task, updatedAt: new Date().toISOString() };
    db.prepare(`
      UPDATE scheduled_tasks
      SET name = ?, cron_expression = ?, enabled = ?, updated_at = ?
      WHERE id = ?
    `).run(updated.name, updated.cronExpression, updated.enabled ? 1 : 0, updated.updatedAt, id);

    db.prepare('DELETE FROM scheduled_task_rules WHERE task_id = ?').run(id);
    const insertRule = db.prepare('INSERT INTO scheduled_task_rules (task_id, rule_id) VALUES (?, ?)');
    updated.ruleIds.forEach(ruleId => {
      insertRule.run(id, ruleId);
    });

    return updated;
  },

  updateLastRun(id: string, lastRunAt: Date): void {
    db.prepare('UPDATE scheduled_tasks SET last_run_at = ? WHERE id = ?').run(lastRunAt.toISOString(), id);
  },
};

export const executionsRepository = {
  create(execution: Omit<TaskExecution, 'id'>): TaskExecution {
    const id = uuidv4();
    db.prepare(`
      INSERT INTO task_executions (id, task_id, task_name, status, start_time, end_time, total_records, failed_records, quality_score)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      execution.taskId,
      execution.taskName,
      execution.status,
      execution.startTime,
      execution.endTime || null,
      execution.totalRecords,
      execution.failedRecords,
      execution.qualityScore
    );
    return { ...execution, id };
  },

  update(id: string, updates: Partial<TaskExecution>): void {
    const setClauses: string[] = [];
    const values: unknown[] = [];

    if (updates.status !== undefined) {
      setClauses.push('status = ?');
      values.push(updates.status);
    }
    if (updates.endTime !== undefined) {
      setClauses.push('end_time = ?');
      values.push(updates.endTime || null);
    }
    if (updates.totalRecords !== undefined) {
      setClauses.push('total_records = ?');
      values.push(updates.totalRecords);
    }
    if (updates.failedRecords !== undefined) {
      setClauses.push('failed_records = ?');
      values.push(updates.failedRecords);
    }
    if (updates.qualityScore !== undefined) {
      setClauses.push('quality_score = ?');
      values.push(updates.qualityScore);
    }

    if (setClauses.length > 0) {
      values.push(id);
      db.prepare(`UPDATE task_executions SET ${setClauses.join(', ')} WHERE id = ?`).run(...values);
    }
  },

  getRecent(limit = 10): TaskExecution[] {
    const rows = db.prepare('SELECT * FROM task_executions ORDER BY start_time DESC LIMIT ?').all(limit) as Array<{
      id: string;
      task_id: string;
      task_name: string;
      status: string;
      start_time: string;
      end_time: string | null;
      total_records: number;
      failed_records: number;
      quality_score: number;
    }>;
    return rows.map(row => ({
      id: row.id,
      taskId: row.task_id,
      taskName: row.task_name,
      status: row.status as TaskExecution['status'],
      startTime: formatDate(row.start_time)!,
      endTime: formatDate(row.end_time),
      totalRecords: row.total_records,
      failedRecords: row.failed_records,
      qualityScore: row.quality_score,
    }));
  },
};

export const issuesRepository = {
  create(issue: Omit<QualityIssue, 'id' | 'createdAt'>): QualityIssue {
    const id = uuidv4();
    const now = new Date().toISOString();
    db.prepare(`
      INSERT INTO quality_issues (id, execution_id, rule_id, rule_name, table_name, column_name, row_identifier, issue_type, description, status, assignee, priority)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id,
      issue.executionId,
      issue.ruleId,
      issue.ruleName,
      issue.tableName,
      issue.columnName,
      issue.rowIdentifier,
      issue.issueType,
      issue.description,
      issue.status,
      issue.assignee || null,
      issue.priority
    );
    return { ...issue, id, createdAt: now };
  },

  getAll(filters?: { status?: string }): QualityIssue[] {
    let query = 'SELECT * FROM quality_issues';
    const params: unknown[] = [];

    if (filters?.status) {
      query += ' WHERE status = ?';
      params.push(filters.status);
    }
    query += ' ORDER BY created_at DESC';

    const rows = db.prepare(query).all(...params) as Array<{
      id: string;
      execution_id: string;
      rule_id: string;
      rule_name: string;
      table_name: string;
      column_name: string;
      row_identifier: string;
      issue_type: string;
      description: string;
      status: string;
      assignee: string | null;
      priority: string;
      created_at: string;
      resolved_at: string | null;
    }>;
    return rows.map(row => ({
      id: row.id,
      executionId: row.execution_id,
      ruleId: row.rule_id,
      ruleName: row.rule_name,
      tableName: row.table_name,
      columnName: row.column_name,
      rowIdentifier: row.row_identifier,
      issueType: row.issue_type,
      description: row.description,
      status: row.status as QualityIssue['status'],
      assignee: row.assignee || undefined,
      priority: row.priority as QualityIssue['priority'],
      createdAt: formatDate(row.created_at)!,
      resolvedAt: formatDate(row.resolved_at),
    }));
  },

  update(id: string, updates: Partial<QualityIssue>): void {
    const setClauses: string[] = [];
    const values: unknown[] = [];

    if (updates.status !== undefined) {
      setClauses.push('status = ?');
      values.push(updates.status);
      if (updates.status === 'resolved') {
        setClauses.push('resolved_at = ?');
        values.push(new Date().toISOString());
      }
    }
    if (updates.assignee !== undefined) {
      setClauses.push('assignee = ?');
      values.push(updates.assignee || null);
    }
    if (updates.priority !== undefined) {
      setClauses.push('priority = ?');
      values.push(updates.priority);
    }

    if (setClauses.length > 0) {
      values.push(id);
      db.prepare(`UPDATE quality_issues SET ${setClauses.join(', ')} WHERE id = ?`).run(...values);
    }
  },
};

export const statsRepository = {
  getOverview(): OverviewStats {
    const totalRules = (db.prepare('SELECT COUNT(*) as count FROM data_quality_rules').get() as { count: number }).count;
    const activeRules = (db.prepare('SELECT COUNT(*) as count FROM data_quality_rules WHERE enabled = 1').get() as { count: number }).count;
    const totalTasks = (db.prepare('SELECT COUNT(*) as count FROM scheduled_tasks').get() as { count: number }).count;
    const totalExecutions = (db.prepare('SELECT COUNT(*) as count FROM task_executions').get() as { count: number }).count;
    const openIssues = (db.prepare("SELECT COUNT(*) as count FROM quality_issues WHERE status != 'resolved'").get() as { count: number }).count;
    const avgScoreRow = db.prepare('SELECT AVG(quality_score) as avg FROM task_executions WHERE quality_score > 0').get() as { avg: number | null };

    return {
      totalRules,
      activeRules,
      totalTasks,
      totalExecutions,
      openIssues,
      avgQualityScore: avgScoreRow.avg ? Math.round(avgScoreRow.avg * 100) / 100 : 0,
    };
  },

  getQualityTrend(days = 7): TrendDataPoint[] {
    const rows = db.prepare(`
      SELECT DATE(start_time) as date, AVG(quality_score) as score
      FROM task_executions
      WHERE start_time >= DATE('now', '-' || ? || ' days')
      GROUP BY DATE(start_time)
      ORDER BY date ASC
    `).all(days) as Array<{ date: string; score: number }>;

    return rows.map(row => ({
      date: row.date,
      value: Math.round(row.score * 100) / 100,
    }));
  },

  getIssuesTrend(days = 7): TrendDataPoint[] {
    const rows = db.prepare(`
      SELECT DATE(created_at) as date, COUNT(*) as count
      FROM quality_issues
      WHERE created_at >= DATE('now', '-' || ? || ' days')
      GROUP BY DATE(created_at)
      ORDER BY date ASC
    `).all(days) as Array<{ date: string; count: number }>;

    return rows.map(row => ({
      date: row.date,
      value: row.count,
    }));
  },

  getQualityTrendWithThreshold(days = 7): import('../../shared/types.js').TrendDataWithThreshold[] {
    const extendedDays = days * 2;
    const rows = db.prepare(`
      SELECT DATE(start_time) as date, AVG(quality_score) as score
      FROM task_executions
      WHERE start_time >= DATE('now', '-' || ? || ' days')
      GROUP BY DATE(start_time)
      ORDER BY date ASC
    `).all(extendedDays) as Array<{ date: string; score: number }>;

    const allData = rows.map(row => ({
      date: row.date,
      value: Math.round(row.score * 100) / 100,
    }));

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);
    const cutoffStr = cutoffDate.toISOString().split('T')[0];

    return computeDynamicThreshold(allData, cutoffStr, true);
  },

  getIssuesTrendWithThreshold(days = 7): import('../../shared/types.js').TrendDataWithThreshold[] {
    const extendedDays = days * 2;
    const rows = db.prepare(`
      SELECT DATE(created_at) as date, COUNT(*) as count
      FROM quality_issues
      WHERE created_at >= DATE('now', '-' || ? || ' days')
      GROUP BY DATE(created_at)
      ORDER BY date ASC
    `).all(extendedDays) as Array<{ date: string; count: number }>;

    const allData = rows.map(row => ({
      date: row.date,
      value: row.count,
    }));

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);
    const cutoffStr = cutoffDate.toISOString().split('T')[0];

    return computeDynamicThreshold(allData, cutoffStr, false);
  },
};
