import chroma from 'chroma-js'

const COLOR_BLINDNESS_TYPES = {
  PROTANOPIA: 'protanopia',
  DEUTERANOPIA: 'deuteranopia',
  TRITANOPIA: 'tritanopia',
  ACHROMATOPSIA: 'achromatopsia',
  BLUE_YELLOW: 'blue_yellow',
  MONOCHROMACY: 'monochromacy'
}

const PROTANOPIA_MATRIX = [
  [0.56667, 0.43333, 0],
  [0.55833, 0.44167, 0],
  [0, 0.24167, 0.75833]
]

const PROTANOMALY_MATRIX = [
  [0.81667, 0.18333, 0],
  [0.33333, 0.66667, 0],
  [0, 0.125, 0.875]
]

const DEUTERANOPIA_MATRIX = [
  [0.625, 0.375, 0],
  [0.7, 0.3, 0],
  [0, 0.3, 0.7]
]

const DEUTERANOMALY_MATRIX = [
  [0.8, 0.2, 0],
  [0.25833, 0.74167, 0],
  [0, 0.14167, 0.85833]
]

const TRITANOPIA_MATRIX = [
  [0.95, 0.05, 0],
  [0, 0.43333, 0.56667],
  [0, 0.475, 0.525]
]

const TRITANOMALY_MATRIX = [
  [0.96667, 0.03333, 0],
  [0, 0.73333, 0.26667],
  [0, 0.18333, 0.81667]
]

const ACHROMATOPSIA_MATRIX = [
  [0.299, 0.587, 0.114],
  [0.299, 0.587, 0.114],
  [0.299, 0.587, 0.114]
]

const ACHROMATOMALY_MATRIX = [
  [0.618, 0.320, 0.062],
  [0.163, 0.775, 0.062],
  [0.163, 0.320, 0.516]
]

const BLUE_YELLOW_MATRIX = [
  [0.8, 0.2, 0],
  [0.333, 0.333, 0.334],
  [0, 0.125, 0.875]
]

const MONOCHROMACY_MATRIX = [
  [0.299, 0.587, 0.114],
  [0.299, 0.587, 0.114],
  [0.299, 0.587, 0.114]
]

function applyColorMatrix(color, matrix) {
  const [r, g, b] = chroma(color).rgb()
  const newR = r * matrix[0][0] + g * matrix[0][1] + b * matrix[0][2]
  const newG = r * matrix[1][0] + g * matrix[1][1] + b * matrix[1][2]
  const newB = r * matrix[2][0] + g * matrix[2][1] + b * matrix[2][2]
  return chroma.rgb(
    Math.min(255, Math.max(0, Math.round(newR))),
    Math.min(255, Math.max(0, Math.round(newG))),
    Math.min(255, Math.max(0, Math.round(newB)))
  ).hex()
}

export function simulateColorBlindness(color, type) {
  switch (type) {
    case COLOR_BLINDNESS_TYPES.PROTANOPIA:
      return applyColorMatrix(color, PROTANOPIA_MATRIX)
    case COLOR_BLINDNESS_TYPES.DEUTERANOPIA:
      return applyColorMatrix(color, DEUTERANOPIA_MATRIX)
    case COLOR_BLINDNESS_TYPES.TRITANOPIA:
      return applyColorMatrix(color, TRITANOPIA_MATRIX)
    case COLOR_BLINDNESS_TYPES.ACHROMATOPSIA:
      return applyColorMatrix(color, ACHROMATOPSIA_MATRIX)
    case COLOR_BLINDNESS_TYPES.BLUE_YELLOW:
      return applyColorMatrix(color, BLUE_YELLOW_MATRIX)
    case COLOR_BLINDNESS_TYPES.MONOCHROMACY:
      return applyColorMatrix(color, MONOCHROMACY_MATRIX)
    default:
      return color
  }
}

