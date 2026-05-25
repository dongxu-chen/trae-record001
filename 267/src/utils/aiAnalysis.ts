import type { DataRow, AIAnalysisResult } from '@/types/table'

interface QueryIntent {
  type: 'sum' | 'avg' | 'count' | 'min' | 'max' | 'compare' | 'trend' | 'list' | 'summary'
  targetField?: string
  groupBy?: string
  condition?: { field: string; operator: string; value: string }
  limit?: number
}

const fieldMapping: Record<string, string> = {
  '薪资': 'salary',
  '工资': 'salary',
  '薪水': 'salary',
  '绩效': 'performance',
  '项目': 'projects',
  '项目数': 'projects',
  '部门': 'department',
  '职位': 'position',
  '地区': 'region',
  '团队': 'team',
  '状态': 'status',
  '日期': 'hireDate',
  '入职日期': 'hireDate',
  '姓名': 'name',
  '邮箱': 'email',
}

const intentKeywords: Record<string, string[]> = {
  sum: ['总和', '总计', '合计', '总共有多少', '总共'],
  avg: ['平均', '均值', '平均值'],
  count: ['数量', '多少个', '几个人', '多少人', '统计'],
  min: ['最低', '最小', '最少'],
  max: ['最高', '最大', '最多'],
  compare: ['对比', '比较', '差异', '差别'],
  trend: ['趋势', '变化', '走势'],
  list: ['列出', '显示', '展示', '给我看'],
  summary: ['总结', '分析', '报告', '概况'],
}

export function analyzeQuery(query: string, data: DataRow[]): AIAnalysisResult {
  const intent = parseQueryIntent(query)
  const result = executeAnalysis(intent, data)

  return {
    query,
    result: formatResult(result, intent),
    data: result,
    chartType: suggestChartType(intent),
    confidence: calculateConfidence(query, intent),
  }
}

function parseQueryIntent(query: string): QueryIntent {
  let type: QueryIntent['type'] = 'summary'
  let targetField: string | undefined
  let groupBy: string | undefined

  for (const [intentType, keywords] of Object.entries(intentKeywords)) {
    if (keywords.some(kw => query.includes(kw))) {
      type = intentType as QueryIntent['type']
      break
    }
  }

  for (const [chineseName, fieldKey] of Object.entries(fieldMapping)) {
    if (query.includes(chineseName)) {
      if (!targetField) {
        targetField = fieldKey
      } else if (!groupBy) {
        groupBy = fieldKey
      }
    }
  }

  if (type === 'summary') {
    targetField = targetField || 'salary'
    groupBy = groupBy || 'department'
  }

  return { type, targetField, groupBy }
}

function executeAnalysis(intent: QueryIntent, data: DataRow[]): Record<string, unknown> {
  const { type, targetField, groupBy } = intent

  if (groupBy && targetField) {
    const grouped: Record<string, number[]> = {}
    data.forEach(row => {
      const key = String(row[groupBy as keyof DataRow])
      const value = Number(row[targetField as keyof DataRow]) || 0
      if (!grouped[key]) grouped[key] = []
      grouped[key].push(value)
    })

    const result: Record<string, unknown> = {}
    switch (type) {
      case 'sum':
        Object.entries(grouped).forEach(([k, v]) => { result[k] = v.reduce((a, b) => a + b, 0) })
        break
      case 'avg':
        Object.entries(grouped).forEach(([k, v]) => { result[k] = Number((v.reduce((a, b) => a + b, 0) / v.length).toFixed(2)) })
        break
      case 'count':
        Object.entries(grouped).forEach(([k, v]) => { result[k] = v.length })
        break
      case 'min':
        Object.entries(grouped).forEach(([k, v]) => { result[k] = Math.min(...v) })
        break
      case 'max':
        Object.entries(grouped).forEach(([k, v]) => { result[k] = Math.max(...v) })
        break
      default:
        Object.entries(grouped).forEach(([k, v]) => {
          result[k] = {
            count: v.length,
            sum: v.reduce((a, b) => a + b, 0),
            avg: Number((v.reduce((a, b) => a + b, 0) / v.length).toFixed(2)),
          }
        })
    }
    return result
  }

  const numericData = targetField
    ? data.map(d => Number(d[targetField as keyof DataRow])).filter(v => !isNaN(v))
    : []

  return {
    count: numericData.length,
    sum: numericData.reduce((a, b) => a + b, 0),
    avg: Number((numericData.reduce((a, b) => a + b, 0) / numericData.length).toFixed(2)),
    min: Math.min(...numericData),
    max: Math.max(...numericData),
  }
}

