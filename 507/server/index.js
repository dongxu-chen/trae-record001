const express = require('express')
const cors = require('cors')
const bodyParser = require('body-parser')

const dataAnalyzer = require('./analyzer/dataAnalyzer')
const ruleEngine = require('./engine/ruleEngine')

const learningStore = {
  history: [],
  patternMemory: {},
  columnTypeMemory: {},
  coOccurrenceMap: {}
}

const referenceTables = {}

const auditEntries = []

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(bodyParser.json({ limit: '10mb' }))

app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    message: '智能填充服务运行正常',
    features: ['analyze', 'rules', 'fill', 'learning', 'crossTable', 'audit']
  })
})

app.post('/api/analyze', (req, res) => {
  try {
    const { columnData, columnName } = req.body
    if (!columnData) return res.status(400).json({ error: '缺少列数据' })
    const result = dataAnalyzer.analyzeColumn(columnData, columnName || '未命名')
    res.json(result)
  } catch (error) {
    console.error('分析错误:', error)
    res.status(500).json({ error: '数据分析失败', message: error.message })
  }
})

app.post('/api/analyze/batch', (req, res) => {
  try {
    const { data } = req.body
    if (!data || !Array.isArray(data)) return res.status(400).json({ error: '缺少数据' })
    const result = dataAnalyzer.analyzeAllColumns(data)
    res.json(result)
  } catch (error) {
    console.error('批量分析错误:', error)
    res.status(500).json({ error: '批量分析失败', message: error.message })
  }
})

app.post('/api/rules/recommend', (req, res) => {
  try {
    const { analysis } = req.body
    if (!analysis) return res.status(400).json({ error: '缺少分析结果' })
    const rules = ruleEngine.recommendRules(analysis)
    res.json(rules)
  } catch (error) {
    console.error('规则推荐错误:', error)
    res.status(500).json({ error: '规则推荐失败', message: error.message })
  }
})

app.post('/api/fill/execute', (req, res) => {
  try {
    const { rule, columnData, config, fullData, colIndex } = req.body
    if (!rule || !columnData) return res.status(400).json({ error: '缺少必要参数' })
    const result = ruleEngine.executeRule(rule, columnData, config || {}, fullData || [], colIndex || 0)
    res.json({ result })
  } catch (error) {
    console.error('填充执行错误:', error)
    res.status(500).json({ error: '填充执行失败', message: error.message })
  }
})

app.post('/api/fill/batch', (req, res) => {
  try {
    const { data, rules } = req.body
    if (!data || !rules) return res.status(400).json({ error: '缺少必要参数' })

    let resultData = JSON.parse(JSON.stringify(data))
    for (const { colIndex, rule, config } of rules) {
      const columnData = resultData.slice(1).map(row => row[colIndex])
      const filledColumn = ruleEngine.executeRule(rule, columnData, config || {}, resultData, colIndex)
      resultData = resultData.map((row, rowIndex) => {
        if (rowIndex === 0) return row
        const newRow = [...row]
        if (filledColumn[rowIndex - 1] !== undefined) newRow[colIndex] = filledColumn[rowIndex - 1]
        return newRow
      })
    }
    res.json({ data: resultData })
  } catch (error) {
    console.error('批量填充错误:', error)
    res.status(500).json({ error: '批量填充失败', message: error.message })
  }
})

app.get('/api/rules', (req, res) => {
  try {
    const rules = ruleEngine.getAllRules()
    res.json(rules)
  } catch (error) {
    console.error('获取规则错误:', error)
    res.status(500).json({ error: '获取规则失败', message: error.message })
  }
})

app.post('/api/learning/record', (req, res) => {
  try {
    const operation = req.body
    const record = {
      id: Date.now().toString(36),
      timestamp: new Date().toISOString(),
      ...operation
    }
    learningStore.history.push(record)
    if (learningStore.history.length > 500) {
      learningStore.history = learningStore.history.slice(-500)
    }

    const key = `${operation.dataType}:${operation.ruleId}`
    if (!learningStore.patternMemory[key]) {
      learningStore.patternMemory[key] = { count: 0, ruleId: operation.ruleId, ruleName: operation.ruleName, dataType: operation.dataType }
    }
    learningStore.patternMemory[key].count++

    if (operation.columnName) {
      const colKey = operation.columnName.toLowerCase()
      if (!learningStore.columnTypeMemory[colKey]) learningStore.columnTypeMemory[colKey] = {}
      if (!learningStore.columnTypeMemory[colKey][operation.ruleId]) learningStore.columnTypeMemory[colKey][operation.ruleId] = { count: 0, ruleName: operation.ruleName }
      learningStore.columnTypeMemory[colKey][operation.ruleId].count++
    }

    res.json({ success: true, record })
  } catch (error) {
    console.error('学习记录错误:', error)
    res.status(500).json({ error: '学习记录失败', message: error.message })
  }
})

