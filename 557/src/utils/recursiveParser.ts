export type ASTNode =
  | { type: 'number'; value: number }
  | { type: 'variable'; name: string }
  | { type: 'constant'; name: string; value: number }
  | { type: 'binary'; op: string; left: ASTNode; right: ASTNode }
  | { type: 'unary'; op: string; arg: ASTNode }
  | { type: 'function'; name: string; args: ASTNode[] }
  | { type: 'piecewise'; branches: { condition: ASTNode; expr: ASTNode }[]; elseExpr: ASTNode }

export interface CompiledExpression {
  ast: ASTNode;
  evaluate: (x: number) => number | null;
  toString: () => string;
}

class Tokenizer {
  private pos = 0;
  private tokens: { type: string; value: string; pos: number }[] = [];

  constructor(private input: string) {
    this.tokenize();
  }

  private tokenize(): void {
    const patterns: [RegExp, string][] = [
      [/^\s+/, 'WHITESPACE'],
      [/^\d+\.?\d*([eE][+-]?\d+)?/, 'NUMBER'],
      [/^pi\b/, 'PI'],
      [/^e\b/, 'E'],
      [/^piecewise\b/, 'PIECEWISE'],
      [/^sin\b/, 'SIN'],
      [/^cos\b/, 'COS'],
      [/^tan\b/, 'TAN'],
      [/^asin\b/, 'ASIN'],
      [/^acos\b/, 'ACOS'],
      [/^atan\b/, 'ATAN'],
      [/^sinh\b/, 'SINH'],
      [/^cosh\b/, 'COSH'],
      [/^tanh\b/, 'TANH'],
      [/^sqrt\b/, 'SQRT'],
      [/^log\b/, 'LOG'],
      [/^ln\b/, 'LN'],
      [/^log10\b/, 'LOG10'],
      [/^log2\b/, 'LOG2'],
      [/^exp\b/, 'EXP'],
      [/^abs\b/, 'ABS'],
      [/^ceil\b/, 'CEIL'],
      [/^floor\b/, 'FLOOR'],
      [/^round\b/, 'ROUND'],
      [/^sign\b/, 'SIGN'],
      [/^[a-zA-Z_][a-zA-Z0-9_]*/, 'IDENTIFIER'],
      [/^\+/, 'PLUS'],
      [/^-/, 'MINUS'],
      [/^\*/, 'MULTIPLY'],
      [/^\//, 'DIVIDE'],
      [/^\^/, 'POWER'],
      [/^\(/, 'LPAREN'],
      [/^\)/, 'RPAREN'],
      [/^,/, 'COMMA'],
      [/^<=/, 'LE'],
      [/^>=/, 'GE'],
      [/^==/, 'EQ'],
      [/^!=/, 'NE'],
      [/^</, 'LT'],
      [/^>/, 'GT'],
      [/^&&/, 'AND'],
      [/^\|\|/, 'OR'],
      [/^!/, 'NOT'],
    ];

    let pos = 0;
    while (pos < this.input.length) {
      let matched = false;
      for (const [pattern, type] of patterns) {
        const match = this.input.slice(pos).match(pattern);
        if (match) {
          if (type !== 'WHITESPACE') {
            this.tokens.push({ type, value: match[0], pos });
          }
          pos += match[0].length;
          matched = true;
          break;
        }
      }
      if (!matched) {
        throw new Error(`无法识别的字符 '${this.input[pos]}' 在位置 ${pos}`);
      }
    }
    this.tokens.push({ type: 'EOF', value: '', pos });
  }

  peek(): { type: string; value: string; pos: number } {
    return this.tokens[this.pos];
  }

  consume(...expected: string[]): { type: string; value: string; pos: number } {
    const token = this.tokens[this.pos];
    if (expected.length > 0 && !expected.includes(token.type)) {
      throw new Error(`期望 ${expected.join(' 或 ')}，但在位置 ${token.pos} 得到 '${token.value}'`);
    }
    this.pos++;
    return token;
  }

  currentPos(): number {
    return this.pos;
  }

  backtrack(pos: number): void {
    this.pos = pos;
  }
}

class Parser {
  private tokenizer: Tokenizer;

