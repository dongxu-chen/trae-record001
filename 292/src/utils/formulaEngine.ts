import type { FormSchema } from '@/types/form'

export interface FunctionDef {
  name: string
  minArgs: number
  maxArgs: number
  description: string
  example: string
}

export const functionDefinitions: FunctionDef[] = [
  {
    name: 'SUM',
    minArgs: 1,
    maxArgs: Infinity,
    description: '求和函数，返回所有参数的和',
    example: 'SUM(field_a, field_b, 10)'
  },
  {
    name: 'AVG',
    minArgs: 1,
    maxArgs: Infinity,
    description: '平均值函数，返回所有参数的平均值',
    example: 'AVG(field_a, field_b, field_c)'
  },
  {
    name: 'MAX',
    minArgs: 1,
    maxArgs: Infinity,
    description: '最大值函数，返回所有参数中的最大值',
    example: 'MAX(field_a, field_b, 100)'
  },
  {
    name: 'MIN',
    minArgs: 1,
    maxArgs: Infinity,
    description: '最小值函数，返回所有参数中的最小值',
    example: 'MIN(field_a, field_b, 0)'
  },
  {
    name: 'IF',
    minArgs: 3,
    maxArgs: 3,
    description: '条件判断函数，IF(条件, 真值, 假值)',
    example: 'IF(field_a > 10, field_b * 2, field_b)'
  },
  {
    name: 'ROUND',
    minArgs: 1,
    maxArgs: 2,
    description: '四舍五入函数，可指定小数位数',
    example: 'ROUND(field_a, 2)'
  },
  {
    name: 'ABS',
    minArgs: 1,
    maxArgs: 1,
    description: '绝对值函数',
    example: 'ABS(field_a)'
  },
  {
    name: 'FLOOR',
    minArgs: 1,
    maxArgs: 1,
    description: '向下取整函数',
    example: 'FLOOR(field_a)'
  },
  {
    name: 'CEIL',
    minArgs: 1,
    maxArgs: 1,
    description: '向上取整函数',
    example: 'CEIL(field_a)'
  },
  {
    name: 'POW',
    minArgs: 2,
    maxArgs: 2,
    description: '幂函数，POW(底数, 指数)',
    example: 'POW(field_a, 2)'
  },
  {
    name: 'SQRT',
    minArgs: 1,
    maxArgs: 1,
    description: '平方根函数',
    example: 'SQRT(field_a)'
  },
  {
    name: 'LEN',
    minArgs: 1,
    maxArgs: 1,
    description: '字符串长度函数',
    example: 'LEN(field_a)'
  },
  {
    name: 'CONCAT',
    minArgs: 2,
    maxArgs: Infinity,
    description: '字符串拼接函数',
    example: 'CONCAT(field_a, "-", field_b)'
  },
  {
    name: 'LEFT',
    minArgs: 2,
    maxArgs: 2,
    description: '从左侧截取字符串',
    example: 'LEFT(field_a, 5)'
  },
  {
    name: 'RIGHT',
    minArgs: 2,
    maxArgs: 2,
    description: '从右侧截取字符串',
    example: 'RIGHT(field_a, 3)'
  },
  {
    name: 'MID',
    minArgs: 3,
    maxArgs: 3,
    description: '截取子字符串，MID(字符串, 起始位置, 长度)',
    example: 'MID(field_a, 2, 5)'
  },
  {
    name: 'LOWER',
    minArgs: 1,
    maxArgs: 1,
    description: '转换为小写',
    example: 'LOWER(field_a)'
  },
  {
    name: 'UPPER',
    minArgs: 1,
    maxArgs: 1,
    description: '转换为大写',
    example: 'UPPER(field_a)'
  },
  {
    name: 'TRIM',
    minArgs: 1,
    maxArgs: 1,
    description: '去除首尾空白字符',
    example: 'TRIM(field_a)'
  },
  {
    name: 'AND',
    minArgs: 2,
    maxArgs: Infinity,
    description: '逻辑与运算',
    example: 'AND(field_a > 0, field_b < 100)'
  },
  {
    name: 'OR',
    minArgs: 2,
    maxArgs: Infinity,
    description: '逻辑或运算',
    example: 'OR(field_a == "yes", field_b == true)'
  },
  {
    name: 'NOT',
    minArgs: 1,
    maxArgs: 1,
    description: '逻辑非运算',
    example: 'NOT(field_a)'
  },
  {
    name: 'TODAY',
    minArgs: 0,
    maxArgs: 0,
    description: '返回当前日期',
    example: 'TODAY()'
  },
  {
    name: 'YEAR',
    minArgs: 1,
    maxArgs: 1,
    description: '提取日期的年份',
    example: 'YEAR(field_a)'
  },
  {
    name: 'MONTH',
    minArgs: 1,
    maxArgs: 1,
    description: '提取日期的月份',
    example: 'MONTH(field_a)'
  },
  {
    name: 'DAY',
    minArgs: 1,
    maxArgs: 1,
    description: '提取日期的日',
    example: 'DAY(field_a)'
  }
]

