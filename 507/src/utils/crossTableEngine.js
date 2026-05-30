class CrossTableEngine {
  constructor() {
    this.referenceTables = {}
    this.loadFromStorage()
  }

  addReferenceTable(name, data, keyColumn, valueColumns) {
    if (!data || data.length < 2) return null

    const headers = data[0]
    const rows = data.slice(1)

    const keyColIndex = typeof keyColumn === 'number' ? keyColumn : headers.indexOf(keyColumn)
    if (keyColIndex === -1) return null

    const valueColIndices = valueColumns.map(vc => 
      typeof vc === 'number' ? vc : headers.indexOf(vc)
    ).filter(idx => idx !== -1)

    const lookupMap = {}
    rows.forEach(row => {
      const keyValue = String(row[keyColIndex] || '').trim()
      if (!keyValue) return

      if (!lookupMap[keyValue]) {
        lookupMap[keyValue] = {}
      }

      valueColIndices.forEach((colIdx, i) => {
        const colName = headers[colIdx] || `col_${colIdx}`
        lookupMap[keyValue][colName] = row[colIdx]
      })
    })

    const tableRecord = {
      name,
      headers,
      keyColumn: headers[keyColIndex],
      valueColumns: valueColIndices.map(i => headers[i]),
      keyColIndex,
      valueColIndices,
      lookupMap,
      rowCount: rows.length,
      createdAt: new Date().toISOString()
    }

    this.referenceTables[name] = tableRecord
    this.saveToStorage()
    return tableRecord
  }

  removeReferenceTable(name) {
    delete this.referenceTables[name]
    this.saveToStorage()
  }

  lookup(tableName, keyValue, valueColumnName) {
    const table = this.referenceTables[tableName]
    if (!table || !table.lookupMap) return undefined

    const entry = table.lookupMap[String(keyValue).trim()]
    if (!entry) return undefined

    if (valueColumnName) {
      return entry[valueColumnName]
    }

    return entry
  }

  lookupRow(tableName, keyValue) {
    return this.lookup(tableName, keyValue)
  }

  fillFromReference(tableName, sourceColumnData, valueColumnName) {
    const table = this.referenceTables[tableName]
    if (!table) return sourceColumnData.map(() => undefined)

    return sourceColumnData.map(value => {
      if (value === '' || value === null || value === undefined) return undefined
      return this.lookup(tableName, value, valueColumnName)
    })
  }

  getAvailableTables() {
    return Object.entries(this.referenceTables).map(([name, table]) => ({
      name,
      keyColumn: table.keyColumn,
      valueColumns: table.valueColumns,
      rowCount: table.rowCount,
      createdAt: table.createdAt
    }))
  }

  getTableDetail(name) {
    return this.referenceTables[name] || null
  }

  suggestMapping(currentHeaders, refTableName) {
    const table = this.referenceTables[refTableName]
    if (!table) return []

    const suggestions = []
    const refHeaders = table.headers

    currentHeaders.forEach((header, idx) => {
      const headerLower = header.toLowerCase()
      const matchIdx = refHeaders.findIndex(ref => 
        ref.toLowerCase() === headerLower ||
        this.computeSimilarity(headerLower, ref.toLowerCase()) > 0.6
      )

      if (matchIdx !== -1) {
        suggestions.push({
          currentColumn: header,
          currentIdx: idx,
          refColumn: refHeaders[matchIdx],
          refIdx: matchIdx,
          isKey: matchIdx === table.keyColIndex,
          confidence: this.computeSimilarity(headerLower, refHeaders[matchIdx].toLowerCase())
        })
      }
    })

    return suggestions.sort((a, b) => b.confidence - a.confidence)
  }

  computeSimilarity(a, b) {
    if (a === b) return 1
    if (!a || !b) return 0

    const synonyms = {
      '姓名': ['name', '名字', '人员', '员工姓名'],
      '部门': ['department', '部门名称', '科室', '组'],
      '编号': ['id', '序号', '代码', '编码'],
      '日期': ['date', '时间', '入职日期'],
      '工资': ['salary', '薪资', '薪水', '基本工资'],
      '价格': ['price', '单价', '售价'],
      '数量': ['count', 'qty', '库存', '库存数量']
    }

    for (const [key, syns] of Object.entries(synonyms)) {
      if (a === key || syns.includes(a)) {
        if (b === key || syns.includes(b)) return 0.85
      }
    }

    const setA = new Set(a.split(''))
    const setB = new Set(b.split(''))
    const intersection = new Set([...setA].filter(x => setB.has(x)))
    const union = new Set([...setA, ...setB])
    return intersection.size / union.size
  }

  saveToStorage() {
    try {
      const serializable = {}
      Object.entries(this.referenceTables).forEach(([name, table]) => {
        serializable[name] = {
          name: table.name,
          headers: table.headers,
          keyColumn: table.keyColumn,
          valueColumns: table.valueColumns,
          keyColIndex: table.keyColIndex,
          valueColIndices: table.valueColIndices,
          lookupMap: table.lookupMap,
          rowCount: table.rowCount,
          createdAt: table.createdAt
        }
      })
      localStorage.setItem('smartFill_referenceTables', JSON.stringify(serializable))
    } catch (e) {
      // storage unavailable
    }
  }

  loadFromStorage() {
    try {
      const stored = localStorage.getItem('smartFill_referenceTables')
      if (stored) {
        this.referenceTables = JSON.parse(stored)
      }
    } catch (e) {
      this.referenceTables = {}
    }
  }
}

export default CrossTableEngine
