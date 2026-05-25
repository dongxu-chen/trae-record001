import { functionDefinitions, evaluateExpression, extractFormulaDependencies } from './formulaEngine'
import { checkDependencies, validateFieldDependencies } from './dependencyChecker'
import { compressSchema, decompressSchema } from './schemaCompressor'
import type { FormSchema } from '@/types/form'

export function testFormulaEngine() {
  console.log('=== 测试公式引擎 ===')
  
  const testSchema: FormSchema = {
    id: 'test',
    name: '测试表单',
    description: '',
    version: '1.0.0',
    createdAt: '',
    updatedAt: '',
    tabs: [{
      id: 'tab1',
      name: '测试',
      fields: [
        { id: 'f1', type: 'number', name: 'a', label: 'A', defaultValue: 10 },
        { id: 'f2', type: 'number', name: 'b', label: 'B', defaultValue: 20 },
        { id: 'f3', type: 'number', name: 'c', label: 'C', defaultValue: 5 }
      ]
    }]
  }
  
  const testData = { a: 10, b: 20, c: 5 }
  
  const testCases = [
    { expr: 'SUM(a, b, c)', expected: 35 },
    { expr: 'AVG(a, b, c)', expected: 35/3 },
    { expr: 'MAX(a, b, c)', expected: 20 },
    { expr: 'MIN(a, b, c)', expected: 5 },
    { expr: 'IF(a > 5, b * 2, c)', expected: 40 },
    { expr: 'ROUND(3.14159, 2)', expected: 3.14 },
    { expr: 'ABS(-10)', expected: 10 },
    { expr: 'POW(2, 3)', expected: 8 },
    { expr: 'SQRT(16)', expected: 4 },
    { expr: 'CONCAT("Hello", " ", "World")', expected: 'Hello World' },
    { expr: 'LEN("Test")', expected: 4 },
    { expr: 'UPPER("test")', expected: 'TEST' },
    { expr: 'LOWER("TEST")', expected: 'test' },
    { expr: 'AND(a > 0, b > 0)', expected: true },
    { expr: 'OR(a < 0, b > 0)', expected: true },
    { expr: 'NOT(a > 100)', expected: true }
  ]
  
  let passed = 0
  let failed = 0
  
  testCases.forEach(({ expr, expected }) => {
    const result = evaluateExpression(expr, testData, testSchema)
    const success = result.error === null && 
      (Math.abs(result.result - expected) < 0.0001 || result.result === expected)
    
    if (success) {
      passed++
      console.log(`✅ ${expr} = ${result.result}`)
    } else {
      failed++
      console.log(`❌ ${expr} = ${result.result} (期望: ${expected}, 错误: ${result.error})`)
    }
  })
  
  console.log(`\n总计: ${passed} 通过, ${failed} 失败`)
  return { passed, failed, total: testCases.length }
}

export function testDependencyChecker() {
  console.log('\n=== 测试依赖检测 ===')
  
  const schemaNoCycle: FormSchema = {
    id: 'test',
    name: '无循环',
    description: '',
    version: '1.0.0',
    createdAt: '',
    updatedAt: '',
    tabs: [{
      id: 'tab1',
      name: '测试',
      fields: [
        { id: 'f1', type: 'number', name: 'a', label: 'A' },
        { id: 'f2', type: 'number', name: 'b', label: 'B', formula: { expression: 'a + 1', dependencies: ['a'] } },
        { id: 'f3', type: 'number', name: 'c', label: 'C', formula: { expression: 'b + 1', dependencies: ['b'] } }
      ]
    }]
  }
  
  const schemaWithCycle: FormSchema = {
    id: 'test',
    name: '有循环',
    description: '',
    version: '1.0.0',
    createdAt: '',
    updatedAt: '',
    tabs: [{
      id: 'tab1',
      name: '测试',
      fields: [
        { id: 'f1', type: 'number', name: 'a', label: 'A', formula: { expression: 'b + 1', dependencies: ['b'] } },
        { id: 'f2', type: 'number', name: 'b', label: 'B', formula: { expression: 'c + 1', dependencies: ['c'] } },
        { id: 'f3', type: 'number', name: 'c', label: 'C', formula: { expression: 'a + 1', dependencies: ['a'] } }
      ]
    }]
  }
  
  const result1 = checkDependencies(schemaNoCycle)
  const result2 = checkDependencies(schemaWithCycle)
  
  console.log(`无循环依赖: ${!result1.hasCircularDependency ? '✅ 通过' : '❌ 失败'}`)
  console.log(`有循环依赖: ${result2.hasCircularDependency ? '✅ 检测到' : '❌ 未检测'}`)
  
  if (result2.hasCircularDependency) {
    console.log(`  循环路径: ${result2.circularDependencies[0].path.join(' → ')}`)
  }
  
  return { noCycle: !result1.hasCircularDependency, hasCycle: result2.hasCircularDependency }
}

