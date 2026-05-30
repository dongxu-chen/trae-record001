class DataAnalyzer {
  constructor() {
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
        stats: { totalCount, nonEmptyCount, emptyCount },
        patterns: []
      }
    }

    const typeAnalysis = this.analyzeDataType(nonEmptyValues)
    const patterns = this.detectPatterns(nonEmptyValues, typeAnalysis.dataType)
    const keywordAnalysis = this.analyzeByKeyword(columnName, typeAnalysis)

    return {
      columnName,
      dataType: keywordAnalysis.dataType || typeAnalysis.dataType,
      confidence: Math.max(typeAnalysis.confidence, keywordAnalysis.confidence),
      stats: {
        totalCount,
        nonEmptyCount,
        emptyCount,
        uniqueCount: new Set(nonEmptyValues.map(v => String(v))).size,
        ...typeAnalysis.stats
      },
      patterns,
      sampleValues: nonEmptyValues.slice(0, 5),
      keywordMatch: keywordAnalysis.matched
    }
  }

  analyzeDataType(values) {
    const typeScores = {
      number: 0,
      date: 0,
      boolean: 0,
      string: 0
    }

    let numberStats = { min: Infinity, max: -Infinity, sum: 0, decimals: 0 }
    let dateValues = []

    values.forEach((value) => {
      const strValue = String(value).trim()
      const numValue = Number(value)

      if (!isNaN(numValue) && strValue !== '') {
        typeScores.number++
        numberStats.min = Math.min(numberStats.min, numValue)
        numberStats.max = Math.max(numberStats.max, numValue)
        numberStats.sum += numValue
        if (strValue.includes('.')) {
          numberStats.decimals++
        }
      }

      if (this.datePatterns.some(pattern => pattern.test(strValue)) || !isNaN(Date.parse(strValue))) {
        typeScores.date++
        dateValues.push(new Date(strValue))
      }

      if (typeof value === 'boolean' || ['true', 'false', '是', '否', '有', '无'].includes(strValue.toLowerCase())) {
        typeScores.boolean++
      }

      if (isNaN(numValue) && !this.datePatterns.some(pattern => pattern.test(strValue))) {
        typeScores.string++
      }
    })

    const total = values.length
    let dataType = 'string'
    let confidence = 0

    Object.entries(typeScores).forEach(([type, score]) => {
      const conf = score / total
      if (conf > confidence) {
        confidence = conf
        dataType = type
      }
    })

    const result = {
      dataType,
      confidence
    }

    if (dataType === 'number') {
      result.stats = {
        min: numberStats.min,
        max: numberStats.max,
        avg: numberStats.sum / values.length,
        hasDecimal: numberStats.decimals > 0
      }
    }

    if (dataType === 'date' && dateValues.length > 0) {
      const sortedDates = dateValues.sort((a, b) => a - b)
      result.stats = {
        minDate: sortedDates[0].toISOString(),
        maxDate: sortedDates[sortedDates.length - 1].toISOString()
      }
    }

    return result
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

  analyzeByKeyword(columnName, typeAnalysis) {
    const keywordMap = {
      'id|编号|序号': { dataType: 'number', patterns: ['sequence'] },
      'name|姓名|名称': { dataType: 'string', patterns: [] },
      'date|日期|时间': { dataType: 'date', patterns: [] },
      '部门|部门名称': { dataType: 'string', patterns: ['category'] },
      'salary|工资|薪资|金额|价格': { dataType: 'number', patterns: ['calculation'] },
      'score|评分|分数': { dataType: 'number', patterns: ['range'] },
      'status|状态|是否': { dataType: 'boolean', patterns: [] },
      'type|类型|类别': { dataType: 'string', patterns: ['category'] },
      '数量|count|qty': { dataType: 'number', patterns: [] },
      '地址|address': { dataType: 'string', patterns: [] },
      '电话|phone|mobile': { dataType: 'string', patterns: ['format'] },
      '邮箱|email': { dataType: 'string', patterns: ['format'] }
    }

    const nameLower = columnName.toLowerCase()
    let matched = null
    let dataType = null
    let confidence = 0

    Object.entries(keywordMap).forEach(([pattern, config]) => {
      if (new RegExp(pattern).test(nameLower)) {
        matched = pattern
        dataType = config.dataType
        confidence = 0.9
      }
    })

    return { matched, dataType, confidence }
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

module.exports = new DataAnalyzer()
