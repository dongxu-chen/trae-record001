class ExampleParser {
  constructor() {
    this.patterns = this.initializePatterns()
  }

  initializePatterns() {
    return [
      {
        name: '等差数列',
        detect: (values) => {
          const nums = values.map(Number).filter(n => !isNaN(n))
          if (nums.length < 2) return null
          const diffs = []
          for (let i = 1; i < nums.length; i++) {
            diffs.push(nums[i] - nums[i - 1])
          }
          if (new Set(diffs).size === 1 && diffs[0] !== 0) {
            return {
              ruleId: 'sequence',
              config: { startValue: nums[0], step: diffs[0], fillEmptyOnly: true },
              description: `从${nums[0]}开始，每次加${diffs[0]}`
            }
          }
          return null
        },
        examples: ['1, 2, 3, 4, 5', '10, 20, 30, 40', '100, 95, 90, 85']
      },
      {
        name: '日期递增',
        detect: (values) => {
          const dates = values.map(v => new Date(v)).filter(d => !isNaN(d.getTime()))
          if (dates.length < 2) return null
          const diffs = []
          for (let i = 1; i < dates.length; i++) {
            diffs.push(dates[i] - dates[i - 1])
          }
          const dayMs = 86400000
          const uniqueDayDiffs = [...new Set(diffs.map(d => Math.round(d / dayMs)))]
          if (uniqueDayDiffs.length === 1 && uniqueDayDiffs[0] > 0) {
            const interval = uniqueDayDiffs[0]
            const unit = interval % 365 === 0 ? 'year' : interval % 30 === 0 ? 'month' : 'day'
            const actualInterval = unit === 'year' ? interval / 365 : unit === 'month' ? interval / 30 : interval
            return {
              ruleId: 'date_sequence',
              config: { interval: actualInterval, unit, format: 'YYYY-MM-DD', fillEmptyOnly: true },
              description: `从${values[0]}开始，每${unit === 'day' ? '天' : unit === 'month' ? '月' : '年'}加${actualInterval}`
            }
          }
          return null
        },
        examples: ['2024-01-01, 2024-01-02, 2024-01-03', '2024-01, 2024-02, 2024-03']
      },
      {
        name: '分类循环',
        detect: (values) => {
          const strValues = values.map(String)
          const uniqueValues = [...new Set(strValues)]
          if (uniqueValues.length < values.length && uniqueValues.length >= 2 && uniqueValues.length <= 20) {
            return {
              ruleId: 'category_cycle',
              config: { cycleValues: uniqueValues.join(', '), fillEmptyOnly: true },
              description: `循环填充: ${uniqueValues.join(' → ')}`
            }
          }
          if (uniqueValues.length === values.length && uniqueValues.length >= 2 && uniqueValues.length <= 10) {
            return {
              ruleId: 'category_cycle',
              config: { cycleValues: uniqueValues.join(', '), fillEmptyOnly: true },
              description: `依次填充: ${uniqueValues.join(' → ')}`
            }
          }
          return null
        },
        examples: ['技术部, 产品部, 市场部', '甲, 乙, 丙, 丁', 'A, B, C, D']
      },
      {
        name: '固定值',
        detect: (values) => {
          const uniqueValues = [...new Set(values.map(String))]
          if (uniqueValues.length === 1) {
            return {
              ruleId: 'constant',
              config: { value: uniqueValues[0], fillEmptyOnly: true },
              description: `全部填入「${uniqueValues[0]}」`
            }
          }
          return null
        },
        examples: ['技术部, 技术部, 技术部', '0, 0, 0']
      },
      {
        name: '布尔值交替',
        detect: (values) => {
          const strValues = values.map(v => String(v).toLowerCase())
          const boolPairs = [['true', 'false'], ['是', '否'], ['有', '无'], ['对', '错']]
          for (const [a, b] of boolPairs) {
            if (strValues.every(v => v === a || v === b)) {
              const unique = [...new Set(strValues)]
              if (unique.length === 2) {
                return {
                  ruleId: 'category_cycle',
                  config: { cycleValues: unique.join(', '), fillEmptyOnly: true },
                  description: `交替填入「${unique[0]}」和「${unique[1]}」`
                }
              }
            }
          }
          return null
        },
        examples: ['是, 否, 是, 否', 'true, false, true']
      },
      {
        name: '等比数列',
        detect: (values) => {
          const nums = values.map(Number).filter(n => !isNaN(n) && n !== 0)
          if (nums.length < 2) return null
          const ratios = []
          for (let i = 1; i < nums.length; i++) {
            if (nums[i - 1] !== 0) {
              ratios.push(nums[i] / nums[i - 1])
            }
          }
          const uniqueRatios = [...new Set(ratios.map(r => Number(r.toFixed(4))))]
          if (uniqueRatios.length === 1 && uniqueRatios[0] !== 1) {
            return {
              ruleId: 'sequence',
              config: {
                startValue: nums[0],
                step: 0,
                fillEmptyOnly: true,
                _geometric: true,
                _ratio: uniqueRatios[0],
                _customApply: (index, columnData) => {
                  let lastVal = nums[0]
                  let lastIdx = 0
                  for (let i = 0; i < index; i++) {
                    if (columnData[i] !== '' && columnData[i] !== null) {
                      const n = Number(columnData[i])
                      if (!isNaN(n) && n !== 0) { lastVal = n; lastIdx = i }
                    }
                  }
                  const steps = index - lastIdx
                  return lastVal * Math.pow(uniqueRatios[0], steps)
                }
              },
              description: `从${nums[0]}开始，每次乘以${uniqueRatios[0]}`
            }
          }
          return null
        },
        examples: ['2, 4, 8, 16', '1, 3, 9, 27', '100, 50, 25, 12.5']
      },
      {
        name: '编号前缀序列',
        detect: (values) => {
          const strValues = values.map(String)
          const prefixMatch = strValues[0]?.match(/^([A-Za-z\u4e00-\u9fa5]+)(\d+)$/)
          if (!prefixMatch) return null
          const prefix = prefixMatch[1]
          const nums = []
          for (const v of strValues) {
            const m = v.match(new RegExp(`^${prefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\d+)$`))
            if (m) nums.push(Number(m[1]))
            else return null
          }
          if (nums.length >= 2) {
            const diffs = []
            for (let i = 1; i < nums.length; i++) diffs.push(nums[i] - nums[i - 1])
            if (new Set(diffs).size === 1) {
              return {
                ruleId: 'constant',
                config: {
                  value: '',
                  fillEmptyOnly: true,
                  _prefix: prefix,
                  _startNum: nums[0],
                  _step: diffs[0],
                  _digitLen: prefixMatch[2].length,
                  _customApply: (index, columnData) => {
                    const p = prefix
                    let lastNum = nums[0]
                    let lastIdx = 0
                    for (let i = 0; i < index; i++) {
                      if (columnData[i] !== '' && columnData[i] !== null) {
                        const m2 = String(columnData[i]).match(new RegExp(`${p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\d+)$`))
                        if (m2) { lastNum = Number(m2[1]); lastIdx = i }
                      }
                    }
                    const nextNum = lastNum + diffs[0] * (index - lastIdx)
                    return p + String(nextNum).padStart(prefixMatch[2].length, '0')
                  }
                },
                description: `从${values[0]}开始，编号每次加${diffs[0]}`
              }
            }
          }
          return null
        },
        examples: ['SKU001, SKU002, SKU003', 'NO001, NO002, NO003']
      }
    ]
  }

  parseExample(input) {
    const trimmed = input.trim()
    if (!trimmed) return []

    let values
    if (trimmed.includes('，') || trimmed.includes('、')) {
      values = trimmed.split(/[，、]/).map(v => v.trim()).filter(v => v)
    } else if (trimmed.includes(',')) {
      values = trimmed.split(',').map(v => v.trim()).filter(v => v)
    } else if (trimmed.includes(' ')) {
      values = trimmed.split(/\s+/).map(v => v.trim()).filter(v => v)
    } else if (trimmed.includes('\n')) {
      values = trimmed.split('\n').map(v => v.trim()).filter(v => v)
    } else {
      values = [trimmed]
    }

    const results = []
    for (const pattern of this.patterns) {
      try {
        const match = pattern.detect(values)
        if (match) {
          results.push({
            ...match,
            patternName: pattern.name,
            exampleValues: values,
            confidence: this.calculateConfidence(values, match)
          })
        }
      } catch (e) {
        continue
      }
    }

    return results.sort((a, b) => b.confidence - a.confidence)
  }

  calculateConfidence(values, match) {
    let confidence = 0.5

    if (values.length >= 3) confidence += 0.2
    if (values.length >= 5) confidence += 0.1
    if (match.description) confidence += 0.1
    if (match.config._customApply) confidence -= 0.05

    return Math.min(1, confidence)
  }

  getExampleHints() {
    return this.patterns.map(p => ({
      name: p.name,
      examples: p.examples
    }))
  }

  generateNaturalLanguage(ruleId, config) {
    switch (ruleId) {
      case 'sequence': {
        const { startValue = 1, step = 1 } = config
        if (step > 0) return `从 ${startValue} 开始，每次加 ${step}`
        if (step < 0) return `从 ${startValue} 开始，每次减 ${Math.abs(step)}`
        return `全部填入 ${startValue}`
      }
      case 'date_sequence': {
        const { interval = 1, unit = 'day' } = config
        const unitLabel = { day: '天', month: '个月', year: '年' }[unit] || '天'
        return `日期每次加 ${interval} ${unitLabel}`
      }
      case 'formula': {
        const { formula = '' } = config
        return `公式: ${formula}`
      }
      case 'category_cycle': {
        const { cycleValues = '' } = config
        return `循环填入: ${cycleValues}`
      }
      case 'copy_value':
        return '复制上一个非空值'
      case 'constant': {
        if (config._prefix) {
          return config.description || `编号序列: ${config._prefix}+数字`
        }
        const { value = '' } = config
        return `固定填入「${value}」`
      }
      case 'lookup':
        return '根据映射表查表填充'
      case 'random': {
        const { min = 0, max = 100 } = config
        return `随机填入 ${min}~${max} 之间的数`
      }
      default:
        return '未知规则'
    }
  }
}

export default ExampleParser
