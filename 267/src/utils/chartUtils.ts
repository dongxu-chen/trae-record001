import type { DataRow, ChartConfig, ChartRecommendation, CellRange } from '@/types/table'

interface FieldInfo {
  key: string
  label: string
  type: 'string' | 'number' | 'date'
}

const fieldInfo: FieldInfo[] = [
  { key: 'id', label: 'ID', type: 'number' },
  { key: 'name', label: '姓名', type: 'string' },
  { key: 'email', label: '邮箱', type: 'string' },
  { key: 'department', label: '部门', type: 'string' },
  { key: 'position', label: '职位', type: 'string' },
  { key: 'salary', label: '薪资', type: 'number' },
  { key: 'hireDate', label: '入职日期', type: 'date' },
  { key: 'status', label: '状态', type: 'string' },
  { key: 'performance', label: '绩效', type: 'number' },
  { key: 'projects', label: '项目数', type: 'number' },
  { key: 'region', label: '地区', type: 'string' },
  { key: 'team', label: '团队', type: 'string' },
]

export function analyzeDataForChart(
  data: DataRow[],
  range?: CellRange,
  columns?: string[]
): ChartRecommendation[] {
  const recommendations: ChartRecommendation[] = []

  const numericFields = fieldInfo.filter(f => f.type === 'number' && f.key !== 'id')
  const categoryFields = fieldInfo.filter(f => f.type === 'string' && ['department', 'position', 'region', 'team', 'status'].includes(f.key))

  if (numericFields.length >= 1 && categoryFields.length >= 1) {
    const primaryNum = numericFields[0]
    const primaryCat = categoryFields[0]

    recommendations.push({
      type: 'bar',
      confidence: 0.9,
      reason: `分类数据对比最适合柱状图展示`,
      config: {
        type: 'bar',
        title: `${primaryCat.label} vs ${primaryNum.label}`,
        xField: primaryCat.key,
        yField: primaryNum.key,
      },
    })

    recommendations.push({
      type: 'pie',
      confidence: 0.75,
      reason: `占比分析适合饼图展示`,
      config: {
        type: 'pie',
        title: `${primaryCat.label}${primaryNum.label}占比`,
        xField: primaryCat.key,
        yField: primaryNum.key,
      },
    })
  }

  const dateFields = fieldInfo.filter(f => f.type === 'date')
  if (dateFields.length > 0 && numericFields.length > 0) {
    recommendations.push({
      type: 'line',
      confidence: 0.85,
      reason: `时间趋势分析适合折线图`,
      config: {
        type: 'line',
        title: `${dateFields[0].label}趋势`,
        xField: dateFields[0].key,
        yField: numericFields[0].key,
      },
    })
  }

  if (numericFields.length >= 2) {
    recommendations.push({
      type: 'scatter',
      confidence: 0.7,
      reason: `两个数值字段的相关性分析适合散点图`,
      config: {
        type: 'scatter',
        title: `${numericFields[0].label} vs ${numericFields[1].label}`,
        xField: numericFields[0].key,
        yField: numericFields[1].key,
      },
    })

    recommendations.push({
      type: 'area',
      confidence: 0.65,
      reason: `累积数据展示适合面积图`,
      config: {
        type: 'area',
        title: `${numericFields[0].label}面积图`,
        xField: categoryFields[0]?.key || 'department',
        yField: numericFields[0].key,
      },
    })
  }

  return recommendations.sort((a, b) => b.confidence - a.confidence)
}

export function prepareChartData(
  data: DataRow[],
  config: ChartConfig
): Record<string, unknown>[] {
  const { xField, yField, seriesField, type } = config

  if (type === 'pie') {
    const aggregated: Record<string, number> = {}
    data.forEach(row => {
      const key = String(row[xField as keyof DataRow])
      const value = Number(row[yField as keyof DataRow]) || 0
      aggregated[key] = (aggregated[key] || 0) + value
    })

    return Object.entries(aggregated).map(([name, value]) => ({
      name,
      value,
    }))
  }

  if (seriesField) {
    const grouped: Record<string, Record<string, unknown>> = {}
    data.forEach(row => {
      const xVal = String(row[xField as keyof DataRow])
      const sVal = String(row[seriesField as keyof DataRow])
      const yVal = Number(row[yField as keyof DataRow]) || 0

      if (!grouped[xVal]) {
        grouped[xVal] = { [xField]: xVal }
      }
      const current = Number(grouped[xVal][sVal] || 0)
      grouped[xVal][sVal] = current + yVal
    })

    return Object.values(grouped)
  }

  const aggregated: Record<string, number> = {}
  data.forEach(row => {
    const key = String(row[xField as keyof DataRow])
    const value = Number(row[yField as keyof DataRow]) || 0
    aggregated[key] = (aggregated[key] || 0) + value
  })

  return Object.entries(aggregated).map(([x, y]) => ({
    [xField]: x,
    [yField]: y,
  }))
}

export function getChartTypeLabel(type: ChartConfig['type']): string {
  const labels: Record<ChartConfig['type'], string> = {
    bar: '柱状图',
    line: '折线图',
    pie: '饼图',
    area: '面积图',
    scatter: '散点图',
  }
  return labels[type]
}

export function getFieldLabel(key: string): string {
  return fieldInfo.find(f => f.key === key)?.label || key
}
