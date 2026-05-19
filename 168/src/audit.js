import fs from 'fs/promises';
import path from 'path';

class ConfigAuditLogger {
  constructor(options = {}) {
    this.logPath = options.logPath || './config-audit.log';
    this.maxEntries = options.maxEntries || 1000;
    this.consoleOutput = options.consoleOutput !== false;
    this.entries = [];
  }

  createEntry(action, data = {}) {
    return {
      id: Date.now() + '-' + Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toISOString(),
      action,
      ...data
    };
  }

  logLoad(config, source) {
    const entry = this.createEntry('LOAD', {
      source,
      configKeys: Object.keys(config)
    });
    this.write(entry);
    return entry;
  }

  logChange(oldConfig, newConfig, source = 'hot-reload') {
    const diff = this.calculateDiff(oldConfig, newConfig);
    const entry = this.createEntry('CHANGE', {
      source,
      changes: diff.changes,
      added: diff.added,
      removed: diff.removed
    });
    this.write(entry);
    return entry;
  }

  logValidationPass(config) {
    const entry = this.createEntry('VALIDATION_PASS', {
      configKeys: Object.keys(config)
    });
    this.write(entry);
    return entry;
  }

  logValidationFail(errors) {
    const entry = this.createEntry('VALIDATION_FAIL', {
      errorCount: errors.length,
      errors: errors.map(e => ({ path: e.path, message: e.message }))
    });
    this.write(entry);
    return entry;
  }

  logPush(target, status, config, error = null) {
    const entry = this.createEntry('PUSH', {
      target,
      status,
      configKeys: Object.keys(config),
      error: error ? error.message : null
    });
    this.write(entry);
    return entry;
  }

  logEncrypt(paths) {
    const entry = this.createEntry('ENCRYPT', {
      encryptedPaths: paths
    });
    this.write(entry);
    return entry;
  }

  logDecrypt(paths) {
    const entry = this.createEntry('DECRYPT', {
      decryptedPaths: paths
    });
    this.write(entry);
    return entry;
  }

  calculateDiff(oldObj, newObj, prefix = '') {
    const changes = [];
    const added = [];
    const removed = [];

    const allKeys = new Set([...Object.keys(oldObj || {}), ...Object.keys(newObj || {})]);

    for (const key of allKeys) {
      const path = prefix ? `${prefix}.${key}` : key;
      const oldVal = oldObj ? oldObj[key] : undefined;
      const newVal = newObj ? newObj[key] : undefined;

      if (oldVal === undefined && newVal !== undefined) {
        added.push({ path, newValue: newVal });
      } else if (newVal === undefined && oldVal !== undefined) {
        removed.push({ path, oldValue: oldVal });
      } else if (typeof oldVal === 'object' && typeof newVal === 'object' && oldVal !== null && newVal !== null) {
        const nestedDiff = this.calculateDiff(oldVal, newVal, path);
        changes.push(...nestedDiff.changes);
        added.push(...nestedDiff.added);
        removed.push(...nestedDiff.removed);
      } else if (JSON.stringify(oldVal) !== JSON.stringify(newVal)) {
        changes.push({ path, oldValue: oldVal, newValue: newVal });
      }
    }

    return { changes, added, removed };
  }

  async write(entry) {
    this.entries.push(entry);
    
    if (this.entries.length > this.maxEntries) {
      this.entries = this.entries.slice(-this.maxEntries);
    }

    if (this.consoleOutput) {
      const time = new Date(entry.timestamp).toLocaleTimeString();
      console.log(`[AUDIT ${time}] ${entry.action}:`, JSON.stringify({
        ...entry,
        id: undefined,
        timestamp: undefined,
        action: undefined
      }));
    }

    try {
      const logDir = path.dirname(this.logPath);
      await fs.mkdir(logDir, { recursive: true });
      
      const logLine = JSON.stringify(entry) + '\n';
      await fs.appendFile(this.logPath, logLine);
    } catch (error) {
      console.error('写入审计日志失败:', error.message);
    }
  }

  async getHistory(filter = {}) {
    try {
      const content = await fs.readFile(this.logPath, 'utf8');
      const entries = content.split('\n')
        .filter(line => line.trim())
        .map(line => JSON.parse(line));

      let result = entries;

      if (filter.action) {
        result = result.filter(e => e.action === filter.action);
      }

      if (filter.startTime) {
        result = result.filter(e => e.timestamp >= filter.startTime);
      }

      if (filter.endTime) {
        result = result.filter(e => e.timestamp <= filter.endTime);
      }

      if (filter.limit) {
        result = result.slice(-filter.limit);
      }

      return result.reverse();
    } catch (error) {
      return this.entries;
    }
  }

  async clear() {
    try {
      await fs.unlink(this.logPath);
      this.entries = [];
    } catch (error) {
    }
  }

  formatEntry(entry) {
    const time = new Date(entry.timestamp).toLocaleString();
    let details = '';

    switch (entry.action) {
      case 'LOAD':
        details = `从 ${entry.source} 加载配置，共 ${entry.configKeys?.length || 0} 个字段`;
        break;
      case 'CHANGE':
        details = `${entry.changes?.length || 0} 个变更, ${entry.added?.length || 0} 个新增, ${entry.removed?.length || 0} 个删除`;
        break;
      case 'VALIDATION_PASS':
        details = '配置校验通过';
        break;
      case 'VALIDATION_FAIL':
        details = `配置校验失败，${entry.errorCount} 个错误`;
        break;
      case 'PUSH':
        details = `推送到 ${entry.target}，状态: ${entry.status}`;
        break;
      case 'ENCRYPT':
        details = `加密 ${entry.encryptedPaths?.length || 0} 个字段`;
        break;
      case 'DECRYPT':
        details = `解密 ${entry.decryptedPaths?.length || 0} 个字段`;
        break;
    }

    return `[${time}] ${entry.action}: ${details}`;
  }
}

export default ConfigAuditLogger;