export function simulateColorBlindnessDetailed(color, type) {
  const results = { normal: color }
  switch (type) {
    case COLOR_BLINDNESS_TYPES.PROTANOPIA:
      results.anopia = simulateColorBlindness(color, COLOR_BLINDNESS_TYPES.PROTANOPIA)
      results.anomaly = applyColorMatrix(color, PROTANOMALY_MATRIX)
      break
    case COLOR_BLINDNESS_TYPES.DEUTERANOPIA:
      results.anopia = simulateColorBlindness(color, COLOR_BLINDNESS_TYPES.DEUTERANOPIA)
      results.anomaly = applyColorMatrix(color, DEUTERANOMALY_MATRIX)
      break
    case COLOR_BLINDNESS_TYPES.TRITANOPIA:
      results.anopia = simulateColorBlindness(color, COLOR_BLINDNESS_TYPES.TRITANOPIA)
      results.anomaly = applyColorMatrix(color, TRITANOMALY_MATRIX)
      break
    case COLOR_BLINDNESS_TYPES.ACHROMATOPSIA:
      results.anopia = simulateColorBlindness(color, COLOR_BLINDNESS_TYPES.ACHROMATOPSIA)
      results.anomaly = applyColorMatrix(color, ACHROMATOMALY_MATRIX)
      break
    case COLOR_BLINDNESS_TYPES.BLUE_YELLOW:
      results.anopia = simulateColorBlindness(color, COLOR_BLINDNESS_TYPES.BLUE_YELLOW)
      break
    case COLOR_BLINDNESS_TYPES.MONOCHROMACY:
      results.anopia = simulateColorBlindness(color, COLOR_BLINDNESS_TYPES.MONOCHROMACY)
      break
  }
  return results
}

export function checkColorAccessibility(color1, color2) {
  const c1 = chroma(color1)
  const c2 = chroma(color2)
  const contrast = chroma.contrast(c1, c2)

  return {
    contrast,
    wcagAA: contrast >= 4.5,
    wcagAAA: contrast >= 7,
    wcagAALarge: contrast >= 3,
    level: contrast >= 7 ? 'AAA' : contrast >= 4.5 ? 'AA' : contrast >= 3 ? 'AA Large' : 'Fail'
  }
}

export function checkPaletteColorBlindFriendly(colors) {
  const results = {
    isFriendly: true,
    overallScore: 100,
    passedTypes: [],
    failedTypes: [],
    protanopia: { colors: [], distinguishable: true, deltaEMin: 100, deltaEAvg: 0 },
    deuteranopia: { colors: [], distinguishable: true, deltaEMin: 100, deltaEAvg: 0 },
    tritanopia: { colors: [], distinguishable: true, deltaEMin: 100, deltaEAvg: 0 },
    achromatopsia: { colors: [], distinguishable: true, deltaEMin: 100, deltaEAvg: 0 },
    blue_yellow: { colors: [], distinguishable: true, deltaEMin: 100, deltaEAvg: 0 },
    monochromacy: { colors: [], distinguishable: true, deltaEMin: 100, deltaEAvg: 0 }
  }

  const allTypes = Object.values(COLOR_BLINDNESS_TYPES)
  let totalScore = 0
  let passedCount = 0

  allTypes.forEach(type => {
    const simulatedColors = colors.map(c => simulateColorBlindness(c, type))
    const { distinguishable, minDeltaE, avgDeltaE } = checkColorDistinguishabilityDetailed(simulatedColors)
    results[type] = {
      colors: simulatedColors,
      distinguishable,
      deltaEMin: minDeltaE,
      deltaEAvg: avgDeltaE
    }
    if (distinguishable) {
      passedCount++
      results.passedTypes.push(type)
    } else {
      results.failedTypes.push(type)
      results.isFriendly = false
    }
    totalScore += Math.min(100, (minDeltaE / 10) * 100)
  })

  results.overallScore = Math.round(totalScore / allTypes.length)
  return results
}

function checkColorDistinguishabilityDetailed(colors, threshold = 10) {
  let minDeltaE = Infinity
  let totalDeltaE = 0
  let pairCount = 0
  let distinguishable = true

  for (let i = 0; i < colors.length; i++) {
    for (let j = i + 1; j < colors.length; j++) {
      const c1 = chroma(colors[i])
      const c2 = chroma(colors[j])
      const deltaE = chroma.deltaE(c1, c2)
      minDeltaE = Math.min(minDeltaE, deltaE)
      totalDeltaE += deltaE
      pairCount++
      if (deltaE < threshold) {
        distinguishable = false
      }
    }
  }

  return {
    distinguishable,
    minDeltaE: pairCount > 0 ? Math.round(minDeltaE * 10) / 10 : 0,
    avgDeltaE: pairCount > 0 ? Math.round((totalDeltaE / pairCount) * 10) / 10 : 0
  }
}

function checkColorDistinguishability(colors, threshold = 0.1) {
  for (let i = 0; i < colors.length; i++) {
    for (let j = i + 1; j < colors.length; j++) {
      const c1 = chroma(colors[i])
      const c2 = chroma(colors[j])
      const deltaE = chroma.deltaE(c1, c2)
      if (deltaE < threshold * 100) {
        return false
      }
    }
  }
  return true
}

