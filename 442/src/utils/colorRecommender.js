import chroma from 'chroma-js'
import colorbrewer from 'colorbrewer'

export const CHART_TYPES = {
  BAR: 'bar',
  LINE: 'line',
  PIE: 'pie',
  SCATTER: 'scatter',
  AREA: 'area',
  HEATMAP: 'heatmap',
  RADAR: 'radar',
  SANKEY: 'sankey',
  TREEMAP: 'treemap'
}

export const DATA_FEATURES = {
  CATEGORICAL: 'categorical',
  SEQUENTIAL: 'sequential',
  DIVERGING: 'diverging',
  ORDINAL: 'ordinal',
  SKEWED_POSITIVE: 'skewed_positive',
  SKEWED_NEGATIVE: 'skewed_negative',
  OUTLIERS: 'outliers'
}

export const DATA_DISTRIBUTION = {
  SKEWED_POSITIVE: 'skewed_positive',
  SKEWED_NEGATIVE: 'skewed_negative',
  OUTLIERS: 'outliers',
  NORMAL: 'normal',
  UNIFORM: 'uniform'
}

const COLOR_SCHEME_TYPES = {
  QUALITATIVE: 'qualitative',
  SEQUENTIAL: 'sequential',
  DIVERGING: 'diverging'
}

const QUALITATIVE_SCHEMES = [
  'Set1', 'Set2', 'Set3', 'Accent', 'Dark2', 'Paired', 'Pastel1', 'Pastel2'
]

const SEQUENTIAL_SCHEMES = [
  'Blues', 'BuGn', 'BuPu', 'GnBu', 'Greens', 'Greys', 'Oranges', 'OrRd',
  'PuBu', 'PuBuGn', 'PuRd', 'Purples', 'RdPu', 'Reds', 'YlGn', 'YlGnBu',
  'YlOrBr', 'YlOrRd'
]

const DIVERGING_SCHEMES = [
  'BrBG', 'PiYG', 'PRGn', 'PuOr', 'RdBu', 'RdGy', 'RdYlBu', 'RdYlGn', 'Spectral'
]

function generateQualitativeColors(schemeName, count) {
  const scheme = colorbrewer[schemeName]
  if (!scheme) return null

  const maxColors = Math.max(...Object.keys(scheme).map(Number))
  const n = Math.min(count, maxColors)

  if (scheme[n]) {
    return scheme[n].slice(0, count)
  }

  if (scheme[maxColors]) {
    const baseColors = scheme[maxColors]
    if (count <= maxColors) {
      return baseColors.slice(0, count)
    }
    return chroma.scale(baseColors).colors(count)
  }

  return null
}

function generateSequentialColors(schemeName, count) {
  const scheme = colorbrewer[schemeName]
  if (!scheme) return null

  const keys = Object.keys(scheme).map(Number).sort((a, b) => a - b)
  const maxColors = keys[keys.length - 1]

  if (scheme[maxColors]) {
    return chroma.scale(scheme[maxColors]).mode('lab').colors(count)
  }

  return null
}

function generateDivergingColors(schemeName, count) {
  const scheme = colorbrewer[schemeName]
  if (!scheme) return null

  const keys = Object.keys(scheme).map(Number).sort((a, b) => a - b)
  const maxColors = keys[keys.length - 1]

  if (scheme[maxColors]) {
    return chroma.scale(scheme[maxColors]).mode('lab').colors(count)
  }

  return null
}

