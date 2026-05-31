import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const dbPath = path.join(__dirname, '../../data/quality.db');

export function initDatabase() {
  const db = new Database(dbPath);

  db.exec(`
    CREATE TABLE IF NOT EXISTS rule_templates (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      type TEXT NOT NULL,
      default_config TEXT NOT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS data_quality_rules (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      description TEXT,
      type TEXT NOT NULL,
      data_source TEXT NOT NULL,
      table_name TEXT NOT NULL,
      column_name TEXT NOT NULL,
      config TEXT NOT NULL,
      enabled BOOLEAN DEFAULT 1,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS scheduled_tasks (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      cron_expression TEXT NOT NULL,
      enabled BOOLEAN DEFAULT 1,
      last_run_at DATETIME,
      next_run_at DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS scheduled_task_rules (
      task_id TEXT NOT NULL,
      rule_id TEXT NOT NULL,
      PRIMARY KEY (task_id, rule_id),
      FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id) ON DELETE CASCADE,
      FOREIGN KEY (rule_id) REFERENCES data_quality_rules(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS task_executions (
      id TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      task_name TEXT NOT NULL,
      status TEXT NOT NULL,
      start_time DATETIME NOT NULL,
      end_time DATETIME,
      total_records INTEGER DEFAULT 0,
      failed_records INTEGER DEFAULT 0,
      quality_score REAL DEFAULT 100,
      FOREIGN KEY (task_id) REFERENCES scheduled_tasks(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS quality_issues (
      id TEXT PRIMARY KEY,
      execution_id TEXT NOT NULL,
      rule_id TEXT NOT NULL,
      rule_name TEXT NOT NULL,
      table_name TEXT NOT NULL,
      column_name TEXT NOT NULL,
      row_identifier TEXT NOT NULL,
      issue_type TEXT NOT NULL,
      description TEXT,
      status TEXT NOT NULL DEFAULT 'open',
      assignee TEXT,
      priority TEXT NOT NULL DEFAULT 'medium',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      resolved_at DATETIME,
      FOREIGN KEY (execution_id) REFERENCES task_executions(id) ON DELETE CASCADE,
      FOREIGN KEY (rule_id) REFERENCES data_quality_rules(id)
    );
  `);

  const templateCount = db.prepare('SELECT COUNT(*) as count FROM rule_templates').get() as { count: number };
  if (templateCount.count === 0) {
    const insertTemplate = db.prepare(`
      INSERT INTO rule_templates (id, name, description, type, default_config)
      VALUES (?, ?, ?, ?, ?)
    `);

    const templates = [
      { id: 'tpl_null_check', name: '非空校验', description: '确保指定列不包含空值', type: 'null_check', config: '{"nullCheck": {"allowNull": false}}' },
      { id: 'tpl_uniqueness', name: '唯一性校验', description: '确保指定列值唯一', type: 'uniqueness', config: '{"uniqueness": {"columns": []}}' },
      { id: 'tpl_value_range', name: '值域范围校验', description: '校验数值范围或枚举值', type: 'value_range', config: '{"valueRange": {"min": null, "max": null, "allowedValues": []}}' },
      { id: 'tpl_dependency', name: '外键依赖校验', description: '确保关联表数据存在', type: 'dependency', config: '{"dependency": {"targetTable": "", "targetColumn": ""}}' },
    ];

    templates.forEach(t => {
      insertTemplate.run(t.id, t.name, t.description, t.type, t.config);
    });
  }

  db.pragma('foreign_keys = ON');
  return db;
}

export const db = initDatabase();
export default db;
