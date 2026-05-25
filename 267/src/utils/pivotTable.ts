import type { DataRow, PivotConfig, PivotData } from '@/types/table'

type Aggregator = 'sum' | 'avg' | 'count' | 'min' | 'max'

const aggregators: Record<Aggregator, (values: number[]) => number> = {
  sum: (values) => values.reduce((a, b) => a + b, 0),
  avg: (values) => values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0,
  count: (values) => values.length,
  min: (values) => values.length > 0 ? Math.min(...values) : 0,
  max: (values) => values.length > 0 ? Math.max(...values) : 0,
}

export function generatePivotTable(
  data: DataRow[],
  config: PivotConfig
): PivotData {
  const { rows: rowFields, columns: colFields, values: valueConfigs } = config

  if (rowFields.length === 0 || valueConfigs.length === 0) {
    return {
      rowHeaders: [],
      colHeaders: [],
      values: [],
      grandTotalRow: [],
      grandTotalCol: [],
    }
  }

  const uniqueRowValues = getUniqueValues(data, rowFields)
  const uniqueColValues = colFields.length > 0 
    ? getUniqueValues(data, colFields)
    : [['Total']]

  const rowHeaders = uniqueRowValues.map(v => v.join(' - '))
  const colHeaders = uniqueColValues.map(v => v.join(' - '))

  const values: (number | string)[][] = []
  const grandTotalRow: (number | string)[] = []
  const grandTotalCol: (number | string)[] = []

  uniqueRowValues.forEach((rowCombo, rowIndex) => {
    const rowData: (number | string)[] = []
    let rowTotal = 0

    uniqueColValues.forEach((colCombo) => {
      const filtered = filterData(data, rowFields, rowCombo, colFields, colCombo)
      
      valueConfigs.forEach((valueConfig) => {
        const numericValues = filtered
          .map(d => Number(d[valueConfig.field as keyof DataRow]))
          .filter(v => !isNaN(v))
        
        const result = aggregators[valueConfig.aggregator](numericValues)
        rowData.push(Number(result.toFixed(2)))
        rowTotal += result
      })
    })

    values.push(rowData)
    grandTotalCol.push(Number(rowTotal.toFixed(2)))
  })

  const numValueCols = valueConfigs.length
  for (let i = 0; i < colHeaders.length * numValueCols; i++) {
    let colTotal = 0
    for (let j = 0; j < rowHeaders.length; j++) {
      colTotal += Number(values[j]?.[i] || 0)
    }
    grandTotalRow.push(Number(colTotal.toFixed(2)))
  }

  return {
    rowHeaders,
    colHeaders,
    values,
    grandTotalRow,
    grandTotalCol,
  }
}

function getUniqueValues(data: DataRow[], fields: string[]): string[][] {
  const valueSet = new Set<string>()

  data.forEach(row => {
    const key = fields.map(f => String(row[f as keyof DataRow] || '')).join('|||')
    valueSet.add(key)
  })

  return Array.from(valueSet)
    .sort()
    .map(key => key.split('|||'))
}

function filterData(
  data: DataRow[],
  rowFields: string[],
  rowValues: string[],
  colFields: string[],
  colValues: string[]
): DataRow[] {
  return data.filter(row => {
    const rowMatch = rowFields.every((field, i) => 
      String(row[field as keyof DataRow]) === rowValues[i]
    )
    
    if (colFields.length === 0 || colValues[0] === 'Total') {
      return rowMatch
    }

    const colMatch = colFields.every((field, i) => 
      String(row[field as keyof DataRow]) === colValues[i]
    )

    return rowMatch && colMatch
  })
}

export function getAvailableFields(): { key: keyof DataRow; label: string; type: 'string' | 'number' | 'date' }[] {
  return [
    { key: 'department', label: '部门', type: 'string' },
    { key: 'position', label: '职位', type: 'string' },
    { key: 'region', label: '地区', type: 'string' },
    { key: 'team', label: '团队', type: 'string' },
    { key: 'status', label: '状态', type: 'string' },
    { key: 'salary', label: '薪资', type: 'number' },
    { key: 'performance', label: '绩效', type: 'number' },
    { key: 'projects', label: '项目数', type: 'number' },
    { key: 'hireDate', label: '入职日期', type: 'date' },
  ]
}

export function getAggregatorLabel(aggregator: Aggregator): string {
  const labels: Record<Aggregator, string> = {
    sum: '求和',
    avg: '平均值',
    count: '计数',
    min: '最小值',
    max: '最大值',
  }
  return labels[aggregator]
}
