class DataAnalyzer {
  constructor() {
    this.formatDetectors = [
      {
        type: 'email',
        label: '邮箱',
        test: (v) => /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(v),
        weight: 1.0
      },
      {
        type: 'phone_cn',
        label: '手机号',
        test: (v) => /^1[3-9]\d{9}$/.test(v),
        weight: 1.0
      },
      {
        type: 'url',
        label: 'URL',
        test: (v) => /^https?:\/\/[^\s]+/.test(v),
        weight: 1.0
      },
      {
        type: 'id_card_cn',
        label: '身份证号',
        test: (v) => /^\d{17}[\dXx]$/.test(v),
        weight: 1.0
      },
      {
        type: 'postal_code_cn',
        label: '邮编',
        test: (v) => /^\d{6}$/.test(v),
        weight: 0.9
      },
      {
        type: 'ip_address',
        label: 'IP地址',
        test: (v) => /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(v),
        weight: 0.95
      },
      {
        type: 'currency_cny',
        label: '人民币金额',
        test: (v) => /^[¥￥]?\d{1,3}(,\d{3})*(\.\d{1,2})?$|^[¥￥]?\d+(\.\d{1,2})?$/.test(v),
        weight: 0.95
      },
      {
        type: 'percentage',
        label: '百分比',
        test: (v) => /^-?\d+(\.\d+)?%$/.test(v),
        weight: 1.0
      },
      {
        type: 'date_iso',
        label: '日期(ISO)',
        test: (v) => /^\d{4}-\d{2}-\d{2}$/.test(v),
        weight: 1.0
      },
      {
        type: 'date_slash',
        label: '日期(斜杠)',
        test: (v) => /^\d{4}\/\d{2}\/\d{2}$/.test(v),
        weight: 1.0
      },
      {
        type: 'date_cn',
        label: '日期(中文)',
        test: (v) => /^\d{4}年\d{1,2}月\d{1,2}日$/.test(v),
        weight: 1.0
      },
      {
        type: 'time_hms',
        label: '时间',
        test: (v) => /^\d{1,2}:\d{2}(:\d{2})?$/.test(v),
        weight: 1.0
      },
      {
        type: 'sku_code',
        label: 'SKU编码',
        test: (v) => /^[A-Za-z]{2,4}\d{3,}$/.test(v),
        weight: 0.85
      },
      {
        type: 'boolean_cn',
        label: '布尔值(中文)',
        test: (v) => ['是', '否', '有', '无', '对', '错', '真', '假'].includes(v.toLowerCase()),
        weight: 1.0
      },
      {
        type: 'boolean_en',
        label: '布尔值(英文)',
        test: (v) => ['true', 'false', 'yes', 'no'].includes(v.toLowerCase()),
        weight: 1.0
      }
    ]

    this.datePatterns = [
      /^\d{4}-\d{2}-\d{2}$/,
      /^\d{4}\/\d{2}\/\d{2}$/,
      /^\d{2}-\d{2}-\d{4}$/,
      /^\d{2}\/\d{2}\/\d{4}$/,
      /^\d{4}年\d{1,2}月\d{1,2}日$/
    ]
  }

  analyzeColumn(columnData, columnName) {
    const nonEmptyValues = columnData.filter(v => v !== '' && v !== null && v !== undefined)
    const totalCount = columnData.length
    const nonEmptyCount = nonEmptyValues.length
    const emptyCount = totalCount - nonEmptyCount

    if (nonEmptyCount === 0) {
      return {
        columnName,
        dataType: 'unknown',
        confidence: 0,
        typeCandidates: [],
        stats: { totalCount, nonEmptyCount, emptyCount },
        patterns: []
      }
    }

    const typeCandidates = this.analyzeAllTypeCandidates(nonEmptyValues)
    const patterns = this.detectPatterns(nonEmptyValues, typeCandidates[0]?.type || 'string')
    const keywordAnalysis = this.analyzeByKeyword(columnName, typeCandidates)

    const mergedCandidates = this.mergeKeywordIntoCandidates(keywordAnalysis, typeCandidates)

    return {
      columnName,
      dataType: mergedCandidates[0]?.type || 'string',
      confidence: mergedCandidates[0]?.confidence || 0,
      typeCandidates: mergedCandidates,
      stats: {
        totalCount,
        nonEmptyCount,
        emptyCount,
        uniqueCount: new Set(nonEmptyValues.map(v => String(v))).size,
        ...this.computeTypeStats(nonEmptyValues, mergedCandidates[0]?.type || 'string')
      },
      patterns,
      sampleValues: nonEmptyValues.slice(0, 5),
      keywordMatch: keywordAnalysis.matched
    }
  }

