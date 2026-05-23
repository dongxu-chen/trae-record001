class Tokenizer {
  constructor(input) {
    this.input = input
    this.pos = 0
    this.tokens = []
  }

  tokenize() {
    while (this.pos < this.input.length) {
      this.skipWhitespace()
      if (this.pos >= this.input.length) break

      const char = this.input[this.pos]

      if (char === '"' || char === "'") {
        this.tokens.push(this.readString(char))
      } else if (/\d/.test(char)) {
        this.tokens.push(this.readNumber())
      } else if (/[a-zA-Z_$]/.test(char)) {
        this.tokens.push(this.readIdentifier())
      } else if ('+-*/%=!<>()&|'.includes(char)) {
        this.tokens.push(this.readOperator())
      } else {
        throw new Error(`Unexpected character: ${char}`)
      }
    }
    return this.tokens
  }

  skipWhitespace() {
    while (this.pos < this.input.length && /\s/.test(this.input[this.pos])) {
      this.pos++
    }
  }

  readString(quote) {
    this.pos++
    let value = ''
    while (this.pos < this.input.length && this.input[this.pos] !== quote) {
      if (this.input[this.pos] === '\\') {
        this.pos++
        value += this.input[this.pos]
      } else {
        value += this.input[this.pos]
      }
      this.pos++
    }
    this.pos++
    return { type: 'STRING', value }
  }

  readNumber() {
    let value = ''
    while (this.pos < this.input.length && /[\d.]/.test(this.input[this.pos])) {
      value += this.input[this.pos]
      this.pos++
    }
    return { type: 'NUMBER', value: parseFloat(value) }
  }

  readIdentifier() {
    let value = ''
    while (this.pos < this.input.length && /[a-zA-Z0-9_$.]/.test(this.input[this.pos])) {
      value += this.input[this.pos]
      this.pos++
    }

    const keywords = {
      true: { type: 'BOOLEAN', value: true },
      false: { type: 'BOOLEAN', value: false },
      null: { type: 'NULL', value: null },
      undefined: { type: 'UNDEFINED', value: undefined }
    }

    if (keywords[value]) {
      return keywords[value]
    }

    return { type: 'IDENTIFIER', value }
  }

  readOperator() {
    const twoChar = this.input.slice(this.pos, this.pos + 2)
    const twoCharOps = ['==', '!=', '>=', '<=', '&&', '||', '++', '--']

    if (twoCharOps.includes(twoChar)) {
      this.pos += 2
      return { type: 'OPERATOR', value: twoChar }
    }

    const char = this.input[this.pos]
    this.pos++
    return { type: 'OPERATOR', value: char }
  }
}

class Parser {
  constructor(tokens) {
    this.tokens = tokens
    this.pos = 0
  }

  parse() {
    return this.parseOr()
  }

  current() {
    return this.tokens[this.pos]
  }

  consume() {
    return this.tokens[this.pos++]
  }

  parseOr() {
    let left = this.parseAnd()
    while (this.current()?.value === '||') {
      this.consume()
      const right = this.parseAnd()
      left = { type: 'LogicalExpression', operator: '||', left, right }
    }
    return left
  }

  parseAnd() {
    let left = this.parseEquality()
    while (this.current()?.value === '&&') {
      this.consume()
      const right = this.parseEquality()
      left = { type: 'LogicalExpression', operator: '&&', left, right }
    }
    return left
  }

  parseEquality() {
    let left = this.parseComparison()
    while (this.current()?.value === '==' || this.current()?.value === '!=') {
      const operator = this.consume().value
      const right = this.parseComparison()
      left = { type: 'BinaryExpression', operator, left, right }
    }
    return left
  }

  parseComparison() {
    let left = this.parseAdditive()
    while (['>', '<', '>=', '<='].includes(this.current()?.value)) {
      const operator = this.consume().value
      const right = this.parseAdditive()
      left = { type: 'BinaryExpression', operator, left, right }
    }
    return left
  }

  parseAdditive() {
    let left = this.parseMultiplicative()
    while (['+', '-'].includes(this.current()?.value)) {
      const operator = this.consume().value
      const right = this.parseMultiplicative()
      left = { type: 'BinaryExpression', operator, left, right }
    }
    return left
  }

  parseMultiplicative() {
    let left = this.parseUnary()
    while (['*', '/', '%'].includes(this.current()?.value)) {
      const operator = this.consume().value
      const right = this.parseUnary()
      left = { type: 'BinaryExpression', operator, left, right }
    }
    return left
  }

  parseUnary() {
    if (['!', '-', '+'].includes(this.current()?.value)) {
      const operator = this.consume().value
      const argument = this.parseUnary()
      return { type: 'UnaryExpression', operator, argument }
    }
    return this.parsePrimary()
  }