app.get('/api/learning/suggest', (req, res) => {
  try {
    const { columnName, dataType } = req.query
    const suggestions = []

    if (columnName) {
      const colKey = columnName.toLowerCase()
      const colMem = learningStore.columnTypeMemory[colKey]
      if (colMem) {
        Object.entries(colMem).forEach(([ruleId, data]) => {
          suggestions.push({
            source: 'history_column',
            ruleId,
            ruleName: data.ruleName,
            confidence: Math.min(0.95, 0.5 + data.count * 0.1),
            reason: `此列曾${data.count}次使用「${data.ruleName}」填充`
          })
        })
      }
    }

    if (dataType) {
      Object.values(learningStore.patternMemory)
        .filter(mem => mem.dataType === dataType)
        .sort((a, b) => b.count - a.count)
        .forEach(mem => {
          if (!suggestions.find(s => s.ruleId === mem.ruleId)) {
            suggestions.push({
              source: 'history_type',
              ruleId: mem.ruleId,
              ruleName: mem.ruleName,
              confidence: Math.min(0.8, 0.3 + mem.count * 0.05),
              reason: `类似类型数据曾${mem.count}次使用「${mem.ruleName}」`
            })
          }
        })
    }

    res.json({ suggestions: suggestions.sort((a, b) => b.confidence - a.confidence).slice(0, 5) })
  } catch (error) {
    console.error('AI建议错误:', error)
    res.status(500).json({ error: 'AI建议失败', message: error.message })
  }
})

app.get('/api/learning/summary', (req, res) => {
  try {
    res.json({
      totalOperations: learningStore.history.length,
      learnedColumnPatterns: Object.keys(learningStore.columnTypeMemory).length,
      learnedTypePatterns: Object.keys(learningStore.patternMemory).length,
      recentOperations: learningStore.history.slice(-10).reverse()
    })
  } catch (error) {
    console.error('学习摘要错误:', error)
    res.status(500).json({ error: '学习摘要失败', message: error.message })
  }
})

app.post('/api/cross-table/add', (req, res) => {
  try {
    const { name, data, keyColumn, valueColumns } = req.body
    if (!name || !data || data.length < 2) return res.status(400).json({ error: '缺少必要参数' })

    const headers = data[0]
    const rows = data.slice(1)
    const keyColIndex = typeof keyColumn === 'number' ? keyColumn : headers.indexOf(keyColumn)
    if (keyColIndex === -1) return res.status(400).json({ error: '键列未找到' })

    const valueColIndices = (valueColumns || []).map(vc => typeof vc === 'number' ? vc : headers.indexOf(vc)).filter(idx => idx !== -1)

    const lookupMap = {}
    rows.forEach(row => {
      const keyValue = String(row[keyColIndex] || '').trim()
      if (!keyValue) return
      if (!lookupMap[keyValue]) lookupMap[keyValue] = {}
      valueColIndices.forEach((colIdx) => {
        lookupMap[keyValue][headers[colIdx]] = row[colIdx]
      })
    })

    referenceTables[name] = {
      name,
      headers,
      keyColumn: headers[keyColIndex],
      valueColumns: valueColIndices.map(i => headers[i]),
      lookupMap,
      rowCount: rows.length,
      createdAt: new Date().toISOString()
    }

    res.json({ success: true, table: { name, keyColumn: headers[keyColIndex], valueColumns: valueColIndices.map(i => headers[i]), rowCount: rows.length } })
  } catch (error) {
    console.error('添加参考表错误:', error)
    res.status(500).json({ error: '添加参考表失败', message: error.message })
  }
})

app.post('/api/cross-table/lookup', (req, res) => {
  try {
    const { tableName, keyValue, valueColumn } = req.body
    const table = referenceTables[tableName]
    if (!table) return res.status(404).json({ error: '参考表不存在' })

    const entry = table.lookupMap[String(keyValue).trim()]
    if (!entry) return res.json({ found: false, value: null })

    if (valueColumn) {
      res.json({ found: true, value: entry[valueColumn] })
    } else {
      res.json({ found: true, value: entry })
    }
  } catch (error) {
    console.error('跨表查找错误:', error)
    res.status(500).json({ error: '跨表查找失败', message: error.message })
  }
})