  constructor(input: string) {
    this.tokenizer = new Tokenizer(input);
  }

  parse(): ASTNode {
    const node = this.parseExpression();
    if (this.tokenizer.peek().type !== 'EOF') {
      throw new Error(`表达式在位置 ${this.tokenizer.peek().pos} 未结束`);
    }
    return node;
  }

  private parseExpression(): ASTNode {
    return this.parseOr();
  }

  private parseOr(): ASTNode {
    let left = this.parseAnd();
    while (this.tokenizer.peek().type === 'OR') {
      this.tokenizer.consume('OR');
      const right = this.parseAnd();
      left = { type: 'binary', op: '||', left, right };
    }
    return left;
  }

  private parseAnd(): ASTNode {
    let left = this.parseComparison();
    while (this.tokenizer.peek().type === 'AND') {
      this.tokenizer.consume('AND');
      const right = this.parseComparison();
      left = { type: 'binary', op: '&&', left, right };
    }
    return left;
  }

  private parseComparison(): ASTNode {
    let left = this.parseAddSub();
    const ops = ['LT', 'GT', 'LE', 'GE', 'EQ', 'NE'];
    const opMap: Record<string, string> = {
      LT: '<', GT: '>', LE: '<=', GE: '>=', EQ: '==', NE: '!='
    };
    while (ops.includes(this.tokenizer.peek().type)) {
      const token = this.tokenizer.consume();
      const right = this.parseAddSub();
      left = { type: 'binary', op: opMap[token.type], left, right };
    }
    return left;
  }

  private parseAddSub(): ASTNode {
    let left = this.parseMulDiv();
    while (['PLUS', 'MINUS'].includes(this.tokenizer.peek().type)) {
      const token = this.tokenizer.consume();
      const right = this.parseMulDiv();
      left = { type: 'binary', op: token.type === 'PLUS' ? '+' : '-', left, right };
    }
    return left;
  }

  private parseMulDiv(): ASTNode {
    let left = this.parsePower();
    while (['MULTIPLY', 'DIVIDE'].includes(this.tokenizer.peek().type)) {
      const token = this.tokenizer.consume();
      const right = this.parsePower();
      left = { type: 'binary', op: token.type === 'MULTIPLY' ? '*' : '/', left, right };
    }
    return left;
  }

  private parsePower(): ASTNode {
    let left = this.parseUnary();
    if (this.tokenizer.peek().type === 'POWER') {
      this.tokenizer.consume('POWER');
      const right = this.parsePower();
      left = { type: 'binary', op: '^', left, right };
    }
    return left;
  }

  private parseUnary(): ASTNode {
    if (this.tokenizer.peek().type === 'MINUS') {
      this.tokenizer.consume('MINUS');
      const arg = this.parseUnary();
      return { type: 'unary', op: '-', arg };
    }
    if (this.tokenizer.peek().type === 'NOT') {
      this.tokenizer.consume('NOT');
      const arg = this.parseUnary();
      return { type: 'unary', op: '!', arg };
    }
    return this.parsePrimary();
  }

  private parsePrimary(): ASTNode {
    const token = this.tokenizer.peek();

    if (token.type === 'NUMBER') {
      this.tokenizer.consume('NUMBER');
      return { type: 'number', value: parseFloat(token.value) };
    }

    if (token.type === 'PI') {
      this.tokenizer.consume('PI');
      return { type: 'constant', name: 'pi', value: Math.PI };
    }

    if (token.type === 'E') {
      this.tokenizer.consume('E');
      return { type: 'constant', name: 'e', value: Math.E };
    }

    if (token.type === 'IDENTIFIER') {
      this.tokenizer.consume('IDENTIFIER');
      return { type: 'variable', name: token.value };
    }

    if (token.type === 'PIECEWISE') {
      return this.parsePiecewise();
    }

    const funcTypes = [
      'SIN', 'COS', 'TAN', 'ASIN', 'ACOS', 'ATAN',
      'SINH', 'COSH', 'TANH',
      'SQRT', 'LOG', 'LN', 'LOG10', 'LOG2', 'EXP',
      'ABS', 'CEIL', 'FLOOR', 'ROUND', 'SIGN'
    ];
    if (funcTypes.includes(token.type)) {
      const funcName = token.value.toLowerCase();
      this.tokenizer.consume(token.type);
      this.tokenizer.consume('LPAREN');
      const args: ASTNode[] = [];
      if (this.tokenizer.peek().type !== 'RPAREN') {
        args.push(this.parseExpression());
        while (this.tokenizer.peek().type === 'COMMA') {
          this.tokenizer.consume('COMMA');
          args.push(this.parseExpression());
        }
      }
      this.tokenizer.consume('RPAREN');
      return { type: 'function', name: funcName, args };
    }

    if (token.type === 'LPAREN') {
      this.tokenizer.consume('LPAREN');
      const node = this.parseExpression();
      this.tokenizer.consume('RPAREN');
      return node;
    }

    throw new Error(`在位置 ${token.pos} 处遇到意外的 '${token.value}'`);
  }

