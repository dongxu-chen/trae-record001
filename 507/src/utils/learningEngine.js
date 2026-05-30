class LearningEngine {
  constructor() {
    this.history = []
    this.patternMemory = {}
    this.columnTypeMemory = {}
    this.coOccurrenceMap = {}
    this.loadFromStorage()
  }

  recordFillOperation(operation) {
    const record = {
      id: Date.now() + Math.random().toString(36).substr(2, 6),
      timestamp: new Date().toISOString(),
      columnName: operation.columnName,
      columnType: operation.columnType,
      dataType: operation.dataType,
      ruleId: operation.ruleId,
      ruleName: operation.ruleName,
      ruleConfig: { ...operation.ruleConfig },
      affectedRows: operation.affectedRows || [],
      totalRows: operation.totalRows,
      fillCount: operation.fillCount || 0,
      sampleBefore: operation.sampleBefore || [],
      sampleAfter: operation.sampleAfter || [],
      dataHash: this.hashData(operation.sampleBefore)
    }

    this.history.push(record)
    this.updatePatternMemory(record)
    this.updateColumnTypeMemory(record)
    this.updateCoOccurrence(record)

    if (this.history.length > 500) {
      this.history = this.history.slice(-500)
    }

    this.saveToStorage()
    return record
  }

  updatePatternMemory(record) {
    const key = `${record.dataType}:${record.ruleId}`
    if (!this.patternMemory[key]) {
      this.patternMemory[key] = {
        count: 0,
        ruleId: record.ruleId,
        ruleName: record.ruleName,
        dataType: record.dataType,
        avgFillCount: 0,
        configs: []
      }
    }

    const mem = this.patternMemory[key]
    mem.count++
    mem.avgFillCount = (mem.avgFillCount * (mem.count - 1) + record.fillCount) / mem.count

    const configStr = JSON.stringify(record.ruleConfig)
    const existingConfig = mem.configs.find(c => JSON.stringify(c.config) === configStr)
    if (existingConfig) {
      existingConfig.count++
    } else if (mem.configs.length < 20) {
      mem.configs.push({ config: record.ruleConfig, count: 1 })
    }
  }

  updateColumnTypeMemory(record) {
    const colKey = record.columnName?.toLowerCase() || 'unknown'
    if (!this.columnTypeMemory[colKey]) {
      this.columnTypeMemory[colKey] = {}
    }

    const typeMem = this.columnTypeMemory[colKey]
    const ruleKey = record.ruleId
    if (!typeMem[ruleKey]) {
      typeMem[ruleKey] = {
        count: 0,
        ruleName: record.ruleName,
        configs: []
      }
    }

    typeMem[ruleKey].count++
    const configStr = JSON.stringify(record.ruleConfig)
    const existing = typeMem[ruleKey].configs.find(c => JSON.stringify(c.config) === configStr)
    if (existing) {
      existing.count++
    } else if (typeMem[ruleKey].configs.length < 10) {
      typeMem[ruleKey].configs.push({ config: record.ruleConfig, count: 1 })
    }
  }

  updateCoOccurrence(record) {
    const patterns = this.extractPatterns(record.sampleAfter)
    patterns.forEach(pattern => {
      if (!this.coOccurrenceMap[pattern]) {
        this.coOccurrenceMap[pattern] = { ruleIds: {}, count: 0 }
      }
      this.coOccurrenceMap[pattern].count++
      if (!this.coOccurrenceMap[pattern].ruleIds[record.ruleId]) {
        this.coOccurrenceMap[pattern].ruleIds[record.ruleId] = 0
      }
      this.coOccurrenceMap[pattern].ruleIds[record.ruleId]++
    })
  }

  extractPatterns(values) {
    const patterns = []
    if (!values || values.length === 0) return patterns

    const nums = values.map(Number).filter(n => !isNaN(n))
    if (nums.length >= 2) {
      const diffs = []
      for (let i = 1; i < nums.length; i++) diffs.push(nums[i] - nums[i - 1])
      const uniqueDiffs = [...new Set(diffs)]
      if (uniqueDiffs.length === 1) {
        patterns.push(`seq:step=${uniqueDiffs[0]}`)
      }
    }

    const uniqueStrs = [...new Set(values.map(String))]
    if (uniqueStrs.length <= 5 && uniqueStrs.length < values.length) {
      patterns.push(`cat:${uniqueStrs.length}`)
    }

    return patterns
  }

  getAISuggestions(columnName, dataType, columnAnalysis) {
    const suggestions = []

    const colKey = columnName?.toLowerCase() || ''
    const colMem = this.columnTypeMemory[colKey]

    if (colMem) {
      Object.entries(colMem)
        .sort((a, b) => b[1].count - a[1].count)
        .forEach(([ruleId, data]) => {
          const bestConfig = data.configs.sort((a, b) => b.count - a.count)[0]
          suggestions.push({
            source: 'history_column',
            sourceLabel: '历史记录(同列)',
            ruleId,
            ruleName: data.ruleName,
            config: bestConfig?.config || {},
            confidence: Math.min(0.95, 0.5 + data.configs.reduce((s, c) => s + c.count, 0) * 0.1),
            reason: `此列曾${data.configs.reduce((s, c) => s + c.count, 0)}次使用「${data.ruleName}」填充`
          })
        })
    }

    if (dataType && this.patternMemory) {
      Object.values(this.patternMemory)
        .filter(mem => mem.dataType === dataType)
        .sort((a, b) => b.count - a.count)
        .forEach(mem => {
          const exists = suggestions.find(s => s.ruleId === mem.ruleId)
          if (!exists) {
            const bestConfig = mem.configs.sort((a, b) => b.count - a.count)[0]
            suggestions.push({
              source: 'history_type',
              sourceLabel: '历史记录(同类型)',
              ruleId: mem.ruleId,
              ruleName: mem.ruleName,
              config: bestConfig?.config || {},
              confidence: Math.min(0.8, 0.3 + mem.count * 0.05),
              reason: `类似类型数据曾${mem.count}次使用「${mem.ruleName}」`
            })
          }
        })
    }

    if (columnAnalysis?.patterns?.length > 0) {
      columnAnalysis.patterns.forEach(pattern => {
        const patternKey = pattern.type === 'arithmetic_sequence' 
          ? `seq:step=${pattern.step}` 
          : `cat:${pattern.values?.length || 0}`
        
        const coMem = this.coOccurrenceMap[patternKey]
        if (coMem) {
          Object.entries(coMem.ruleIds)
            .sort((a, b) => b[1] - a[1])
            .forEach(([ruleId, count]) => {
              const exists = suggestions.find(s => s.ruleId === ruleId)
              if (!exists) {
                suggestions.push({
                  source: 'pattern_match',
                  sourceLabel: '模式匹配',
                  ruleId,
                  ruleName: ruleId,
                  config: {},
                  confidence: Math.min(0.75, count / coOccurrenceMap[patternKey].count + 0.3),
                  reason: `检测到「${pattern.name}」模式，历史匹配${count}次`
                })
              }
            })
        }
      })
    }

    const inferredRules = this.inferFromColumnName(columnName, dataType)
    inferredRules.forEach(inferred => {
      const exists = suggestions.find(s => s.ruleId === inferred.ruleId)
      if (!exists) {
        suggestions.push(inferred)
      }
    })

    return suggestions
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 5)
  }

  inferFromColumnName(columnName, dataType) {
    const inferences = []
    const name = (columnName || '').toLowerCase()

    const rules = [
      { pattern: /工资|薪资|金额|价格|费用/, dataType: 'number', ruleId: 'formula', ruleName: '公式计算', reason: '金额类列通常需要公式计算' },
      { pattern: /日期|时间|入职/, dataType: 'date', ruleId: 'date_sequence', ruleName: '日期序列', reason: '日期类列通常使用日期序列填充' },
      { pattern: /编号|序号|id/, dataType: 'number', ruleId: 'sequence', ruleName: '序列填充', reason: '编号类列通常使用序列填充' },
      { pattern: /部门|类型|类别|分类/, dataType: 'string', ruleId: 'category_cycle', ruleName: '分类循环', reason: '分类列通常使用循环填充' },
      { pattern: /是否|状态|转正/, dataType: 'boolean', ruleId: 'category_cycle', ruleName: '分类循环', reason: '状态列通常使用分类循环' }
    ]

    rules.forEach(rule => {
      if (rule.pattern.test(name) && (!dataType || rule.dataType === dataType)) {
        inferences.push({
          source: 'ai_inference',
          sourceLabel: 'AI推断',
          ruleId: rule.ruleId,
          ruleName: rule.ruleName,
          config: {},
          confidence: 0.6,
          reason: rule.reason
        })
      }
    })

    return inferences
  }

  getHistorySummary() {
    const totalOps = this.history.length
    const ruleUsage = {}
    this.history.forEach(op => {
      if (!ruleUsage[op.ruleId]) {
        ruleUsage[op.ruleId] = { name: op.ruleName, count: 0, totalFilled: 0 }
      }
      ruleUsage[op.ruleId].count++
      ruleUsage[op.ruleId].totalFilled += op.fillCount
    })

    const recentOps = this.history.slice(-10).reverse()

    return {
      totalOperations: totalOps,
      ruleUsage,
      recentOperations: recentOps,
      learnedColumnPatterns: Object.keys(this.columnTypeMemory).length,
      learnedTypePatterns: Object.keys(this.patternMemory).length
    }
  }

  getSimilarColumns(columnName, dataType) {
    const colKey = columnName?.toLowerCase() || ''
    const similar = []

    Object.entries(this.columnTypeMemory).forEach(([key, rules]) => {
      if (key === colKey) return
      const nameSimilarity = this.computeNameSimilarity(colKey, key)
      const hasSameTypeRules = Object.keys(rules).some(ruleId => {
        const patternKey = `${dataType}:${ruleId}`
        return !!this.patternMemory[patternKey]
      })

      if (nameSimilarity > 0.3 || hasSameTypeRules) {
        similar.push({
          columnName: key,
          similarity: nameSimilarity,
          rules: Object.entries(rules).map(([ruleId, data]) => ({
            ruleId,
            ruleName: data.ruleName,
            count: data.configs.reduce((s, c) => s + c.count, 0),
            bestConfig: data.configs.sort((a, b) => b.count - a.count)[0]?.config
          }))
        })
      }
    })

    return similar.sort((a, b) => b.similarity - a.similarity).slice(0, 3)
  }

  computeNameSimilarity(a, b) {
    if (!a || !b) return 0
    if (a === b) return 1
    const setA = new Set(a.split(''))
    const setB = new Set(b.split(''))
    const intersection = new Set([...setA].filter(x => setB.has(x)))
    const union = new Set([...setA, ...setB])
    return intersection.size / union.size
  }

  hashData(values) {
    if (!values || values.length === 0) return ''
    const str = values.slice(0, 10).join('|')
    let hash = 0
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i)
      hash = ((hash << 5) - hash) + char
      hash = hash & hash
    }
    return Math.abs(hash).toString(36)
  }

  clearHistory() {
    this.history = []
    this.patternMemory = {}
    this.columnTypeMemory = {}
    this.coOccurrenceMap = {}
    this.saveToStorage()
  }

  saveToStorage() {
    try {
      const data = {
        history: this.history,
        patternMemory: this.patternMemory,
        columnTypeMemory: this.columnTypeMemory,
        coOccurrenceMap: this.coOccurrenceMap
      }
      localStorage.setItem('smartFill_learningData', JSON.stringify(data))
    } catch (e) {
      // storage full or unavailable
    }
  }

  loadFromStorage() {
    try {
      const stored = localStorage.getItem('smartFill_learningData')
      if (stored) {
        const data = JSON.parse(stored)
        this.history = data.history || []
        this.patternMemory = data.patternMemory || {}
        this.columnTypeMemory = data.columnTypeMemory || {}
        this.coOccurrenceMap = data.coOccurrenceMap || {}
      }
    } catch (e) {
      // corrupted data, start fresh
    }
  }
}

export default LearningEngine