const functionLibrary: Record<string, (...args: any[]) => any> = {
  SUM: (...args: any[]) => args.reduce((sum, val) => sum + (Number(val) || 0), 0),
  AVG: (...args: any[]) => {
    const nums = args.map(v => Number(v) || 0)
    return nums.length > 0 ? nums.reduce((a, b) => a + b, 0) / nums.length : 0
  },
  MAX: (...args: any[]) => Math.max(...args.map(v => Number(v) || -Infinity)),
  MIN: (...args: any[]) => Math.min(...args.map(v => Number(v) || Infinity)),
  IF: (condition: any, trueVal: any, falseVal: any) => condition ? trueVal : falseVal,
  ROUND: (num: any, decimals = 0) => {
    const n = Number(num) || 0
    const d = Math.pow(10, decimals)
    return Math.round(n * d) / d
  },
  ABS: (num: any) => Math.abs(Number(num) || 0),
  FLOOR: (num: any) => Math.floor(Number(num) || 0),
  CEIL: (num: any) => Math.ceil(Number(num) || 0),
  POW: (base: any, exponent: any) => Math.pow(Number(base) || 0, Number(exponent) || 0),
  SQRT: (num: any) => Math.sqrt(Number(num) || 0),
  LEN: (str: any) => String(str || '').length,
  CONCAT: (...args: any[]) => args.map(v => v ?? '').join(''),
  LEFT: (str: any, length: any) => String(str || '').slice(0, Number(length) || 0),
  RIGHT: (str: any, length: any) => String(str || '').slice(-(Number(length) || 0)),
  MID: (str: any, start: any, length: any) => String(str || '').slice(Number(start) || 0, (Number(start) || 0) + (Number(length) || 0)),
  LOWER: (str: any) => String(str || '').toLowerCase(),
  UPPER: (str: any) => String(str || '').toUpperCase(),
  TRIM: (str: any) => String(str || '').trim(),
  AND: (...args: any[]) => args.every(v => Boolean(v)),
  OR: (...args: any[]) => args.some(v => Boolean(v)),
  NOT: (val: any) => !Boolean(val),
  TODAY: () => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  },
  YEAR: (dateStr: any) => {
    const d = new Date(String(dateStr || ''))
    return isNaN(d.getTime()) ? null : d.getFullYear()
  },
  MONTH: (dateStr: any) => {
    const d = new Date(String(dateStr || ''))
    return isNaN(d.getTime()) ? null : d.getMonth() + 1
  },
  DAY: (dateStr: any) => {
    const d = new Date(String(dateStr || ''))
    return isNaN(d.getTime()) ? null : d.getDate()
  }
}

export function evaluateExpression(
  expression: string,
  formData: Record<string, any>,
  schema: FormSchema
): { result: any; error: string | null } {
  try {
    let expr = expression.trim()
    
    if (!expr) {
      return { result: null, error: null }
    }

    const fieldNameMap: Record<string, string> = {}
    schema.tabs.forEach(tab => {
      tab.fields.forEach(field => {
        fieldNameMap[field.name] = field.name
      })
    })

    const usedFields: Set<string> = new Set()
    const sortedNames = Object.keys(fieldNameMap).sort((a, b) => b.length - a.length)
    sortedNames.forEach(name => {
      const regex = new RegExp(`\\b${name}\\b`, 'g')
      if (regex.test(expr)) {
        usedFields.add(name)
      }
    })

    sortedNames.forEach(name => {
      const regex = new RegExp(`\\b${name}\\b`, 'g')
      const value = formData[name]
      const safeValue = typeof value === 'string' ? JSON.stringify(value) : (value ?? 0)
      expr = expr.replace(regex, String(safeValue))
    })

    Object.keys(functionLibrary).forEach(funcName => {
      const regex = new RegExp(`\\b${funcName}\\(`, 'gi')
      expr = expr.replace(regex, `__FUNC_${funcName.toUpperCase()}(`)
    })

    const context: Record<string, any> = {}
    Object.keys(functionLibrary).forEach(funcName => {
      context[`__FUNC_${funcName}`] = functionLibrary[funcName]
    })

    const paramNames = Object.keys(context).join(', ')
    const funcBody = `"use strict"; return (${expr})`
    const evaluator = new Function(paramNames, funcBody)
    const result = evaluator(...Object.values(context))

    return { result, error: null }
  } catch (error) {
    return { 
      result: null, 
      error: error instanceof Error ? error.message : '公式计算错误' 
    }
  }
}

export function extractFormulaDependencies(expression: string, schema: FormSchema): string[] {
  const dependencies: Set<string> = new Set()
  const fieldNames = new Set<string>()
  
  schema.tabs.forEach(tab => {
    tab.fields.forEach(field => {
      fieldNames.add(field.name)
    })
  })

  const sortedNames = Array.from(fieldNames).sort((a, b) => b.length - a.length)
  sortedNames.forEach(name => {
    const regex = new RegExp(`\\b${name}\\b`, 'g')
    if (regex.test(expression)) {
      dependencies.add(name)
    }
  })

  return Array.from(dependencies)
}

export function getFunctionHelp(funcName: string): FunctionDef | undefined {
  return functionDefinitions.find(f => f.name.toLowerCase() === funcName.toLowerCase())
}