  analyzeAllTypeCandidates(values) {
    const candidateScores = {}
    const candidateLabels = {}

    this.formatDetectors.forEach(detector => {
      let matchCount = 0
      values.forEach(v => {
        if (detector.test(String(v).trim())) matchCount++
      })
      if (matchCount > 0) {
        const rawConf = matchCount / values.length
        candidateScores[detector.type] = rawConf * detector.weight
        candidateLabels[detector.type] = detector.label
      }
    })

    let numberCount = 0
    let numberStats = { min: Infinity, max: -Infinity, sum: 0, decimals: 0 }
    let dateCount = 0
    let stringCount = 0
    let booleanCount = 0

    values.forEach((value) => {
      const strValue = String(value).trim()
      const numValue = Number(value)

      const isSpecialFormat = this.formatDetectors
        .filter(d => d.type.startsWith('date') || d.type === 'percentage' || d.type === 'currency_cny')
        .some(d => d.test(strValue))
      if (!isNaN(numValue) && strValue !== '' && !isSpecialFormat) {
        numberCount++
        numberStats.min = Math.min(numberStats.min, numValue)
        numberStats.max = Math.max(numberStats.max, numValue)
        numberStats.sum += numValue
        if (strValue.includes('.')) numberStats.decimals++
      }

      if (this.datePatterns.some(p => p.test(strValue)) || (!isNaN(Date.parse(strValue)) && isNaN(numValue))) {
        dateCount++
      }

      if (typeof value === 'boolean' || ['true', 'false', '是', '否', '有', '无'].includes(strValue.toLowerCase())) {
        booleanCount++
      }

      if (isNaN(numValue)) {
        stringCount++
      }
    })

    const total = values.length

    if (numberCount > 0 && !candidateScores.number) {
      candidateScores.number = numberCount / total
      candidateLabels.number = '数字'
    }
    if (dateCount > 0 && !candidateScores.date) {
      candidateScores.date = dateCount / total
      candidateLabels.date = '日期'
    }
    if (stringCount > 0 && !candidateScores.string) {
      candidateScores.string = stringCount / total
      candidateLabels.string = '文本'
    }
    if (booleanCount > 0 && !candidateScores.boolean) {
      candidateScores.boolean = booleanCount / total
      candidateLabels.boolean = '布尔值'
    }

    if (numberStats.min !== Infinity) {
      candidateScores._numberStats = numberStats
    }

    const candidates = Object.entries(candidateScores)
      .filter(([key]) => !key.startsWith('_'))
      .map(([type, confidence]) => ({
        type,
        label: candidateLabels[type] || type,
        confidence: Math.round(confidence * 100) / 100
      }))
      .sort((a, b) => b.confidence - a.confidence)

    return candidates
  }

  mergeKeywordIntoCandidates(keywordAnalysis, existingCandidates) {
    const result = [...existingCandidates]

    if (keywordAnalysis.matched && keywordAnalysis.dataType) {
      const existing = result.find(c => c.type === keywordAnalysis.dataType)
      if (existing) {
        existing.confidence = Math.min(1, existing.confidence + 0.15)
        existing.source = 'data+keyword'
      } else {
        result.push({
          type: keywordAnalysis.dataType,
          label: keywordAnalysis.label || keywordAnalysis.dataType,
          confidence: keywordAnalysis.confidence,
          source: 'keyword'
        })
      }
    }

    return result.sort((a, b) => b.confidence - a.confidence)
  }

  computeTypeStats(values, dataType) {
    const stats = {}

    if (dataType === 'number') {
      const numValues = values.map(v => Number(v)).filter(v => !isNaN(v))
      if (numValues.length > 0) {
        stats.min = Math.min(...numValues)
        stats.max = Math.max(...numValues)
        stats.avg = numValues.reduce((a, b) => a + b, 0) / numValues.length
        stats.hasDecimal = numValues.some(v => !Number.isInteger(v))
      }
    }

    if (dataType === 'date' || dataType.startsWith('date')) {
      const dates = values
        .map(v => new Date(v))
        .filter(d => !isNaN(d.getTime()))
        .sort((a, b) => a - b)
      if (dates.length > 0) {
        stats.minDate = dates[0].toISOString()
        stats.maxDate = dates[dates.length - 1].toISOString()
      }
    }

    return stats
  }