export function recommendColorSchemes(chartType, dataFeatures, categoryCount = 5, sampleData = null) {
  const recommendations = []
  const isCategorical = dataFeatures.includes(DATA_FEATURES.CATEGORICAL)
  const isSequential = dataFeatures.includes(DATA_FEATURES.SEQUENTIAL)
  const isDiverging = dataFeatures.includes(DATA_FEATURES.DIVERGING)
  const isOrdinal = dataFeatures.includes(DATA_FEATURES.ORDINAL)
  const hasSkewedPositive = dataFeatures.includes(DATA_FEATURES.SKEWED_POSITIVE)
  const hasSkewedNegative = dataFeatures.includes(DATA_FEATURES.SKEWED_NEGATIVE)
  const hasOutliers = dataFeatures.includes(DATA_FEATURES.OUTLIERS)

  let distributionAnalysis = null
  if (sampleData && Array.isArray(sampleData) && sampleData.length > 0) {
    distributionAnalysis = analyzeDataDistribution(sampleData)
  }

  if (isCategorical || [CHART_TYPES.PIE, CHART_TYPES.BAR, CHART_TYPES.RADAR].includes(chartType)) {
    QUALITATIVE_SCHEMES.forEach(schemeName => {
      const colors = generateQualitativeColors(schemeName, categoryCount)
      if (colors) {
        recommendations.push({
          name: schemeName,
          type: COLOR_SCHEME_TYPES.QUALITATIVE,
          typeLabel: '分类色',
          colors,
          score: calculateSchemeScore(
            schemeName, COLOR_SCHEME_TYPES.QUALITATIVE, chartType,
            dataFeatures, distributionAnalysis
          )
        })
      }
    })
  }

  if (isSequential || isOrdinal || [CHART_TYPES.LINE, CHART_TYPES.AREA, CHART_TYPES.HEATMAP].includes(chartType)) {
    SEQUENTIAL_SCHEMES.forEach(schemeName => {
      const colors = generateSequentialColors(schemeName, categoryCount)
      if (colors) {
        recommendations.push({
          name: schemeName,
          type: COLOR_SCHEME_TYPES.SEQUENTIAL,
          typeLabel: '顺序色',
          colors,
          score: calculateSchemeScore(
            schemeName, COLOR_SCHEME_TYPES.SEQUENTIAL, chartType,
            dataFeatures, distributionAnalysis
          )
        })
      }
    })
  }

  if (isDiverging) {
    DIVERGING_SCHEMES.forEach(schemeName => {
      const colors = generateDivergingColors(schemeName, categoryCount)
      if (colors) {
        recommendations.push({
          name: schemeName,
          type: COLOR_SCHEME_TYPES.DIVERGING,
          typeLabel: '发散色',
          colors,
          score: calculateSchemeScore(
            schemeName, COLOR_SCHEME_TYPES.DIVERGING, chartType,
            dataFeatures, distributionAnalysis
          )
        })
      }
    })
  }

  const sorted = recommendations.sort((a, b) => b.score - a.score)

  if (hasOutliers && distributionAnalysis) {
    const outlierSchemes = sorted.filter(s => ['Spectral', 'RdYlBu', 'RdBu', 'Set1', 'Paired'].includes(s.name))
    if (outlierSchemes.length > 0) {
      outlierSchemes.forEach(s => {
        s.reasonTags = s.reasonTags || []
        s.reasonTags.push('适合突出离群值')
      })
    }
  }

  if (hasSkewedPositive) {
    const skewedPositiveSchemes = sorted.filter(s => ['Reds', 'Oranges', 'YlOrRd', 'YlOrBr'].includes(s.name))
    skewedPositiveSchemes.forEach(s => {
      s.reasonTags = s.reasonTags || []
      s.reasonTags.push('适合右偏分布')
    })
  }

  if (hasSkewedNegative) {
    const skewedNegativeSchemes = sorted.filter(s => ['Blues', 'BuPu', 'PuBu', 'Purples'].includes(s.name))
    skewedNegativeSchemes.forEach(s => {
      s.reasonTags = s.reasonTags || []
      s.reasonTags.push('适合左偏分布')
    })
  }

  return sorted
}

