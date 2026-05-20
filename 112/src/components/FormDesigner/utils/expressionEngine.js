export class ExpressionEngine {
  constructor() {
    this.cache = new Map()
  }

  parseExpression(expression) {
    if (!expression || typeof expression !== 'string') {
      return null
    }

    const regex = /\{\{([^}]+)\}\}/g
    const matches = []
    let match

    while ((match = regex.exec(expression)) !== null) {
      matches.push({
        full: match[0],
        expression: match[1].trim()
      })
    }

    return matches.length > 0 ? matches : null
  }

  evaluate(expression, context = {}) {
    try {
      const parsed = this.parseExpression(expression)
      
      if (!parsed) {
        return expression
      }

      let result = expression
      for (const match of parsed) {
        const value = this.evaluateSingle(match.expression, context)
        result = result.replace(match.full, String(value))
      }

      return result
    } catch (error) {
      console.error('表达式计算错误:', error)
      return `Error: ${error.message}`
    }
  }

  evaluateSingle(expr, context) {
    try {
      const safeContext = this.createSafeContext(context)
      const func = new Function(...Object.keys(safeContext), `return ${expr}`)
      return func(...Object.values(safeContext))
    } catch (error) {
      throw new Error(`"${expr}" 计算失败: ${error.message}`)
    }
  }

  evaluateCondition(condition, context = {}) {
    try {
      if (!condition) return true
      return Boolean(this.evaluateSingle(condition, context))
    } catch (error) {
      console.error('条件计算错误:', error)
      return false
    }
  }

  createSafeContext(context) {
    const safe = {
      formData: context.formData || {},
      ...context
    }

    Object.defineProperty(safe, 'window', { value: undefined })
    Object.defineProperty(safe, 'document', { value: undefined })
    Object.defineProperty(safe, 'eval', { value: undefined })
    Object.defineProperty(safe, 'Function', { value: undefined })

    return safe
  }

  extractDependencies(expression) {
    const parsed = this.parseExpression(expression)
    if (!parsed) return []

    const dependencies = new Set()
    for (const match of parsed) {
      const fieldMatches = match.expression.match(/formData\.([a-zA-Z_$][a-zA-Z0-9_$]*)/g)
      if (fieldMatches) {
        fieldMatches.forEach(m => {
          const fieldName = m.replace('formData.', '')
          dependencies.add(fieldName)
        })
      }
    }

    return Array.from(dependencies)
  }

  validateExpression(expression) {
    try {
      const testContext = { formData: {} }
      this.evaluate(expression, testContext)
      return { valid: true, error: null }
    } catch (error) {
      return { valid: false, error: error.message }
    }
  }

  clearCache() {
    this.cache.clear()
  }
}

export const expressionEngine = new ExpressionEngine()

export function createValidator(rule, formData, fieldName) {
  return (rule, value, callback) => {
    try {
      const context = { formData, value, fieldName }
      const result = expressionEngine.evaluateCondition(rule.condition, context)
      
      if (result) {
        callback()
      } else {
        callback(new Error(rule.message || '校验失败'))
      }
    } catch (error) {
      callback(new Error(`表达式错误: ${error.message}`))
    }
  }
}

export function generateExpressionPreview(expression, sampleData = {}) {
  const context = { formData: sampleData }
  try {
    return {
      result: expressionEngine.evaluate(expression, context),
      dependencies: expressionEngine.extractDependencies(expression),
      valid: true
    }
  } catch (error) {
    return {
      result: error.message,
      dependencies: expressionEngine.extractDependencies(expression),
      valid: false
    }
  }
}