  detectPatterns(values, dataType) {
    const patterns = []

    if (dataType === 'number') {
      const numValues = values.map(v => Number(v)).filter(v => !isNaN(v))
      if (numValues.length >= 2) {
        const diffs = []
        for (let i = 1; i < numValues.length; i++) {
          diffs.push(numValues[i] - numValues[i - 1])
        }
        const uniqueDiffs = [...new Set(diffs)]
        if (uniqueDiffs.length === 1 && uniqueDiffs[0] !== 0) {
          patterns.push({
            type: 'arithmetic_sequence',
            name: '等差数列',
            step: uniqueDiffs[0],
            confidence: 1
          })
        }

        const ratios = []
        for (let i = 1; i < numValues.length; i++) {
          if (numValues[i - 1] !== 0) {
            ratios.push(numValues[i] / numValues[i - 1])
          }
        }
        const uniqueRatios = [...new Set(ratios.map(r => Number(r.toFixed(4))))]
        if (uniqueRatios.length === 1 && uniqueRatios[0] !== 1) {
          patterns.push({
            type: 'geometric_sequence',
            name: '等比数列',
            ratio: uniqueRatios[0],
            confidence: 1
          })
        }
      }
    }

    if (values.length >= 2) {
      const valueCounts = {}
      values.forEach(v => {
        const key = String(v)
        valueCounts[key] = (valueCounts[key] || 0) + 1
      })
      const frequentValues = Object.entries(valueCounts)
        .filter(([_, count]) => count > 1)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([value, count]) => ({ value, count }))

      if (frequentValues.length > 0) {
        patterns.push({
          type: 'frequent_values',
          name: '高频值',
          values: frequentValues,
          confidence: frequentValues.length / Object.keys(valueCounts).length
        })
      }
    }

    const uniqueValues = [...new Set(values.map(v => String(v)))]
    if (uniqueValues.length <= Math.min(values.length * 0.3, 10) && uniqueValues.length > 1) {
      patterns.push({
        type: 'category_values',
        name: '分类值',
        values: uniqueValues,
        confidence: 1 - (uniqueValues.length / values.length)
      })
    }

    return patterns
  }

  analyzeByKeyword(columnName, typeCandidates) {
    const keywordMap = {
      'id|编号|序号|序': { dataType: 'number', label: '序号', patterns: ['sequence'] },
      'name|姓名|名称|名字': { dataType: 'string', label: '姓名', patterns: [] },
      'date|日期|时间|入职': { dataType: 'date', label: '日期', patterns: [] },
      '部门|部门名称|科室': { dataType: 'string', label: '部门', patterns: ['category'] },
      'salary|工资|薪资|金额|价格|费用|成本': { dataType: 'number', label: '金额', patterns: ['calculation'] },
      'score|评分|分数|评级': { dataType: 'number', label: '评分', patterns: ['range'] },
      'status|状态|是否|转正': { dataType: 'boolean', label: '状态', patterns: [] },
      'type|类型|类别|分类': { dataType: 'string', label: '分类', patterns: ['category'] },
      '数量|count|qty|库存': { dataType: 'number', label: '数量', patterns: [] },
      '地址|address|住址': { dataType: 'string', label: '地址', patterns: [] },
      '电话|phone|mobile|手机': { dataType: 'phone_cn', label: '手机号', patterns: ['format'] },
      '邮箱|email|邮件': { dataType: 'email', label: '邮箱', patterns: ['format'] },
      'sku|编码|代号': { dataType: 'sku_code', label: 'SKU编码', patterns: [] }
    }

    const nameLower = columnName.toLowerCase()
    let matched = null
    let dataType = null
    let confidence = 0
    let label = null

    Object.entries(keywordMap).forEach(([pattern, config]) => {
      if (new RegExp(pattern).test(nameLower)) {
        matched = pattern
        dataType = config.dataType
        confidence = 0.9
        label = config.label
      }
    })

    return { matched, dataType, confidence, label }
  }

  analyzeAllColumns(data) {
    const headers = data[0]
    const results = []

    headers.forEach((header, index) => {
      const columnData = data.slice(1).map(row => row[index])
      results.push(this.analyzeColumn(columnData, header))
    })

    return results
  }
}

export default DataAnalyzer