function calculateSchemeScore(schemeName, schemeType, chartType, dataFeatures, distributionAnalysis) {
  let score = 50

  const preferredForCategorical = ['Set1', 'Set2', 'Set3', 'Paired']
  const preferredForSequential = ['Blues', 'Greens', 'Reds', 'Oranges', 'YlOrRd']
  const preferredForDiverging = ['RdBu', 'RdYlBu', 'Spectral', 'BrBG']

  if (schemeType === COLOR_SCHEME_TYPES.QUALITATIVE && preferredForCategorical.includes(schemeName)) {
    score += 30
  }
  if (schemeType === COLOR_SCHEME_TYPES.SEQUENTIAL && preferredForSequential.includes(schemeName)) {
    score += 30
  }
  if (schemeType === COLOR_SCHEME_TYPES.DIVERGING && preferredForDiverging.includes(schemeName)) {
    score += 30
  }

  if ([CHART_TYPES.PIE, CHART_TYPES.BAR].includes(chartType) && schemeType === COLOR_SCHEME_TYPES.QUALITATIVE) {
    score += 10
  }
  if ([CHART_TYPES.HEATMAP, CHART_TYPES.LINE].includes(chartType) && schemeType === COLOR_SCHEME_TYPES.SEQUENTIAL) {
    score += 10
  }

  const colorblindFriendly = ['Set2', 'Dark2', 'Paired', 'Blues', 'Greens', 'Reds', 'RdBu', 'RdYlBu']
  if (colorblindFriendly.includes(schemeName)) {
    score += 15
  }

  if (distributionAnalysis) {
    if (distributionAnalysis.hasOutliers && ['Spectral', 'RdYlBu', 'Set1', 'Paired'].includes(schemeName)) {
      score += 15
    }

    if (distributionAnalysis.skewness > 1.0 && ['Reds', 'Oranges', 'YlOrRd'].includes(schemeName)) {
      score += 15
    }
    if (distributionAnalysis.skewness < -1.0 && ['Blues', 'BuPu', 'Purples'].includes(schemeName)) {
      score += 15
    }

    if (distributionAnalysis.kurtosis > 3 && schemeType === COLOR_SCHEME_TYPES.DIVERGING) {
      score += 10
    }

    if (distributionAnalysis.variance < 100 && ['Pastel1', 'Pastel2'].includes(schemeName)) {
      score -= 10
    }
  }

  return Math.min(100, Math.max(0, score))
}

export function analyzeDataDistribution(data) {
  if (!data || data.length === 0) {
    return null
  }

  const values = data.filter(v => typeof v === 'number').sort((a, b) => a - b)
  if (values.length === 0) return null

  const n = values.length
  const mean = values.reduce((sum, v) => sum + v, 0) / n

  const median = n % 2 === 0
    ? (values[n / 2 - 1] + values[n / 2]) / 2
    : values[Math.floor(n / 2)]

  const variance = values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / n
  const stdDev = Math.sqrt(variance)

  const skewness = n > 2
    ? (n / ((n - 1) * (n - 2))) * values.reduce((sum, v) => sum + ((v - mean) / stdDev) ** 3, 0)
    : 0

  const kurtosis = n > 3
    ? ((n * (n + 1)) / ((n - 1) * (n - 2) * (n - 3))) * values.reduce((sum, v) => sum + ((v - mean) / stdDev) ** 4, 0)
      - (3 * (n - 1) ** 2) / ((n - 2) * (n - 3))
    : 0

  const q1 = values[Math.floor(n * 0.25)]
  const q3 = values[Math.floor(n * 0.75)]
  const iqr = q3 - q1

  const lowerFence = q1 - 1.5 * iqr
  const upperFence = q3 + 1.5 * iqr
  const outliers = values.filter(v => v < lowerFence || v > upperFence)

  const min = values[0]
  const max = values[n - 1]
  const range = max - min

  let distributionType = DATA_DISTRIBUTION.NORMAL
  if (skewness > 0.5) {
    distributionType = DATA_DISTRIBUTION.SKEWED_POSITIVE
  } else if (skewness < -0.5) {
    distributionType = DATA_DISTRIBUTION.SKEWED_NEGATIVE
  }
  if (range < stdDev * 2 && n > 10) {
    distributionType = DATA_DISTRIBUTION.UNIFORM
  }

  return {
    mean: Math.round(mean * 100) / 100,
    median: Math.round(median * 100) / 100,
    variance: Math.round(variance * 100) / 100,
    stdDev: Math.round(stdDev * 100) / 100,
    skewness: Math.round(skewness * 100) / 100,
    kurtosis: Math.round(kurtosis * 100) / 100,
    min,
    max,
    range,
    iqr: Math.round(iqr * 100) / 100,
    outlierCount: outliers.length,
    outlierValues: outliers.slice(0, 5),
    hasOutliers: outliers.length > 0,
    hasSkewedPositive: skewness > 0.5,
    hasSkewedNegative: skewness < -0.5,
    distributionType,
    sampleSize: n
  }
}

