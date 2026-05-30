import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { HotTable } from '@handsontable/react'
import 'handsontable/dist/handsontable.full.min.css'
import DataAnalyzer from './utils/dataAnalyzer'
import RuleEngine from './utils/ruleEngine'
import LearningEngine from './utils/learningEngine'
import AuditLog from './utils/auditLog'
import Sidebar from './components/Sidebar'

const sampleData = [
  ['序号', '姓名', '入职日期', '部门', '基本工资', '绩效评分', '是否转正'],
  [1, '张三', '2024-01-15', '技术部', 15000, 4.5, true],
  [2, '李四', '2024-02-20', '产品部', 14000, 4.2, true],
  [3, '王五', '2024-03-10', '技术部', 16000, 4.8, true],
  [4, '赵六', '2024-04-05', '市场部', 12000, 3.9, false],
  [5, '钱七', '2024-05-12', '技术部', 18000, 4.9, true],
  [6, '孙八', '2024-06-01', '产品部', 13500, 4.1, false],
  [7, '', '', '', '', '', ''],
  [8, '', '', '', '', '', ''],
  [9, '', '', '', '', '', ''],
  [10, '', '', '', '', '', '']
]

function App() {
  const [data, setData] = useState(sampleData)
  const [selectedColumn, setSelectedColumn] = useState(null)
  const [columnAnalysis, setColumnAnalysis] = useState(null)
  const [recommendedRules, setRecommendedRules] = useState([])
  const [selectedRule, setSelectedRule] = useState(null)
  const [ruleConfig, setRuleConfig] = useState({})
  const [showPreview, setShowPreview] = useState(true)
  const [previewCache, setPreviewCache] = useState({})
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 20 })
  const hotRef = useRef(null)
  const dataHistoryRef = useRef([])

  const dataAnalyzer = useMemo(() => new DataAnalyzer(), [])
  const ruleEngine = useMemo(() => new RuleEngine(), [])
  const learningEngine = useMemo(() => new LearningEngine(), [])
  const auditLog = useMemo(() => new AuditLog(), [])

  const pushHistory = useCallback((currentData) => {
    dataHistoryRef.current.push(JSON.parse(JSON.stringify(currentData)))
    if (dataHistoryRef.current.length > 20) {
      dataHistoryRef.current = dataHistoryRef.current.slice(-20)
    }
  }, [])

  const analyzeColumn = useCallback((colIndex) => {
    if (colIndex === null) return
    
    const columnData = data.slice(1).map(row => row[colIndex])
    const headers = data[0]
    const analysis = dataAnalyzer.analyzeColumn(columnData, headers[colIndex])
    setColumnAnalysis(analysis)
    
    const rules = ruleEngine.recommendRules(analysis)
    setRecommendedRules(rules)
    setSelectedRule(null)
    setRuleConfig({})
    setPreviewCache({})
  }, [data, dataAnalyzer, ruleEngine])

  const handleSelection = useCallback((row, col) => {
    if (col >= 0 && col !== selectedColumn) {
      setSelectedColumn(col)
      analyzeColumn(col)
    }
  }, [selectedColumn, analyzeColumn])

  const handleRuleSelect = (rule) => {
    setSelectedRule(rule)
    setRuleConfig(rule.defaultConfig || {})
    setPreviewCache({})
  }

  const handleConfigChange = (key, value) => {
    setRuleConfig(prev => ({ ...prev, [key]: value }))
    setPreviewCache({})
  }

  const computePreviewForRange = useCallback((startRow, endRow) => {
    if (!selectedRule || selectedColumn === null) return {}

    const columnData = data.slice(1).map(row => row[selectedColumn])
    const newCache = { ...previewCache }

    for (let i = startRow; i <= endRow && i < columnData.length; i++) {
      if (newCache[i] !== undefined) continue

      const originalValue = columnData[i]
      if (originalValue !== '' && originalValue !== null && originalValue !== undefined && ruleConfig.fillEmptyOnly !== false) {
        newCache[i] = originalValue
        continue
      }

      const filledValue = ruleEngine.applyRule(
        selectedRule, ruleConfig, i, columnData, data, selectedColumn, originalValue
      )
      newCache[i] = filledValue
    }

    return newCache
  }, [selectedRule, selectedColumn, ruleConfig, data, ruleEngine, previewCache])

  useEffect(() => {
    if (!showPreview || !selectedRule || selectedColumn === null) {
      setPreviewCache({})
      return
    }

    const newCache = computePreviewForRange(visibleRange.start, visibleRange.end)
    setPreviewCache(newCache)
  }, [showPreview, selectedRule, selectedColumn, ruleConfig, visibleRange, computePreviewForRange])

  const applyFill = () => {
    if (selectedColumn === null) return

    const startTime = performance.now()
    pushHistory(data)

    const columnData = data.slice(1).map(row => row[selectedColumn])
    const fullResult = ruleEngine.executeRule(selectedRule, columnData, ruleConfig, data, selectedColumn)

    const affectedRows = []
    const beforeData = []
    const afterData = []
    let fillCount = 0
    let skipCount = 0

    const newData = data.map((row, rowIndex) => {
      if (rowIndex === 0) return [...row]
      const newRow = [...row]
      const dataIdx = rowIndex - 1
      if (fullResult[dataIdx] !== undefined) {
        const oldVal = row[selectedColumn]
        const newVal = fullResult[dataIdx]
        if (oldVal === '' || oldVal === null || oldVal === undefined) {
          newRow[selectedColumn] = newVal
          affectedRows.push(dataIdx)
          beforeData.push(oldVal)
          afterData.push(newVal)
          fillCount++
        } else {
          skipCount++
        }
      }
      return newRow
    })

    const duration = Math.round(performance.now() - startTime)

    learningEngine.recordFillOperation({
      columnName: data[0][selectedColumn],
      columnType: columnAnalysis?.dataType,
      dataType: columnAnalysis?.dataType,
      ruleId: selectedRule.id,
      ruleName: selectedRule.name,
      ruleConfig,
      affectedRows,
      totalRows: data.length - 1,
      fillCount,
      sampleBefore: beforeData.slice(0, 5),
      sampleAfter: afterData.slice(0, 5)
    })

    auditLog.logFillOperation({
      type: 'fill',
      columnName: data[0][selectedColumn],
      columnType: columnAnalysis?.dataType,
      columnKey: `${selectedColumn}_${data[0][selectedColumn]}`,
      ruleId: selectedRule.id,
      ruleName: selectedRule.name,
      ruleConfig,
      affectedRows,
      totalRows: data.length - 1,
      fillCount,
      skipCount,
      beforeData: beforeData.slice(0, 5),
      afterData: afterData.slice(0, 5),
      duration
    })

    setData(newData)
    setPreviewCache({})
    analyzeColumn(selectedColumn)
  }

  const batchApplyRules = async (rules) => {
    pushHistory(data)

    const startTime = performance.now()
    let newData = [...data]
    const allAffectedRows = []

    for (const { colIndex, rule, config } of rules) {
      const columnData = newData.slice(1).map(row => row[colIndex])
      const result = ruleEngine.executeRule(rule, columnData, config, newData, colIndex)
      
      const beforeData = []
      const afterData = []
      const affectedRows = []

      newData = newData.map((row, rowIndex) => {
        if (rowIndex === 0) return row
        const newRow = [...row]
        const dataIdx = rowIndex - 1
        if (result[dataIdx] !== undefined) {
          const oldVal = row[colIndex]
          const newVal = result[dataIdx]
          if (oldVal === '' || oldVal === null || oldVal === undefined) {
            newRow[colIndex] = newVal
            affectedRows.push(dataIdx)
            beforeData.push(oldVal)
            afterData.push(newVal)
          }
        }
        return newRow
      })

      allAffectedRows.push(...affectedRows)

      learningEngine.recordFillOperation({
        columnName: data[0][colIndex],
        dataType: 'string',
        ruleId: rule.id,
        ruleName: rule.name,
        ruleConfig: config,
        affectedRows,
        totalRows: data.length - 1,
        fillCount: affectedRows.length,
        sampleBefore: beforeData.slice(0, 5),
        sampleAfter: afterData.slice(0, 5)
      })

      auditLog.logFillOperation({
        type: 'batch_fill',
        columnName: data[0][colIndex],
        ruleId: rule.id,
        ruleName: rule.name,
        ruleConfig: config,
        affectedRows,
        totalRows: data.length - 1,
        fillCount: affectedRows.length,
        skipCount: 0,
        beforeData: beforeData.slice(0, 5),
        afterData: afterData.slice(0, 5),
        duration: Math.round(performance.now() - startTime)
      })
    }
    
    setData(newData)
    setSelectedColumn(null)
    setColumnAnalysis(null)
    setRecommendedRules([])
    setSelectedRule(null)
    setPreviewCache({})
  }

  const handleRevert = useCallback((auditEntry) => {
    if (dataHistoryRef.current.length === 0) return

    const previousData = dataHistoryRef.current.pop()
    setData(previousData)

    auditLog.logRevert(auditEntry.id)

    setSelectedColumn(null)
    setColumnAnalysis(null)
    setRecommendedRules([])
    setSelectedRule(null)
    setPreviewCache({})
  }, [auditLog])

  const handleAfterScrollVertically = useCallback(() => {
    const hotInstance = hotRef.current?.hotInstance
    if (!hotInstance) return

    const plugin = hotInstance.getPlugin('autoRowSize')
    if (plugin && plugin.getFirstVisibleRow) {
      const startRow = Math.max(0, plugin.getFirstVisibleRow() - 5)
      const endRow = Math.min(data.length - 2, plugin.getLastVisibleRow() + 5)
      setVisibleRange({ start: startRow, end: endRow })
    }
  }, [data.length])

  const handleExampleRule = useCallback((rule, config) => {
    setSelectedRule(rule)
    setRuleConfig(config)
    setPreviewCache({})
  }, [])

  const cellRenderer = useCallback((instance, td, row, col, prop, value, cellProperties) => {
    td.innerHTML = value !== undefined && value !== null ? value : ''
    
    if (showPreview && row > 0 && col === selectedColumn) {
      const dataRowIndex = row - 1
      const originalValue = data[row]?.[col]
      const previewValue = previewCache[dataRowIndex]
      if ((originalValue === '' || originalValue === undefined || originalValue === null) && previewValue !== undefined) {
        td.innerHTML = `<span style="color: #d97706; font-style: italic;">${previewValue}</span>`
        td.style.background = '#fef3c7'
      }
    }
    
    return td
  }, [showPreview, previewCache, selectedColumn, data])

  const loadSampleData = (type) => {
    let newData
    switch (type) {
      case 'sales':
        newData = [
          ['日期', '产品名称', '销量', '单价', '销售额', '区域', '销售员'],
          ['2024-01-01', '产品A', 100, 50, 5000, '华东', '李明'],
          ['2024-01-02', '产品B', 80, 75, 6000, '华北', '王芳'],
          ['2024-01-03', '产品A', 120, 50, 6000, '华南', '张伟'],
          ['2024-01-04', '产品C', 50, 100, 5000, '华东', '李明'],
          ['2024-01-05', '产品B', 90, 75, 6750, '华北', '王芳'],
          ['', '', '', '', '', '', ''],
          ['', '', '', '', '', '', ''],
          ['', '', '', '', '', '', '']
        ]
        break
      case 'inventory':
        newData = [
          ['SKU编码', '商品名称', '类别', '库存数量', '安全库存', '单价', '供应商'],
          ['SKU001', '笔记本电脑', '电子产品', 50, 20, 4999, '供应商A'],
          ['SKU002', '无线鼠标', '配件', 200, 50, 99, '供应商B'],
          ['SKU003', '机械键盘', '配件', 150, 30, 299, '供应商B'],
          ['SKU004', '显示器', '电子产品', 30, 10, 1299, '供应商A'],
          ['SKU005', '耳机', '配件', 180, 40, 199, '供应商C'],
          ['', '', '', '', '', '', ''],
          ['', '', '', '', '', '', '']
        ]
        break
      default:
        newData = sampleData
    }
    setData(newData)
    setSelectedColumn(null)
    setColumnAnalysis(null)
    setRecommendedRules([])
    setSelectedRule(null)
    setPreviewCache({})
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>📊 表格数据智能填充工具</h1>
        <p>AI学习建议 · 跨表关联填充 · 填充审计追踪 · 支持公式/序列/查表等多种填充方式</p>
      </header>
      
      <main className="app-main">
        <section className="table-section">
          <div className="section-header">
            <h2>数据表格</h2>
            <div className="toolbar">
              <button className="btn btn-default" onClick={() => loadSampleData('employee')}>
                员工数据
              </button>
              <button className="btn btn-default" onClick={() => loadSampleData('sales')}>
                销售数据
              </button>
              <button className="btn btn-default" onClick={() => loadSampleData('inventory')}>
                库存数据
              </button>
            </div>
          </div>
          
          <HotTable
            ref={hotRef}
            data={data}
            colHeaders={false}
            rowHeaders={true}
            height="calc(100vh - 220px)"
            licenseKey="non-commercial-and-evaluation"
            afterSelection={(row, col) => handleSelection(row, col)}
            afterScrollVertically={handleAfterScrollVertically}
            afterChange={(changes) => {
              if (changes) {
                const newData = [...data]
                changes.forEach(([row, col, _, newValue]) => {
                  newData[row][col] = newValue
                })
                setData(newData)
                if (selectedColumn !== null) {
                  analyzeColumn(selectedColumn)
                }
              }
            }}
            cells={(row, col) => {
              const cellProperties = {}
              if (row === 0) {
                cellProperties.renderer = (instance, td, ...args) => {
                  cellRenderer(instance, td, ...args)
                  td.style.fontWeight = 'bold'
                  td.style.background = '#f8fafc'
                }
              } else {
                cellProperties.renderer = cellRenderer
              }
              return cellProperties
            }}
          />
        </section>
        
        <Sidebar
          selectedColumn={selectedColumn}
          columnName={selectedColumn !== null ? data[0]?.[selectedColumn] : null}
          columnAnalysis={columnAnalysis}
          recommendedRules={recommendedRules}
          selectedRule={selectedRule}
          ruleConfig={ruleConfig}
          showPreview={showPreview}
          onRuleSelect={handleRuleSelect}
          onConfigChange={handleConfigChange}
          onTogglePreview={() => setShowPreview(!showPreview)}
          onApplyFill={applyFill}
          onBatchApply={batchApplyRules}
          onExampleRule={handleExampleRule}
          onRevert={handleRevert}
          data={data}
        />
      </main>
    </div>
  )
}

export default App
