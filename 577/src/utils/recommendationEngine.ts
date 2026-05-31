import { type AnalysisGoal, type SampleRecommendation, type SampleMethod, type ColumnMeta, type FileMeta } from '@/store/appStore'

export interface RecommendationInput {
  fileMeta: FileMeta
  analysisGoal: AnalysisGoal
  data?: Record<string, unknown>[]
}

const GOAL_METHOD_SCORES: Record<AnalysisGoal, Record<SampleMethod, number>> = {
  descriptive: { random: 0.9, stratified: 0.7, systematic: 0.5 },
  inferential: { random: 0.6, stratified: 0.95, systematic: 0.4 },
  exploratory: { random: 0.7, stratified: 0.6, systematic: 0.9 },
  classification: { random: 0.5, stratified: 0.95, systematic: 0.3 },
  regression: { random: 0.7, stratified: 0.6, systematic: 0.8 },
}

const GOAL_LABELS: Record<AnalysisGoal, string> = {
  descriptive: '描述统计',
  inferential: '推断统计',
  exploratory: '探索性分析',
  classification: '分类建模',
  regression: '回归建模',
}

const METHOD_LABELS: Record<SampleMethod, string> = {
  random: '随机抽样',
  stratified: '分层抽样',
  systematic: '系统抽样',
}

export function getGoalLabel(goal: AnalysisGoal): string {
  return GOAL_LABELS[goal]
}

export function getMethodLabel(method: SampleMethod): string {
  return METHOD_LABELS[method]
}

export function generateRecommendation(input: RecommendationInput): SampleRecommendation {
  const { fileMeta, analysisGoal, data } = input
  const scores: Record<SampleMethod, number> = { random: 0, stratified: 0, systematic: 0 }

  for (const method of Object.keys(scores) as SampleMethod[]) {
    scores[method] = GOAL_METHOD_SCORES[analysisGoal][method]
  }

  const stringCols = fileMeta.columns.filter(c => c.type === 'string')
  const numberCols = fileMeta.columns.filter(c => c.type === 'number')

  if (stringCols.length > 0) {
    scores.stratified += 0.1
    if (data && data.length > 0) {
      const catCounts = stringCols.map(col => {
        const unique = new Set(data.map(r => r[col.name])).size
        return { col, unique }
      })
      if (catCounts.some(c => c.unique > 2 && c.unique < 20)) {
        scores.stratified += 0.15
      }
    }
  }

  if (numberCols.length > 0) {
    scores.systematic += 0.05
  }

  if (fileMeta.totalRows < 1000) {
    scores.random += 0.1
  } else if (fileMeta.totalRows > 100000) {
    scores.systematic += 0.15
    scores.stratified += 0.1
  }

  const reasons: string[] = []
  const alternatives: Array<{ method: SampleMethod; reason: string }> = []
  const sorted = (Object.entries(scores) as [SampleMethod, number][]).sort((a, b) => b[1] - a[1])
  const recommendedMethod = sorted[0][0]

  reasons.push(`分析目标为「${GOAL_LABELS[analysisGoal]}」，${METHOD_LABELS[recommendedMethod]}最适合`)

  if (recommendedMethod === 'stratified') {
    if (stringCols.length > 0) {
      reasons.push(`数据包含 ${stringCols.length} 个分类字段，适合按字段分层以保证代表性`)
    }
    if (fileMeta.totalRows > 10000) {
      reasons.push('数据量较大，分层抽样可减少抽样误差')
    }
  } else if (recommendedMethod === 'systematic') {
    reasons.push('数据分布较均匀时，系统抽样高效且易于实现')
    if (fileMeta.totalRows > 100000) {
      reasons.push('大数据量下系统抽样性能最优')
    }
  } else {
    reasons.push('随机抽样无偏性最好，适合多数场景')
  }

  for (let i = 1; i < sorted.length; i++) {
    const [method, score] = sorted[i]
    let reason = ''
    if (method === 'random') reason = '作为基准方法，无偏性最好'
    if (method === 'stratified' && stringCols.length > 0) reason = `可按 ${stringCols[0].name} 等字段分层`
    if (method === 'systematic') reason = '执行效率最高，适合大数据'
    alternatives.push({ method, reason: `${reason} (匹配度 ${(score * 100).toFixed(0)}%)` })
  }

  return {
    recommendedMethod,
    confidence: Math.min(0.99, scores[recommendedMethod]),
    reasons,
    alternatives,
  }
}
