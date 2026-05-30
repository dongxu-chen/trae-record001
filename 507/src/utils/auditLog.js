class AuditLog {
  constructor() {
    this.entries = []
    this.loadFromStorage()
  }

  logFillOperation(operation) {
    const entry = {
      id: this.generateId(),
      timestamp: new Date().toISOString(),
      type: operation.type || 'fill',
      operator: operation.operator || 'user',
      
      columnName: operation.columnName || '',
      columnType: operation.columnType || '',
      columnKey: operation.columnKey || '',
      
      ruleId: operation.ruleId || '',
      ruleName: operation.ruleName || '',
      ruleConfig: this.sanitizeConfig(operation.ruleConfig),
      
      affectedRows: operation.affectedRows || [],
      affectedRange: operation.affectedRange || '',
      totalAffected: operation.affectedRows?.length || 0,
      totalRows: operation.totalRows || 0,
      
      fillCount: operation.fillCount || 0,
      skipCount: operation.skipCount || 0,
      errorCount: operation.errorCount || 0,
      
      beforeSample: this.takeSample(operation.beforeData),
      afterSample: this.takeSample(operation.afterData),
      
      duration: operation.duration || 0,
      
      reverted: false,
      revertedAt: null,
      revertEntryId: null
    }

    this.entries.unshift(entry)

    if (this.entries.length > 1000) {
      this.entries = this.entries.slice(0, 1000)
    }

    this.saveToStorage()
    return entry
  }

  logBatchOperation(operations) {
    const batchId = this.generateId()
    const entries = []

    operations.forEach(op => {
      const entry = this.logFillOperation({
        ...op,
        type: 'batch_fill',
        batchId
      })
      entries.push(entry)
    })

    return { batchId, entries }
  }

  logRevert(targetEntryId) {
    const target = this.entries.find(e => e.id === targetEntryId)
    if (!target) return null

    target.reverted = true
    target.revertedAt = new Date().toISOString()

    const revertEntry = {
      id: this.generateId(),
      timestamp: new Date().toISOString(),
      type: 'revert',
      operator: 'user',
      targetEntryId,
      targetRuleName: target.ruleName,
      targetColumnName: target.columnName,
      affectedRows: target.affectedRows
    }

    this.entries.unshift(revertEntry)
    this.saveToStorage()
    return revertEntry
  }

  getEntries(filters = {}) {
    let result = [...this.entries]

    if (filters.type) {
      result = result.filter(e => e.type === filters.type)
    }

    if (filters.columnName) {
      result = result.filter(e => e.columnName === filters.columnName)
    }

    if (filters.ruleId) {
      result = result.filter(e => e.ruleId === filters.ruleId)
    }

    if (filters.startDate) {
      result = result.filter(e => e.timestamp >= filters.startDate)
    }

    if (filters.endDate) {
      result = result.filter(e => e.timestamp <= filters.endDate)
    }

    if (filters.reverted !== undefined) {
      result = result.filter(e => e.reverted === filters.reverted)
    }

    if (filters.limit) {
      result = result.slice(0, filters.limit)
    }

    return result
  }

  getImpactSummary(entryId) {
    const entry = this.entries.find(e => e.id === entryId)
    if (!entry) return null

    return {
      columnName: entry.columnName,
      ruleName: entry.ruleName,
      totalAffected: entry.totalAffected,
      fillCount: entry.fillCount,
      skipCount: entry.skipCount,
      affectedRows: entry.affectedRows,
      beforeSample: entry.beforeSample,
      afterSample: entry.afterSample,
      coveragePercent: entry.totalRows > 0 
        ? Math.round((entry.totalAffected / entry.totalRows) * 100) 
        : 0,
      fillPercent: entry.totalAffected > 0 
        ? Math.round((entry.fillCount / entry.totalAffected) * 100) 
        : 0
    }
  }

  getColumnHistory(columnName) {
    return this.entries
      .filter(e => e.columnName === columnName && e.type !== 'revert')
      .map(e => ({
        id: e.id,
        timestamp: e.timestamp,
        ruleName: e.ruleName,
        fillCount: e.fillCount,
        reverted: e.reverted
      }))
  }

  getStatistics() {
    const fillOps = this.entries.filter(e => e.type !== 'revert')
    const revertOps = this.entries.filter(e => e.type === 'revert')

    const ruleCounts = {}
    const columnCounts = {}

    fillOps.forEach(op => {
      ruleCounts[op.ruleName] = (ruleCounts[op.ruleName] || 0) + 1
      columnCounts[op.columnName] = (columnCounts[op.columnName] || 0) + 1
    })

    const totalFilled = fillOps.reduce((sum, op) => sum + (op.fillCount || 0), 0)
    const today = new Date().toISOString().split('T')[0]
    const todayOps = fillOps.filter(e => e.timestamp.startsWith(today))

    return {
      totalOperations: fillOps.length,
      totalReverts: revertOps.length,
      totalCellsFilled: totalFilled,
      todayOperations: todayOps.length,
      todayCellsFilled: todayOps.reduce((sum, op) => sum + (op.fillCount || 0), 0),
      ruleCounts,
      columnCounts,
      mostUsedRule: Object.entries(ruleCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || '-',
      mostFilledColumn: Object.entries(columnCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || '-'
    }
  }

  exportLog(format = 'json') {
    if (format === 'csv') {
      const headers = ['timestamp', 'type', 'columnName', 'ruleName', 'fillCount', 'skipCount', 'affectedRows', 'reverted']
      const rows = this.entries.map(e => [
        e.timestamp,
        e.type,
        e.columnName,
        e.ruleName,
        e.fillCount,
        e.skipCount,
        e.affectedRows.join(';'),
        e.reverted
      ])
      return [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    }

    return JSON.stringify(this.entries, null, 2)
  }

  clearLog() {
    this.entries = []
    this.saveToStorage()
  }

  sanitizeConfig(config) {
    if (!config) return {}
    const sanitized = { ...config }
    delete sanitized._customApply
    delete sanitized._geometric
    delete sanitized._ratio
    delete sanitized._prefix
    delete sanitized._startNum
    delete sanitized._step
    delete sanitized._digitLen
    return sanitized
  }

  takeSample(data, maxItems = 5) {
    if (!data || !Array.isArray(data)) return []
    return data.slice(0, maxItems)
  }

  generateId() {
    return `audit_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`
  }

  saveToStorage() {
    try {
      localStorage.setItem('smartFill_auditLog', JSON.stringify(this.entries))
    } catch (e) {
      if (this.entries.length > 100) {
        this.entries = this.entries.slice(0, 100)
        try {
          localStorage.setItem('smartFill_auditLog', JSON.stringify(this.entries))
        } catch (e2) {
          // give up
        }
      }
    }
  }

  loadFromStorage() {
    try {
      const stored = localStorage.getItem('smartFill_auditLog')
      if (stored) {
        this.entries = JSON.parse(stored)
      }
    } catch (e) {
      this.entries = []
    }
  }
}

export default AuditLog
