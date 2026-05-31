export type SampleMethod = 'random' | 'stratified' | 'systematic'

export interface SampleConfig {
  method: SampleMethod
  ratio: number
  stratifyColumn?: string
  stepSize?: number
}

export interface SampleResult {
  indices: number[]
  sampleData: Record<string, unknown>[]
  stats: {
    sampleSize: number
    totalSize: number
    ratio: number
    distribution?: Record<string, number>
  }
}

function randomSample(data: Record<string, unknown>[], ratio: number): SampleResult {
  const totalSize = data.length
  const sampleSize = Math.max(1, Math.round(totalSize * ratio))
  const indices: number[] = []

  const pool = Array.from({ length: totalSize }, (_, i) => i)
  for (let i = pool.length - 1; i > 0 && indices.length < sampleSize; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]]
    indices.push(pool[i])
  }
  while (indices.length < sampleSize) {
    indices.push(pool[indices.length])
  }
  indices.sort((a, b) => a - b)

  return {
    indices,
    sampleData: indices.map(i => data[i]),
    stats: {
      sampleSize,
      totalSize,
      ratio,
    },
  }
}

function stratifiedSample(
  data: Record<string, unknown>[],
  ratio: number,
  column: string,
): SampleResult {
  const totalSize = data.length
  const groups = new Map<string, number[]>()

  data.forEach((row, idx) => {
    const key = String(row[column] ?? '__null__')
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(idx)
  })

  const indices: number[] = []
  const distribution: Record<string, number> = {}

  for (const [groupKey, groupIndices] of groups) {
    const groupSampleSize = Math.max(1, Math.round(groupIndices.length * ratio))
    const shuffled = [...groupIndices].sort(() => Math.random() - 0.5)
    const selected = shuffled.slice(0, groupSampleSize)
    indices.push(...selected)
    distribution[groupKey] = selected.length
  }

  indices.sort((a, b) => a - b)

  return {
    indices,
    sampleData: indices.map(i => data[i]),
    stats: {
      sampleSize: indices.length,
      totalSize,
      ratio,
      distribution,
    },
  }
}

function systematicSample(
  data: Record<string, unknown>[],
  ratio: number,
  stepSize?: number,
): SampleResult {
  const totalSize = data.length
  const sampleSize = Math.max(1, Math.round(totalSize * ratio))
  const step = stepSize ?? Math.max(1, Math.floor(totalSize / sampleSize))
  const startIndex = Math.floor(Math.random() * step)

  const indices: number[] = []
  for (let i = startIndex; i < totalSize && indices.length < sampleSize; i += step) {
    indices.push(i)
  }

  return {
    indices,
    sampleData: indices.map(i => data[i]),
    stats: {
      sampleSize: indices.length,
      totalSize,
      ratio,
    },
  }
}

export function executeSample(
  data: Record<string, unknown>[],
  config: SampleConfig,
): SampleResult {
  switch (config.method) {
    case 'random':
      return randomSample(data, config.ratio)
    case 'stratified':
      if (!config.stratifyColumn) throw new Error('Stratify column is required')
      return stratifiedSample(data, config.ratio, config.stratifyColumn)
    case 'systematic':
      return systematicSample(data, config.ratio, config.stepSize)
    default:
      throw new Error(`Unknown sample method: ${config.method}`)
  }
}