export function testSchemaCompressor() {
  console.log('\n=== 测试Schema压缩 ===')
  
  const originalSchema: FormSchema = {
    id: 'test',
    name: '测试压缩',
    description: '测试Schema压缩功能',
    version: '1.0.0',
    createdAt: '2024-01-01',
    updatedAt: '2024-01-01',
    tabs: [{
      id: 'tab1',
      name: '基本信息',
      fields: [
        {
          id: 'f1', type: 'input', name: 'name1', label: '姓名1',
          required: true,
          validation: [
            { type: 'required', message: '必填' },
            { type: 'min', value: 2, message: '至少2个字符' }
          ],
          props: { options: [{ label: '是', value: 'yes' }, { label: '否', value: 'no' }] }
        },
        {
          id: 'f2', type: 'input', name: 'name2', label: '姓名2',
          required: true,
          validation: [
            { type: 'required', message: '必填' },
            { type: 'min', value: 2, message: '至少2个字符' }
          ],
          props: { options: [{ label: '是', value: 'yes' }, { label: '否', value: 'no' }] }
        },
        {
          id: 'f3', type: 'number', name: 'calc1', label: '计算1',
          formula: { expression: 'a + b', dependencies: ['a', 'b'] }
        },
        {
          id: 'f4', type: 'number', name: 'calc2', label: '计算2',
          formula: { expression: 'a + b', dependencies: ['a', 'b'] }
        }
      ]
    }]
  }
  
  const result = compressSchema(originalSchema)
  
  console.log(`原始大小: ${result.originalSize} 字节`)
  console.log(`压缩大小: ${result.compressedSize} 字节`)
  console.log(`压缩率: ${result.compressionRatio}%`)
  console.log(`去重统计:`)
  console.log(`  - 校验规则: ${result.stats.validationDeduplications} 个唯一定义`)
  console.log(`  - 选项集合: ${result.stats.optionSetDeduplications} 个唯一定义`)
  console.log(`  - 字段模板: ${result.stats.fieldTemplateDeduplications} 个唯一定义`)
  console.log(`  - 公式模板: ${result.stats.formulaDeduplications} 个唯一定义`)
  
  const decompressed = decompressSchema(result.compressed)
  const isLossless = JSON.stringify(decompressed.tabs[0].fields.map(f => ({
    type: f.type, name: f.name, label: f.label, validation: f.validation
  }))) === JSON.stringify(originalSchema.tabs[0].fields.map(f => ({
    type: f.type, name: f.name, label: f.label, validation: f.validation
  })))
  
  console.log(`\n无损压缩验证: ${isLossless ? '✅ 通过' : '❌ 失败'}`)
  
  return result
}

export function runAllTests() {
  console.log('\n🧪 开始运行所有测试...\n')
  
  testFormulaEngine()
  testDependencyChecker()
  testSchemaCompressor()
  
  console.log('\n✅ 测试完成!')
}