app.get('/api/cross-table/list', (req, res) => {
  try {
    const tables = Object.entries(referenceTables).map(([name, table]) => ({
      name,
      keyColumn: table.keyColumn,
      valueColumns: table.valueColumns,
      rowCount: table.rowCount,
      createdAt: table.createdAt
    }))
    res.json({ tables })
  } catch (error) {
    console.error('获取参考表列表错误:', error)
    res.status(500).json({ error: '获取参考表列表失败', message: error.message })
  }
})

app.delete('/api/cross-table/:name', (req, res) => {
  try {
    const name = req.params.name
    if (!referenceTables[name]) return res.status(404).json({ error: '参考表不存在' })
    delete referenceTables[name]
    res.json({ success: true })
  } catch (error) {
    console.error('删除参考表错误:', error)
    res.status(500).json({ error: '删除参考表失败', message: error.message })
  }
})

app.post('/api/audit/log', (req, res) => {
  try {
    const operation = req.body
    const entry = {
      id: `audit_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
      timestamp: new Date().toISOString(),
      ...operation
    }
    auditEntries.unshift(entry)
    if (auditEntries.length > 1000) auditEntries.splice(1000)
    res.json({ success: true, entry })
  } catch (error) {
    console.error('审计记录错误:', error)
    res.status(500).json({ error: '审计记录失败', message: error.message })
  }
})

app.get('/api/audit/entries', (req, res) => {
  try {
    const { type, columnName, limit = 50 } = req.query
    let result = [...auditEntries]
    if (type) result = result.filter(e => e.type === type)
    if (columnName) result = result.filter(e => e.columnName === columnName)
    res.json({ entries: result.slice(0, parseInt(limit)) })
  } catch (error) {
    console.error('获取审计日志错误:', error)
    res.status(500).json({ error: '获取审计日志失败', message: error.message })
  }
})

app.get('/api/audit/statistics', (req, res) => {
  try {
    const fillOps = auditEntries.filter(e => e.type !== 'revert')
    const ruleCounts = {}
    const columnCounts = {}
    fillOps.forEach(op => {
      ruleCounts[op.ruleName] = (ruleCounts[op.ruleName] || 0) + 1
      columnCounts[op.columnName] = (columnCounts[op.columnName] || 0) + 1
    })
    res.json({
      totalOperations: fillOps.length,
      totalCellsFilled: fillOps.reduce((sum, op) => sum + (op.fillCount || 0), 0),
      ruleCounts,
      columnCounts
    })
  } catch (error) {
    console.error('审计统计错误:', error)
    res.status(500).json({ error: '审计统计失败', message: error.message })
  }
})

app.post('/api/import/csv', (req, res) => {
  try {
    const { csv } = req.body
    if (!csv) return res.status(400).json({ error: '缺少CSV数据' })
    const lines = csv.split('\n').filter(line => line.trim())
    const data = lines.map(line => line.split(',').map(v => v.trim().replace(/^"|"$/g, '')))
    res.json({ data })
  } catch (error) {
    console.error('CSV解析错误:', error)
    res.status(500).json({ error: 'CSV解析失败', message: error.message })
  }
})

app.post('/api/export/csv', (req, res) => {
  try {
    const { data } = req.body
    if (!data) return res.status(400).json({ error: '缺少数据' })
    const csv = data.map(row => row.map(cell => { const str = String(cell || ''); return str.includes(',') ? `"${str}"` : str }).join(',')).join('\n')
    res.setHeader('Content-Type', 'text/csv')
    res.setHeader('Content-Disposition', 'attachment; filename="data.csv"')
    res.send(csv)
  } catch (error) {
    console.error('CSV导出错误:', error)
    res.status(500).json({ error: 'CSV导出失败', message: error.message })
  }
})

app.listen(PORT, () => {
  console.log(`\n========================================`)
  console.log(`  智能填充服务已启动`)
  console.log(`  端口: ${PORT}`)
  console.log(`  功能: 分析/规则/填充/学习/跨表/审计`)
  console.log(`  健康检查: http://localhost:${PORT}/api/health`)
  console.log(`========================================\n`)
})