  parsePrimary() {
    const token = this.consume()

    if (token.type === 'NUMBER') {
      return { type: 'Literal', value: token.value }
    }
    if (token.type === 'STRING') {
      return { type: 'Literal', value: token.value }
    }
    if (token.type === 'BOOLEAN') {
      return { type: 'Literal', value: token.value }
    }
    if (token.type === 'NULL') {
      return { type: 'Literal', value: null }
    }
    if (token.type === 'IDENTIFIER') {
      return { type: 'Identifier', name: token.value }
    }
    if (token.value === '(') {
      const expr = this.parseOr()
      if (this.current()?.value !== ')') {
        throw new Error('Expected )')
      }
      this.consume()
      return expr
    }

    throw new Error(`Unexpected token: ${JSON.stringify(token)}`)
  }
}

const ALLOWED_METHODS = new Set([
  'includes', 'startsWith', 'endsWith', 'indexOf', 'lastIndexOf',
  'length', 'toLowerCase', 'toUpperCase', 'trim', 'charAt'
])

const ALLOWED_PROPERTIES = new Set(['length'])

class Interpreter {
  constructor(context = {}) {
    this.context = context
  }

  evaluate(ast) {
    return this.visit(ast)
  }

  visit(node) {
    switch (node.type) {
      case 'Literal':
        return node.value
      case 'Identifier':
        return this.getIdentifierValue(node.name)
      case 'BinaryExpression':
        return this.visitBinaryExpression(node)
      case 'LogicalExpression':
        return this.visitLogicalExpression(node)
      case 'UnaryExpression':
        return this.visitUnaryExpression(node)
      default:
        throw new Error(`Unknown node type: ${node.type}`)
    }
  }

  getIdentifierValue(name) {
    const parts = name.split('.')
    let value = this.context

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]

      if (i === 0) {
        if (value[part] === undefined) {
          return undefined
        }
        value = value[part]
      } else {
        if (typeof value === 'object' && value !== null) {
          if (!ALLOWED_PROPERTIES.has(part) && typeof value[part] !== 'function') {
            throw new Error(`Access to property '${part}' is not allowed`)
          }
          if (typeof value[part] === 'function') {
            if (!ALLOWED_METHODS.has(part)) {
              throw new Error(`Call to method '${part}' is not allowed`)
            }
            return (...args) => {
              return value[part].apply(value, args)
            }
          }
          value = value[part]
        } else {
          return undefined
        }
      }
    }

    return value
  }

  visitBinaryExpression(node) {
    const left = this.visit(node.left)
    const right = this.visit(node.right)

    switch (node.operator) {
      case '+':
        return left + right
      case '-':
        return left - right
      case '*':
        return left * right
      case '/':
        return left / right
      case '%':
        return left % right
      case '==':
        return left == right
      case '!=':
        return left != right
      case '>':
        return left > right
      case '<':
        return left < right
      case '>=':
        return left >= right
      case '<=':
        return left <= right
      default:
        throw new Error(`Unknown operator: ${node.operator}`)
    }
  }

  visitLogicalExpression(node) {
    const left = this.visit(node.left)

    if (node.operator === '||') {
      return left || this.visit(node.right)
    }
    if (node.operator === '&&') {
      return left && this.visit(node.right)
    }

    throw new Error(`Unknown logical operator: ${node.operator}`)
  }

  visitUnaryExpression(node) {
    const value = this.visit(node.argument)

    switch (node.operator) {
      case '!':
        return !value
      case '-':
        return -value
      case '+':
        return +value
      default:
        throw new Error(`Unknown unary operator: ${node.operator}`)
    }
  }
}

export function evaluateExpression(expression, context = {}) {
  try {
    const tokenizer = new Tokenizer(expression)
    const tokens = tokenizer.tokenize()
    const parser = new Parser(tokens)
    const ast = parser.parse()
    const interpreter = new Interpreter(context)
    return interpreter.evaluate(ast)
  } catch (error) {
    console.error('Expression evaluation error:', error)
    return false
  }
}

export function validateExpression(expression) {
  try {
    const tokenizer = new Tokenizer(expression)
    const tokens = tokenizer.tokenize()
    const parser = new Parser(tokens)
    parser.parse()
    return { valid: true }
  } catch (error) {
    return { valid: false, error: error.message }
  }
}

export function generateLinkageExpression(rule, formItems) {
  const targetItem = formItems.find(f => f.id === rule.targetField)
  if (!targetItem) return ''

  const fieldName = targetItem.field
  const value = rule.value
  const action = rule.action

  let expression = ''
  switch (rule.operator) {
    case '==':
      expression = `formData.${fieldName} == '${value}'`
      break
    case '!=':
      expression = `formData.${fieldName} != '${value}'`
      break
    case 'includes':
      expression = `formData.${fieldName}.includes('${value}')`
      break
    case 'empty':
      expression = `!formData.${fieldName}`
      break
    case 'notEmpty':
      expression = `!!formData.${fieldName}`
      break
  }

  return action === 'hide' ? `!(${expression})` : expression
}