function formatResult(data: Record<string, unknown>, intent: QueryIntent): string {
  const lines: string[] = []
  const targetLabel = getFieldChineseName(intent.targetField)
  const groupLabel = getFieldChineseName(intent.groupBy)

  lines.push(`📊 分析结果：`)
  lines.push('')

  if (intent.groupBy) {
    lines.push(`按 ${groupLabel} 分组的${getIntentChineseName(intent.type)}：`)
    lines.push('')
    const sorted = Object.entries(data)
      .sort((a, b) => (Number(b[1]) || 0) - (Number(a[1]) || 0))

    sorted.forEach(([key, value], index) => {
      if (typeof value === 'object') {
        lines.push(`  ${index + 1}. ${key}:`)
        Object.entries(value as Record<string, unknown>).forEach(([k, v]) => {
          lines.push(`     ${getStatChineseName(k)}: ${formatNumber(v)}`)
        })
      } else {
        lines.push(`  ${index + 1}. ${key}: ${formatNumber(value)}`)
      }
    })
  } else {
    lines.push(`${targetLabel} 统计：`)
    lines.push('')
    Object.entries(data).forEach(([key, value]) => {
      lines.push(`  ${getStatChineseName(key)}: ${formatNumber(value)}`)
    })
  }

  return lines.join('\n')
}

function getFieldChineseName(field?: string): string {
  const reverse: Record<string, string> = {
    salary: '薪资',
    performance: '绩效',
    projects: '项目数',
    department: '部门',
    position: '职位',
    region: '地区',
    team: '团队',
    status: '状态',
    hireDate: '入职日期',
  }
  return reverse[field || ''] || field || '数据'
}

function getIntentChineseName(type: string): string {
  const names: Record<string, string> = {
    sum: '总和',
    avg: '平均值',
    count: '数量统计',
    min: '最小值',
    max: '最大值',
    summary: '综合统计',
  }
  return names[type] || '统计'
}

function getStatChineseName(stat: string): string {
  const names: Record<string, string> = {
    count: '数量',
    sum: '总和',
    avg: '平均值',
    min: '最小值',
    max: '最大值',
  }
  return names[stat] || stat
}

function formatNumber(value: unknown): string {
  if (typeof value === 'number') {
    return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
  }
  return String(value)
}

function suggestChartType(intent: QueryIntent): AIAnalysisResult['chartType'] {
  if (intent.groupBy) {
    return 'bar'
  }
  if (intent.type === 'trend') {
    return 'line'
  }
  return 'bar'
}

function calculateConfidence(query: string, intent: QueryIntent): number {
  let confidence = 0.5

  if (intent.targetField) confidence += 0.2
  if (intent.groupBy) confidence += 0.15
  if (intent.type !== 'summary') confidence += 0.1

  const keywords = Object.values(intentKeywords).flat()
  const matchCount = keywords.filter(kw => query.includes(kw)).length
  confidence += Math.min(matchCount * 0.05, 0.15)

  return Math.min(confidence, 1)
}

export function getSuggestedQueries(): string[] {
  return [
    '各部门薪资总和是多少？',
    '各职位的平均绩效',
    '每个团队有多少人？',
    '各地区薪资对比',
    '薪资最高的部门',
    '总结一下薪资情况',
  ]
}