  private parsePiecewise(): ASTNode {
    this.tokenizer.consume('PIECEWISE');
    this.tokenizer.consume('LPAREN');

    const args: ASTNode[] = [];

    if (this.tokenizer.peek().type !== 'RPAREN') {
      args.push(this.parseExpression());
      while (this.tokenizer.peek().type === 'COMMA') {
        this.tokenizer.consume('COMMA');
        args.push(this.parseExpression());
      }
    }

    this.tokenizer.consume('RPAREN');

    if (args.length < 2) {
      throw new Error('分段函数至少需要2个参数');
    }

    const branches: { condition: ASTNode; expr: ASTNode }[] = [];
    let elseExpr: ASTNode = { type: 'number', value: NaN };

    if (args.length % 2 === 1) {
      elseExpr = args[args.length - 1];
      for (let i = 0; i < args.length - 1; i += 2) {
        branches.push({ condition: args[i], expr: args[i + 1] });
      }
    } else {
      for (let i = 0; i < args.length; i += 2) {
        if (i + 1 < args.length) {
          branches.push({ condition: args[i], expr: args[i + 1] });
        }
      }
    }

    return { type: 'piecewise', branches, elseExpr };
  }
}

function evaluateAST(node: ASTNode, x: number, y?: number): number {
  switch (node.type) {
    case 'number':
      return node.value;
    case 'variable':
      if (node.name === 'x') return x;
      if (node.name === 'y' && y !== undefined) return y;
      return NaN;
    case 'constant':
      return node.value;
    case 'unary': {
      const arg = evaluateAST(node.arg, x, y);
      if (node.op === '-') return -arg;
      if (node.op === '!') return arg === 0 ? 1 : 0;
      return NaN;
    }
    case 'binary': {
      const left = evaluateAST(node.left, x, y);
      const right = evaluateAST(node.right, x, y);
      switch (node.op) {
        case '+': return left + right;
        case '-': return left - right;
        case '*': return left * right;
        case '/': return right !== 0 ? left / right : NaN;
        case '^': return Math.pow(left, right);
        case '<': return left < right ? 1 : 0;
        case '>': return left > right ? 1 : 0;
        case '<=': return left <= right ? 1 : 0;
        case '>=': return left >= right ? 1 : 0;
        case '==': return Math.abs(left - right) < 1e-10 ? 1 : 0;
        case '!=': return Math.abs(left - right) >= 1e-10 ? 1 : 0;
        case '&&': return (left !== 0 && right !== 0) ? 1 : 0;
        case '||': return (left !== 0 || right !== 0) ? 1 : 0;
        default: return NaN;
      }
    }
    case 'function': {
      const args = node.args.map(a => evaluateAST(a, x, y));
      const arg = args[0];
      switch (node.name) {
        case 'sin': return Math.sin(arg);
        case 'cos': return Math.cos(arg);
        case 'tan': return Math.tan(arg);
        case 'asin': return Math.asin(arg);
        case 'acos': return Math.acos(arg);
        case 'atan': return Math.atan(arg);
        case 'sinh': return Math.sinh(arg);
        case 'cosh': return Math.cosh(arg);
        case 'tanh': return Math.tanh(arg);
        case 'sqrt': return arg >= 0 ? Math.sqrt(arg) : NaN;
        case 'log': return arg > 0 ? Math.log(arg) : NaN;
        case 'ln': return arg > 0 ? Math.log(arg) : NaN;
        case 'log10': return arg > 0 ? Math.log10(arg) : NaN;
        case 'log2': return arg > 0 ? Math.log2(arg) : NaN;
        case 'exp': return Math.exp(arg);
        case 'abs': return Math.abs(arg);
        case 'ceil': return Math.ceil(arg);
        case 'floor': return Math.floor(arg);
        case 'round': return Math.round(arg);
        case 'sign': return Math.sign(arg);
        default: return NaN;
      }
    }
    case 'piecewise': {
      for (const branch of node.branches) {
        const cond = evaluateAST(branch.condition, x, y);
        if (cond !== 0) {
          return evaluateAST(branch.expr, x, y);
        }
      }
      return evaluateAST(node.elseExpr, x, y);
    }
  }
}

function astToString(node: ASTNode): string {
  switch (node.type) {
    case 'number':
      return node.value.toString();
    case 'variable':
      return node.name;
    case 'constant':
      return node.name;
    case 'unary':
      return `(${node.op}${astToString(node.arg)})`;
    case 'binary':
      return `(${astToString(node.left)} ${node.op} ${astToString(node.right)})`;
    case 'function':
      return `${node.name}(${node.args.map(astToString).join(', ')})`;
    case 'piecewise': {
      const parts = node.branches.map(b => `${astToString(b.condition)}, ${astToString(b.expr)}`).join(', ');
      const elseStr = node.elseExpr.type !== 'number' || !isNaN((node.elseExpr as { value: number }).value)
        ? `, ${astToString(node.elseExpr)}` : '';
      return `piecewise(${parts}${elseStr})`;
    }
  }
}

export function parseExpression(expr: string): { success: boolean; ast?: ASTNode; error?: string } {
  try {
    const parser = new Parser(expr);
    const ast = parser.parse();
    return { success: true, ast };
  } catch (e) {
    return { success: false, error: (e as Error).message };
  }
}

function collectVariables(node: ASTNode, vars: Set<string>): void {
  switch (node.type) {
    case 'variable':
      vars.add(node.name);
      break;
    case 'unary':
      collectVariables(node.arg, vars);
      break;
    case 'binary':
      collectVariables(node.left, vars);
      collectVariables(node.right, vars);
      break;
    case 'function':
      node.args.forEach(arg => collectVariables(arg, vars));
      break;
    case 'piecewise':
      node.branches.forEach(b => {
        collectVariables(b.condition, vars);
        collectVariables(b.expr, vars);
      });
      collectVariables(node.elseExpr, vars);
      break;
  }
}

export function compileExpression(expr: string, allowedVariables: string[] = ['x']): { success: boolean; compiled?: CompiledExpression; error?: string } {
  const result = parseExpression(expr);
  if (!result.success || !result.ast) {
    return { success: false, error: result.error };
  }

  const ast = result.ast;

  const variables = new Set<string>();
  collectVariables(ast, variables);
  for (const v of variables) {
    if (!allowedVariables.includes(v)) {
      return {
        success: false,
        error: `不支持的变量 "${v}"，仅允许使用 ${allowedVariables.map(v => `"${v}"`).join(', ')}`
      };
    }
  }

  const compiled: CompiledExpression = {
    ast,
    evaluate: (x: number): number | null => {
      try {
        const val = evaluateAST(ast, x);
        return Number.isFinite(val) ? val : null;
      } catch {
        return null;
      }
    },
    toString: () => astToString(ast)
  };

  return { success: true, compiled };
}

export function differentiateAST(node: ASTNode, variable: string = 'x'): ASTNode {
  switch (node.type) {
    case 'number':
      return { type: 'number', value: 0 };
    case 'constant':
      return { type: 'number', value: 0 };
    case 'variable':
      return { type: 'number', value: node.name === variable ? 1 : 0 };
    case 'unary': {
      const dArg = differentiateAST(node.arg, variable);
      if (node.op === '-') {
        return { type: 'unary', op: '-', arg: dArg };
      }
      return dArg;
    }
    case 'binary': {
      const dLeft = differentiateAST(node.left, variable);
      const dRight = differentiateAST(node.right, variable);
      switch (node.op) {
        case '+':
        case '-':
          return { type: 'binary', op: node.op, left: dLeft, right: dRight };
        case '*':
          return {
            type: 'binary',
            op: '+',
            left: { type: 'binary', op: '*', left: dLeft, right: node.right },
            right: { type: 'binary', op: '*', left: node.left, right: dRight }
          };
        case '/':
          return {
            type: 'binary',
            op: '/',
            left: {
              type: 'binary',
              op: '-',
              left: { type: 'binary', op: '*', left: dLeft, right: node.right },
              right: { type: 'binary', op: '*', left: node.left, right: dRight }
            },
            right: { type: 'binary', op: '^', left: node.right, right: { type: 'number', value: 2 } }
          };
        case '^': {
          const isRightConstant = isConstant(node.right);
          if (isRightConstant) {
            const power = getConstantValue(node.right);
            return {
              type: 'binary',
              op: '*',
              left: {
                type: 'binary',
                op: '*',
                left: { type: 'number', value: power },
                right: {
                  type: 'binary',
                  op: '^',
                  left: node.left,
                  right: { type: 'number', value: power - 1 }
                }
              },
              right: dLeft
            };
          }
          const lnU = { type: 'function', name: 'ln', args: [node.left] };
          return {
            type: 'binary',
            op: '*',
            left: node,
            right: differentiateAST(
              { type: 'binary', op: '*', left: node.right, right: lnU },
              variable
            )
          };
        }
        default:
          return { type: 'number', value: 0 };
      }
    }
    case 'function': {
      const arg = node.args[0];
      const dArg = differentiateAST(arg, variable);
      switch (node.name) {
        case 'sin':
          return {
            type: 'binary',
            op: '*',
            left: { type: 'function', name: 'cos', args: [arg] },
            right: dArg
          };
        case 'cos':
          return {
            type: 'binary',
            op: '*',
            left: {
              type: 'unary',
              op: '-',
              arg: { type: 'function', name: 'sin', args: [arg] }
            },
            right: dArg
          };
        case 'tan':
          return {
            type: 'binary',
            op: '*',
            left: {
              type: 'binary',
              op: '^',
              left: { type: 'function', name: 'cos', args: [arg] },
              right: { type: 'number', value: 2 }
            },
            right: dArg
          };
        case 'asin':
          return {
            type: 'binary',
            op: '*',
            left: {
              type: 'binary',
              op: '/',
              left: { type: 'number', value: 1 },
              right: {
                type: 'function',
                name: 'sqrt',
                args: [{
                  type: 'binary',
                  op: '-',
                  left: { type: 'number', value: 1 },
                  right: { type: 'binary', op: '^', left: arg, right: { type: 'number', value: 2 } }
                }]
              }
            },
            right: dArg
          };
        case 'acos':
          return {
            type: 'binary',
            op: '*',
            left: {
              type: 'binary',
              op: '/',
              left: { type: 'number', value: -1 },
              right: {
                type: 'function',
                name: 'sqrt',
                args: [{
                  type: 'binary',
                  op: '-',
                  left: { type: 'number', value: 1 },
                  right: { type: 'binary', op: '^', left: arg, right: { type: 'number', value: 2 } }
                }]
              }
            },
            right: dArg
          };
        case 'atan':
          return {
            type: 'binary',
            op: '*',
            left: {
              type: 'binary',
              op: '/',
              left: { type: 'number', value: 1 },
              right: {
                type: 'binary',
                op: '+',
                left: { type: 'binary', op: '^', left: arg, right: { type: 'number', value: 2 } },
                right: { type: 'number', value: 1 }
              }
            },
            right: dArg
          };
        case 'sqrt':
          return {
            type: 'binary',
            op: '*',
            left: {
              type: 'binary',
              op: '/',
              left: { type: 'number', value: 0.5 },
              right: node
            },
            right: dArg
          };
        case 'ln':
        case 'log':
          return {
            type: 'binary',
            op: '*',
            left: { type: 'binary', op: '/', left: { type: 'number', value: 1 }, right: arg },
            right: dArg
          };
        case 'log10':
          return {
            type: 'binary',
            op: '*',
            left: {
              type: 'binary',
              op: '/',
              left: { type: 'number', value: 1 },
              right: { type: 'binary', op: '*', left: arg, right: { type: 'constant', name: 'ln10', value: Math.LN10 } }
            },
            right: dArg
          };
        case 'exp':
          return { type: 'binary', op: '*', left: node, right: dArg };
        case 'abs':
          return {
            type: 'binary',
            op: '*',
            left: { type: 'function', name: 'sign', args: [arg] },
            right: dArg
          };
        default:
          return { type: 'number', value: 0 };
      }
    }
    case 'piecewise': {
      const branches = node.branches.map(b => ({
        condition: b.condition,
        expr: differentiateAST(b.expr, variable)
      }));
      const elseExpr = differentiateAST(node.elseExpr, variable);
      return { type: 'piecewise', branches, elseExpr };
    }
  }
}

function isConstant(node: ASTNode): boolean {
  if (node.type === 'number' || node.type === 'constant') return true;
  if (node.type === 'binary') {
    return isConstant(node.left) && isConstant(node.right);
  }
  if (node.type === 'unary') {
    return isConstant(node.arg);
  }
  if (node.type === 'function') {
    return node.args.every(isConstant);
  }
  return false;
}

function getConstantValue(node: ASTNode): number {
  if (node.type === 'number') return node.value;
  if (node.type === 'constant') return node.value;
  if (node.type === 'binary') {
    const l = getConstantValue(node.left);
    const r = getConstantValue(node.right);
    switch (node.op) {
      case '+': return l + r;
      case '-': return l - r;
      case '*': return l * r;
      case '/': return l / r;
      case '^': return Math.pow(l, r);
    }
  }
  if (node.type === 'unary' && node.op === '-') {
    return -getConstantValue(node.arg);
  }
  return evaluateAST(node, 0);
}

export function simplifyAST(node: ASTNode): ASTNode {
  if (node.type === 'binary') {
    const left = simplifyAST(node.left);
    const right = simplifyAST(node.right);

    if (left.type === 'number' && right.type === 'number') {
      const l = left.value;
      const r = right.value;
      let result: number;
      switch (node.op) {
        case '+': result = l + r; break;
        case '-': result = l - r; break;
        case '*': result = l * r; break;
        case '/': result = r !== 0 ? l / r : NaN; break;
        case '^': result = Math.pow(l, r); break;
        default: return node;
      }
      if (Number.isFinite(result)) {
        return { type: 'number', value: result };
      }
    }

    if (node.op === '+') {
      if (left.type === 'number' && left.value === 0) return right;
      if (right.type === 'number' && right.value === 0) return left;
    }
    if (node.op === '-') {
      if (right.type === 'number' && right.value === 0) return left;
    }
    if (node.op === '*') {
      if (left.type === 'number' && left.value === 0) return { type: 'number', value: 0 };
      if (right.type === 'number' && right.value === 0) return { type: 'number', value: 0 };
      if (left.type === 'number' && left.value === 1) return right;
      if (right.type === 'number' && right.value === 1) return left;
    }
    if (node.op === '/') {
      if (left.type === 'number' && left.value === 0) return { type: 'number', value: 0 };
      if (right.type === 'number' && right.value === 1) return left;
    }
    if (node.op === '^') {
      if (right.type === 'number' && right.value === 0) return { type: 'number', value: 1 };
      if (right.type === 'number' && right.value === 1) return left;
      if (left.type === 'number' && left.value === 1) return { type: 'number', value: 1 };
    }

    return { ...node, left, right };
  }

  if (node.type === 'unary') {
    const arg = simplifyAST(node.arg);
    if (arg.type === 'number') {
      return { type: 'number', value: -arg.value };
    }
    return { ...node, arg };
  }

  if (node.type === 'function') {
    const args = node.args.map(simplifyAST);
    if (args.every(a => a.type === 'number')) {
      const values = args.map(a => (a as { value: number }).value);
      try {
        const result = evaluateAST({ ...node, args: values.map(v => ({ type: 'number' as const, value: v })) }, 0);
        if (Number.isFinite(result)) {
          return { type: 'number', value: result };
        }
      } catch {
        // ignore
      }
    }
    return { ...node, args };
  }

  return node;
}
