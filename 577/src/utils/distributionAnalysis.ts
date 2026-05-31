import { type DistributionComparison } from '@/store/appStore'

function calculateNumericBins(values: number[], binCount: number = 8): string[] {
  if (values.length === 0) return []
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const step = range / binCount
  const bins: string[] = []

  for (let i = 0; i < binCount; i++) {
    const binMin = min + i * step
    const binMax = min + (i + 1) * step
    bins.push(`[${binMin.toFixed(1)}, ${binMax.toFixed(1)})`)
  }
  return bins
}

function binNumericData(values: number[], bins: string[]): Map<string, number> {
  const counts = new Map<string, number>()
  bins.forEach(bin => counts.set(bin, 0))

  if (values.length === 0) return counts

  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const step = range / bins.length

  for (const v of values) {
    let binIdx = Math.floor((v - min) / step)
    if (binIdx >= bins.length) binIdx = bins.length - 1
    if (binIdx < 0) binIdx = 0
    const bin = bins[binIdx]
    counts.set(bin, (counts.get(bin) || 0) + 1)
  }
  return counts
}

function binCategoricalData(values: string[]): Map<string, number> {
  const counts = new Map<string, number>()
  for (const v of values) {
    counts.set(v, (counts.get(v) || 0) + 1)
  }
  return new Map(
    [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
  )
}

function ecdf(values: number[]): Map<number, number> {
  const sorted = [...values].sort((a, b) => a - b)
  const result = new Map<number, number>()
  for (let i = 0; i < sorted.length; i++) {
    result.set(sorted[i], (i + 1) / sorted.length)
  }
  return result
}

function ksStatistic(overall: number[], sample: number[]): number {
  const ecdfOverall = ecdf(overall)
  const ecdfSample = ecdf(sample)
  const allPoints = new Set([...ecdfOverall.keys(), ...ecdfSample.keys()])
  let maxDiff = 0

  for (const x of allPoints) {
    const overallVal = ecdfOverall.get(x) ?? 0
    const sampleVal = ecdfSample.get(x) ?? 0
    maxDiff = Math.max(maxDiff, Math.abs(overallVal - sampleVal))
  }
  return maxDiff
}

function wassersteinDistance(overall: number[], sample: number[]): number {
  const sortedOverall = [...overall].sort((a, b) => a - b)
  const sortedSample = [...sample].sort((a, b) => a - b)
  const n = sortedOverall.length
  const m = sortedSample.length

  if (n === 0 || m === 0) return 0

  let distance = 0
  for (let i = 0; i < Math.max(n, m); i++) {
    const oIdx = Math.min(i, n - 1)
    const sIdx = Math.min(i, m - 1)
    distance += Math.abs(sortedOverall[oIdx] - sortedSample[sIdx])
  }
  return distance / Math.max(n, m)
}

export function compareDistribution(
  overallData: Record<string, unknown>[],
  sampleData: Record<string, unknown>[],
  columnName: string,
  columnType: string,
): DistributionComparison {
  if (columnType === 'number') {
    const overallValues = overallData
      .map(r => Number(r[columnName]))
      .filter(v => !isNaN(v) && isFinite(v))
    const sampleValues = sampleData
      .map(r => Number(r[columnName]))
      .filter(v => !isNaN(v) && isFinite(v))

    const bins = calculateNumericBins(overallValues, 8)
    const overallCounts = binNumericData(overallValues, bins)
    const sampleCounts = binNumericData(sampleValues, bins)

    const overallTotal = overallValues.length || 1
    const sampleTotal = sampleValues.length || 1

    const overallArr = bins.map(bin => ({
      bin,
      count: overallCounts.get(bin) || 0,
      ratio: (overallCounts.get(bin) || 0) / overallTotal,
    }))
    const sampleArr = bins.map(bin => ({
      bin,
      count: sampleCounts.get(bin) || 0,
      ratio: (sampleCounts.get(bin) || 0) / sampleTotal,
    }))

    return {
      column: columnName,
      overall: overallArr,
      sample: sampleArr,
      ksStatistic: ksStatistic(overallValues, sampleValues),
      wassersteinDistance: wassersteinDistance(overallValues, sampleValues),
    }
  }

  const overallValues = overallData.map(r => String(r[columnName] ?? 'null'))
  const sampleValues = sampleData.map(r => String(r[columnName] ?? 'null'))

  const overallCounts = binCategoricalData(overallValues)
  const categories = [...overallCounts.keys()]

  const overallTotal = overallValues.length || 1
  const sampleTotal = sampleValues.length || 1

  const sampleCountMap = new Map<string, number>()
  for (const v of sampleValues) {
    sampleCountMap.set(v, (sampleCountMap.get(v) || 0) + 1)
  }

  const overallArr = categories.map(cat => ({
    bin: cat.length > 15 ? cat.slice(0, 15) + '…' : cat,
    count: overallCounts.get(cat) || 0,
    ratio: (overallCounts.get(cat) || 0) / overallTotal,
  }))
  const sampleArr = categories.map(cat => ({
    bin: cat.length > 15 ? cat.slice(0, 15) + '…' : cat,
    count: sampleCountMap.get(cat) || 0,
    ratio: (sampleCountMap.get(cat) || 0) / sampleTotal,
  }))

  return {
    column: columnName,
    overall: overallArr,
    sample: sampleArr,
    ksStatistic: 0,
    wassersteinDistance: 0,
  }
}

export function findBestComparisonColumn(
  data: Record<string, unknown>[],
  columns: Array<{ name: string; type: string }>,
): { name: string; type: string } | null {
  const numericCols = columns.filter(c => c.type === 'number')
  if (numericCols.length > 0) {
    return numericCols[0]
  }
  const stringCols = columns.filter(c => c.type === 'string')
  if (stringCols.length > 0) {
    return stringCols[0]
  }
  return columns[0] || null
}