export function generateSampleData(chartType, categoryCount, distributionType) {
  const categories = ['类别A', '类别B', '类别C', '类别D', '类别E', '类别F', '类别G', '类别H', '类别I', '类别J', '类别K', '类别L']
  const selectedCategories = categories.slice(0, categoryCount)
  let values

  switch (distributionType) {
    case DATA_DISTRIBUTION.SKEWED_POSITIVE:
      values = selectedCategories.map((_, i) => {
        const base = Math.exp(i * 0.6) * 5 + Math.random() * 10
        return Math.round(base * 10) / 10
      })
      values[values.length - 1] = values[values.length - 2] + Math.random() * 50 + 20
      break

    case DATA_DISTRIBUTION.SKEWED_NEGATIVE:
      values = selectedCategories.map((_, i) => {
        const base = Math.exp((selectedCategories.length - 1 - i) * 0.6) * 5 + Math.random() * 10
        return Math.round(base * 10) / 10
      })
      values[0] = values[1] + Math.random() * 50 + 20
      break

    case DATA_DISTRIBUTION.OUTLIERS:
      values = selectedCategories.map(() => Math.random() * 40 + 30)
      const outlierIndex = Math.floor(Math.random() * selectedCategories.length)
      values[outlierIndex] = Math.random() * 50 + 90
      if (selectedCategories.length > 4) {
        values[(outlierIndex + 2) % selectedCategories.length] = Math.random() * 10 + 5
      }
      break

    case DATA_DISTRIBUTION.UNIFORM:
      values = selectedCategories.map(() => Math.random() * 20 + 50)
      break

    default:
      values = selectedCategories.map((_, i) => {
        const angle = (i / selectedCategories.length) * Math.PI * 2
        return Math.round((50 + Math.sin(angle) * 30 + Math.random() * 10) * 10) / 10
      })
  }

  return values
}

export function generateCustomPalette(baseColor, count, type = 'analogous') {
  switch (type) {
    case 'analogous':
      return chroma.scale([
        chroma(baseColor).set('hsl.h', chroma(baseColor).get('hsl.h') - 30),
        baseColor,
        chroma(baseColor).set('hsl.h', chroma(baseColor).get('hsl.h') + 30)
      ]).mode('hsl').colors(count)
    case 'complementary':
      return chroma.scale([
        baseColor,
        chroma(baseColor).set('hsl.h', chroma(baseColor).get('hsl.h') + 180)
      ]).mode('hsl').colors(count)
    case 'triadic':
      return chroma.scale([
        baseColor,
        chroma(baseColor).set('hsl.h', chroma(baseColor).get('hsl.h') + 120),
        chroma(baseColor).set('hsl.h', chroma(baseColor).get('hsl.h') + 240)
      ]).mode('hsl').colors(count)
    case 'monochromatic':
      return chroma.scale([
        chroma(baseColor).brighten(2),
        baseColor,
        chroma(baseColor).darken(2)
      ]).mode('lab').colors(count)
    default:
      return chroma.scale([baseColor]).colors(count)
  }
}

export function getColorInfo(color) {
  const c = chroma(color)
  return {
    hex: c.hex(),
    rgb: c.rgb(),
    hsl: c.hsl(),
    luminance: c.luminance(),
    saturation: c.get('hsl.s')
  }
}

export { COLOR_SCHEME_TYPES }
