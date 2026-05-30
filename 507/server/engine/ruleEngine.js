class RuleEngine {
  constructor() {
    this.rules = this.initializeRules()
  }

  initializeRules() {
    return {
      sequence: {
        id: 'sequence',
        name: '序列填充',
        description: '自动识别数字序列并延续填充',
        category: 'sequence',
        dataTypes: ['number'],
        defaultConfig: {
          startValue: 1,
          step: 1,
          fillEmptyOnly: true
        },
        configFields: [
          { key: 'startValue', label: '起始值', type: 'number' },
          { key: 'step', label: '步长', type: 'number' },
          { key: 'fillEmptyOnly', label: '仅填充空值', type: 'boolean' }
        ]
      },
      date_sequence: {
        id: 'date_sequence',
        name: '日期序列',
        description: '按日/月/年递增填充日期',
        category: 'sequence',
        dataTypes: ['date'],
        defaultConfig: {
          interval: 1,
          unit: 'day',
          format: 'YYYY-MM-DD',
          fillEmptyOnly: true
        },
        configFields: [
          { key: 'interval', label: '间隔', type: 'number' },
          { key: 'unit', label: '单位', type: 'select', options: ['day', 'month', 'year'] },
          { key: 'format', label: '格式', type: 'text' },
          { key: 'fillEmptyOnly', label: '仅填充空值', type: 'boolean' }
        ]
      },
      copy_value: {
        id: 'copy_value',
        name: '复制填充',
        description: '使用上方值向下填充',
        category: 'basic',
        dataTypes: ['string', 'number', 'date', 'boolean'],
        defaultConfig: {
          fillEmptyOnly: true
        },
        configFields: [
          { key: 'fillEmptyOnly', label: '仅填充空值', type: 'boolean' }
        ]
      },
      formula: {
        id: 'formula',
        name: '公式计算',
        description: '使用公式计算填充值',
        category: 'calculation',
        dataTypes: ['number'],
        defaultConfig: {
          formula: 'A * B',
          columns: [],
          fillEmptyOnly: true
        },
        configFields: [
          { key: 'formula', label: '公式', type: 'textarea' },
          { key: 'fillEmptyOnly', label: '仅填充空值', type: 'boolean' }
        ]
      },
      lookup: {
        id: 'lookup',
        name: '查表填充',
        description: '根据映射表填充对应值',
        category: 'lookup',
        dataTypes: ['string', 'number'],
        defaultConfig: {
          mappings: [],
          fillEmptyOnly: true
        },
        configFields: [
          { key: 'mappings', label: '映射关系', type: 'mappings' },
          { key: 'fillEmptyOnly', label: '仅填充空值', type: 'boolean' }
        ]
      },
      category_cycle: {
        id: 'category_cycle',
        name: '分类循环',
        description: '循环使用已有分类值填充',
        category: 'category',
        dataTypes: ['string'],
        defaultConfig: {
          cycleValues: [],
          fillEmptyOnly: true
        },
        configFields: [
          { key: 'cycleValues', label: '循环值', type: 'text' },
          { key: 'fillEmptyOnly', label: '仅填充空值', type: 'boolean' }
        ]
      },
      constant: {
        id: 'constant',
        name: '固定值',
        description: '使用固定值填充',
        category: 'basic',
        dataTypes: ['string', 'number', 'date', 'boolean'],
        defaultConfig: {
          value: '',
          fillEmptyOnly: false
        },
        configFields: [
          { key: 'value', label: '填充值', type: 'text' },
          { key: 'fillEmptyOnly', label: '仅填充空值', type: 'boolean' }
        ]
      },
      random: {
        id: 'random',
        name: '随机填充',
        description: '在指定范围内随机生成值',
        category: 'advanced',
        dataTypes: ['number', 'string'],
        defaultConfig: {
          min: 0,
          max: 100,
          isInteger: true,
          fillEmptyOnly: true
        },
        configFields: [
          { key: 'min', label: '最小值', type: 'number' },
          { key: 'max', label: '最大值', type: 'number' },
          { key: 'isInteger', label: '整数', type: 'boolean' },
          { key: 'fillEmptyOnly', label: '仅填充空值', type: 'boolean' }
        ]
      }
    }
  }

  recommendRules(analysis) {
    const recommendations = []
    const { dataType, patterns, keywordMatch, stats } = analysis

    patterns.forEach(pattern => {
      if (pattern.type === 'arithmetic_sequence') {
        recommendations.push({
          ...this.rules.sequence,
          defaultConfig: {
            ...this.rules.sequence.defaultConfig,
            step: pattern.step
          },
          isRecommended: true,
          confidence: pattern.confidence
        })
      }
    })

    if (dataType === 'number') {
      if (keywordMatch?.includes('id') || keywordMatch?.includes('编号') || keywordMatch?.includes('序号')) {
        recommendations.push({
          ...this.rules.sequence,
          isRecommended: true,
          confidence: 0.9
        })
      }

      recommendations.push({
        ...this.rules.formula,
        isRecommended: false,
        confidence: 0.5
      })

      recommendations.push({
        ...this.rules.random,
        isRecommended: false,
        confidence: 0.3
      })
    }

    if (dataType === 'date') {
      recommendations.push({
        ...this.rules.date_sequence,
        isRecommended: true,
        confidence: 0.8
      })
    }

    if (dataType === 'string') {
      const categoryPattern = patterns.find(p => p.type === 'category_values')
      if (categoryPattern) {
        recommendations.push({
          ...this.rules.category_cycle,
          defaultConfig: {
            ...this.rules.category_cycle.defaultConfig,
            cycleValues: categoryPattern.values.join(', ')
          },
          isRecommended: true,
          confidence: categoryPattern.confidence
        })
      }

      const frequentPattern = patterns.find(p => p.type === 'frequent_values')
      if (frequentPattern && frequentPattern.values.length > 0) {
        recommendations.push({
          ...this.rules.constant,
          defaultConfig: {
            ...this.rules.constant.defaultConfig,
            value: frequentPattern.values[0].value
          },
          isRecommended: true,
          confidence: 0.6
        })
      }

      recommendations.push({
        ...this.rules.lookup,
        isRecommended: false,
        confidence: 0.4
      })
    }

    recommendations.push({
      ...this.rules.copy_value,
      isRecommended: false,
      confidence: 0.5
    })

    recommendations.push({
      ...this.rules.constant,
      isRecommended: false,
      confidence: 0.3
    })

    return recommendations
      .filter((rule, index, self) => 
        index === self.findIndex(r => r.id === rule.id)
      )
      .sort((a, b) => (b.isRecommended ? 1 : 0) - (a.isRecommended ? 1 : 0))
  }

  executeRule(rule, columnData, config, fullData, colIndex) {
    const { fillEmptyOnly = true } = config
    const result = []

    columnData.forEach((value, index) => {
      if (fillEmptyOnly && value !== '' && value !== null && value !== undefined) {
        result.push(value)
        return
      }

      let filledValue = this.applyRule(rule, config, index, columnData, fullData, colIndex, value)
      result.push(filledValue)
    })

    return result
  }

  applyRule(rule, config, index, columnData, fullData, colIndex, originalValue) {
    switch (rule.id) {
      case 'sequence':
        return this.applySequence(rule, config, index, columnData)

      case 'date_sequence':
        return this.applyDateSequence(rule, config, index, columnData)

      case 'copy_value':
        return this.applyCopyValue(index, columnData)

      case 'formula':
        return this.applyFormula(rule, config, index, fullData, colIndex)

      case 'lookup':
        return this.applyLookup(rule, config, index, columnData, fullData, colIndex)

      case 'category_cycle':
        return this.applyCategoryCycle(rule, config, index, columnData)

      case 'constant':
        return config.value

      case 'random':
        return this.applyRandom(rule, config)

      default:
        return originalValue
    }
  }

  applySequence(rule, config, index, columnData) {
    const { startValue = 1, step = 1 } = config
    
    let baseValue = startValue
    let lastFilledIndex = -1
    
    for (let i = 0; i < index; i++) {
      if (columnData[i] !== '' && columnData[i] !== null && columnData[i] !== undefined) {
        const num = Number(columnData[i])
        if (!isNaN(num)) {
          baseValue = num
          lastFilledIndex = i
        }
      }
    }

    if (lastFilledIndex >= 0) {
      const steps = index - lastFilledIndex
      return baseValue + (step * steps)
    }
    
    return baseValue + (step * index)
  }

  applyDateSequence(rule, config, index, columnData) {
    const { interval = 1, unit = 'day', format = 'YYYY-MM-DD' } = config
    
    let baseDate = null
    let lastFilledIndex = -1
    
    for (let i = 0; i < index; i++) {
      if (columnData[i] && columnData[i] !== '') {
        const date = new Date(columnData[i])
        if (!isNaN(date.getTime())) {
          baseDate = date
          lastFilledIndex = i
        }
      }
    }

    if (!baseDate) {
      baseDate = new Date()
    }

    const steps = lastFilledIndex >= 0 ? index - lastFilledIndex : index + 1
    const resultDate = new Date(baseDate)

    for (let i = 0; i < steps; i++) {
      switch (unit) {
        case 'day':
          resultDate.setDate(resultDate.getDate() + interval)
          break
        case 'month':
          resultDate.setMonth(resultDate.getMonth() + interval)
          break
        case 'year':
          resultDate.setFullYear(resultDate.getFullYear() + interval)
          break
      }
    }

    const year = resultDate.getFullYear()
    const month = String(resultDate.getMonth() + 1).padStart(2, '0')
    const day = String(resultDate.getDate()).padStart(2, '0')
    
    return format
      .replace('YYYY', year)
      .replace('MM', month)
      .replace('DD', day)
  }

  applyCopyValue(index, columnData) {
    for (let i = index - 1; i >= 0; i--) {
      if (columnData[i] !== '' && columnData[i] !== null && columnData[i] !== undefined) {
        return columnData[i]
      }
    }
    return ''
  }

  applyFormula(rule, config, index, fullData, colIndex) {
    const { formula = '' } = config
    const headers = fullData[0]
    const row = fullData[index + 1]

    if (!row) return ''

    let calculatedFormula = formula
    headers.forEach((header, hIndex) => {
      const colLetter = String.fromCharCode(65 + hIndex)
      const value = row[hIndex]
      const numValue = Number(value)
      calculatedFormula = calculatedFormula.replace(new RegExp(colLetter, 'g'), isNaN(numValue) ? 0 : numValue)
    })

    try {
      const sanitized = calculatedFormula.replace(/[^0-9+\-*/().\s]/g, '')
      const result = Function('"use strict"; return (' + sanitized + ')')()
      return isNaN(result) ? '' : result
    } catch (e) {
      return ''
    }
  }

  applyLookup(rule, config, index, columnData, fullData, colIndex) {
    const { mappings = [] } = config
    
    if (mappings.length === 0) {
      const uniqueValues = [...new Set(columnData.filter(v => v && v !== ''))]
      if (uniqueValues.length > 0) {
        return uniqueValues[index % uniqueValues.length]
      }
      return ''
    }

    const mappingIndex = index % mappings.length
    return mappings[mappingIndex] || ''
  }

  applyCategoryCycle(rule, config, index, columnData) {
    let { cycleValues = '' } = config
    
    if (!cycleValues) {
      const uniqueValues = [...new Set(columnData.filter(v => v && v !== ''))]
      cycleValues = uniqueValues.join(', ')
    }

    const values = cycleValues.split(/[,，]/).map(v => v.trim()).filter(v => v)
    if (values.length === 0) return ''
    
    return values[index % values.length]
  }

  applyRandom(rule, config) {
    const { min = 0, max = 100, isInteger = true } = config
    const range = max - min
    const random = Math.random() * range + min
    
    return isInteger ? Math.floor(random) : random
  }

  getAllRules() {
    return Object.values(this.rules)
  }

  getRuleById(id) {
    return this.rules[id]
  }
}

module.exports = new RuleEngine()