export function getColorBlindnessInfo() {
  return [
    {
      type: COLOR_BLINDNESS_TYPES.PROTANOPIA,
      name: '红色盲',
      shortName: '红色',
      description: '无法感知红色光（L锥体细胞缺失），红色与绿色难以区分',
      prevalence: '影响约1%的男性，0.02%的女性',
      severity: 'anopia',
      relatedAnomaly: 'protanomaly'
    },
    {
      type: COLOR_BLINDNESS_TYPES.DEUTERANOPIA,
      name: '绿色盲',
      shortName: '绿色',
      description: '无法感知绿色光（M锥体细胞缺失），是最常见的色盲类型',
      prevalence: '影响约4-5%的男性，0.3%的女性',
      severity: 'anopia',
      relatedAnomaly: 'deuteranomaly'
    },
    {
      type: COLOR_BLINDNESS_TYPES.TRITANOPIA,
      name: '蓝色盲',
      shortName: '蓝色',
      description: '无法感知蓝色光（S锥体细胞缺失），蓝黄色难以区分',
      prevalence: '非常罕见，约0.01%',
      severity: 'anopia',
      relatedAnomaly: 'tritanomaly'
    },
    {
      type: COLOR_BLINDNESS_TYPES.BLUE_YELLOW,
      name: '蓝黄色盲',
      shortName: '蓝黄',
      description: '蓝黄色觉异常，蓝色与黄色、紫色与红色难以区分',
      prevalence: '约0.02%，常为获得性色觉障碍',
      severity: 'mixed',
      relatedAnomaly: null
    },
    {
      type: COLOR_BLINDNESS_TYPES.ACHROMATOPSIA,
      name: '全色盲',
      shortName: '全色',
      description: '完全无法感知颜色，只能看到灰度，常伴随视力低下和畏光',
      prevalence: '极罕见，约0.003%',
      severity: 'total',
      relatedAnomaly: 'achromatomaly'
    },
    {
      type: COLOR_BLINDNESS_TYPES.MONOCHROMACY,
      name: '单色视觉',
      shortName: '单色',
      description: '视锥单色觉，只有一种视锥细胞工作，完全无法区分颜色',
      prevalence: '极罕见，约0.0001%',
      severity: 'total',
      relatedAnomaly: null
    }
  ]
}

export function getComprehensiveAssessment(colors) {
  const cbResult = checkPaletteColorBlindFriendly(colors)

  const contrastChecks = []
  for (let i = 0; i < colors.length; i++) {
    for (let j = i + 1; j < colors.length; j++) {
      const acc = checkColorAccessibility(colors[i], colors[j])
      contrastChecks.push({
        pair: `${colors[i]} vs ${colors[j]}`,
        contrast: acc.contrast,
        level: acc.level
      })
    }
  }

  const avgContrast = contrastChecks.length > 0
    ? contrastChecks.reduce((sum, c) => sum + c.contrast, 0) / contrastChecks.length
    : 0

  const luminanceValues = colors.map(c => chroma(c).luminance())
  const minLuminance = Math.min(...luminanceValues)
  const maxLuminance = Math.max(...luminanceValues)
  const luminanceRange = maxLuminance - minLuminance

  return {
    overallScore: cbResult.overallScore,
    isFriendly: cbResult.isFriendly,
    colorblindScore: cbResult.overallScore,
    contrastScore: Math.min(100, (avgContrast / 7) * 100),
    luminanceScore: Math.min(100, (luminanceRange / 0.5) * 100),
    passedTypes: cbResult.passedTypes,
    failedTypes: cbResult.failedTypes,
    avgContrast: Math.round(avgContrast * 100) / 100,
    luminanceRange: Math.round(luminanceRange * 1000) / 1000,
    recommendations: generateRecommendations(cbResult, avgContrast, luminanceRange)
  }
}

function generateRecommendations(cbResult, avgContrast, luminanceRange) {
  const recs = []

  if (!cbResult.isFriendly) {
    recs.push({
      type: 'warning',
      text: `此方案在 ${cbResult.failedTypes.length} 种色盲类型下可能难以区分颜色`
    })
  }

  if (cbResult.overallScore < 50) {
    recs.push({
      type: 'danger',
      text: '色觉友好度较低，建议选择色盲友好度更高的方案（如Set2、Paired、RdYlBu）'
    })
  }

  if (avgContrast < 3) {
    recs.push({
      type: 'warning',
      text: `平均对比度仅 ${avgContrast.toFixed(2)}，不满足WCAG AA标准（需≥4.5）`
    })
  }

  if (luminanceRange < 0.3) {
    recs.push({
      type: 'info',
      text: '亮度范围较小，在低亮度环境下可能难以区分'
    })
  }

  if (recs.length === 0) {
    recs.push({
      type: 'success',
      text: '此方案在各方面表现良好，适合广泛使用'
    })
  }

  return recs
}

export { COLOR_BLINDNESS_TYPES }
