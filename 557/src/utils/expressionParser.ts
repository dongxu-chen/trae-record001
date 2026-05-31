import {
  parseExpression,
  compileExpression as compileExpr,
  differentiateAST,
  simplifyAST,
  CompiledExpression as NewCompiledExpression,
  ASTNode
} from './recursiveParser';

export type CompiledExpression = NewCompiledExpression;

export function preprocessExpression(expr: string): string {
  let result = expr.trim();

  result = result.replace(/\^/g, '^');

  result = result.replace(/(\d)\s*([a-zA-Z])/g, '$1*$2');
  result = result.replace(/([a-zA-Z])\s*(\d)/g, '$1*$2');
  result = result.replace(/(\))\s*(\d)/g, '$1*$2');
  result = result.replace(/(\d)\s*(\()/g, '$1*$2');
  result = result.replace(/(\))\s*([a-zA-Z])/g, '$1*$2');
  result = result.replace(/([a-zA-Z])\s*(\()/g, '$1*$2');
  result = result.replace(/(\))\s*(\()/g, '$1*$2');

  return result;
}

export function validateExpression(expr: string): { valid: boolean; error?: string } {
  if (!expr || !expr.trim()) {
    return { valid: false, error: '表达式不能为空' };
  }

  try {
    const processed = preprocessExpression(expr);
    const result = parseExpression(processed);
    if (!result.success) {
      return { valid: false, error: result.error };
    }
    return { valid: true };
  } catch (e) {
    return { valid: false, error: (e as Error).message || '表达式语法错误' };
  }
}

export function parseAndCompile(expr: string): { success: boolean; compiled?: CompiledExpression; error?: string } {
  try {
    const validation = validateExpression(expr);
    if (!validation.valid) {
      return { success: false, error: validation.error };
    }

    const processed = preprocessExpression(expr);
    const result = compileExpr(processed);

    if (!result.success || !result.compiled) {
      return { success: false, error: result.error };
    }

    return { success: true, compiled: result.compiled };
  } catch (e) {
    return { success: false, error: (e as Error).message || '编译表达式失败' };
  }
}

function numericalDerivative(
  evaluate: (x: number) => number | null,
  x: number,
  h: number = 1e-5
): number | null {
  const y1 = evaluate(x + h);
  const y2 = evaluate(x - h);

  if (y1 === null || y2 === null) {
    return null;
  }

  return (y1 - y2) / (2 * h);
}

function verifyDerivative(
  originalEvaluate: (x: number) => number | null,
  derivativeEvaluate: (x: number) => number | null,
  testPoints: number[] = [-2, -1, 0, 1, 2, 0.5, -0.5]
): { valid: boolean; confidence: number } {
  let validCount = 0;
  let totalCount = 0;

  for (const x of testPoints) {
    const y = originalEvaluate(x);
    if (y === null || !Number.isFinite(y)) continue;

    const symbolic = derivativeEvaluate(x);
    const numerical = numericalDerivative(originalEvaluate, x);

    if (symbolic === null || numerical === null) continue;
    if (!Number.isFinite(symbolic) || !Number.isFinite(numerical)) continue;

    const absError = Math.abs(symbolic - numerical);
    const relError = absError / (Math.max(Math.abs(symbolic), Math.abs(numerical)) + 1e-10);

    if (absError < 1e-4 || relError < 1e-3) {
      validCount++;
    }
    totalCount++;
  }

  if (totalCount === 0) {
    return { valid: true, confidence: 1 };
  }

  const confidence = validCount / totalCount;
  return { valid: confidence >= 0.7, confidence };
}

export function computeDerivative(
  expr: string,
  variable: string = 'x'
): { success: boolean; derivative?: string; compiled?: CompiledExpression; error?: string; confidence?: number } {
  try {
    const validation = validateExpression(expr);
    if (!validation.valid) {
      return { success: false, error: validation.error };
    }

    const processed = preprocessExpression(expr);
    const parseResult = parseExpression(processed);

    if (!parseResult.success || !parseResult.ast) {
      return { success: false, error: parseResult.error };
    }

    const derivativeAst = differentiateAST(parseResult.ast, variable);
    const simplifiedDerivative = simplifyAST(derivativeAst);

    const derivativeStr = astToHumanString(simplifiedDerivative);

    const derivativeEvaluate = (x: number): number | null => {
      const result = compileExprFromAst(simplifiedDerivative);
      return result.evaluate(x);
    };

    const originalCompiled = compileExpr(processed);
    let confidence = 1;
    if (originalCompiled.success && originalCompiled.compiled) {
      const verification = verifyDerivative(
        originalCompiled.compiled.evaluate,
        derivativeEvaluate
      );
      confidence = verification.confidence;
    }

    const compiled: CompiledExpression = {
      ast: simplifiedDerivative,
      evaluate: derivativeEvaluate,
      toString: () => derivativeStr
    };

    return { success: true, derivative: derivativeStr, compiled, confidence };
  } catch (e) {
    return { success: false, error: (e as Error).message || '计算导函数失败' };
  }
}

function compileExprFromAst(ast: ASTNode): { evaluate: (x: number) => number | null } {
  return {
    evaluate: (x: number): number | null => {
      const result = compileExprFromAstHelper(ast, x);
      return Number.isFinite(result) ? result : null;
    }
  };
}

function compileExprFromAstHelper(node: ASTNode, x: number): number {
  switch (node.type) {
    case 'number': return node.value;
    case 'variable': return node.name === 'x' ? x : NaN;
    case 'constant': return node.value;
    case 'unary': {
      const arg = compileExprFromAstHelper(node.arg, x);
      if (node.op === '-') return -arg;
      if (node.op === '!') return arg === 0 ? 1 : 0;
      return NaN;
    }
    case 'binary': {
      const left = compileExprFromAstHelper(node.left, x);
      const right = compileExprFromAstHelper(node.right, x);
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
      const args = node.args.map(a => compileExprFromAstHelper(a, x));
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
        case 'log':
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
        const cond = compileExprFromAstHelper(branch.condition, x);
        if (cond !== 0) {
          return compileExprFromAstHelper(branch.expr, x);
        }
      }
      return compileExprFromAstHelper(node.elseExpr, x);
    }
  }
}

function astToHumanString(node: ASTNode): string {
  switch (node.type) {
    case 'number': {
      if (Number.isInteger(node.value)) {
        return node.value.toString();
      }
      const rounded = Math.round(node.value * 10000) / 10000;
      return rounded.toString();
    }
    case 'variable':
      return node.name;
    case 'constant':
      return node.name;
    case 'unary':
      if (node.arg.type === 'number' || node.arg.type === 'variable' || node.arg.type === 'constant') {
        return `-${astToHumanString(node.arg)}`;
      }
      return `-(${astToHumanString(node.arg)})`;
    case 'binary': {
      const leftStr = needsParentheses(node, node.left, 'left')
        ? `(${astToHumanString(node.left)})`
        : astToHumanString(node.left);
      const rightStr = needsParentheses(node, node.right, 'right')
        ? `(${astToHumanString(node.right)})`
        : astToHumanString(node.right);

      if (node.op === '*') {
        if (isNumberOne(node.left) || isNumberOne(node.right)) {
          return leftStr + rightStr;
        }
      }

      return `${leftStr} ${node.op} ${rightStr}`;
    }
    case 'function':
      return `${node.name}(${node.args.map(astToHumanString).join(', ')})`;
    case 'piecewise': {
      const parts = node.branches.map(b =>
        `${astToHumanString(b.expr)} 当 ${astToHumanString(b.condition)}`
      ).join('; ');
      const elseStr = node.elseExpr.type === 'number' && isNaN((node.elseExpr as { value: number }).value)
        ? ''
        : `; 否则 ${astToHumanString(node.elseExpr)}`;
      return `分段函数[${parts}${elseStr}]`;
    }
  }
}

function isNumberOne(node: ASTNode): boolean {
  return node.type === 'number' && Math.abs(node.value - 1) < 1e-10;
}

function needsParentheses(parent: { type: string; op?: string }, child: ASTNode, side: 'left' | 'right'): boolean {
  if (child.type !== 'binary') return false;
  if (parent.type !== 'binary') return false;

  const parentOp = parent.op!;
  const childOp = child.op;

  const precedence: Record<string, number> = {
    '||': 1, '&&': 2,
    '<': 3, '>': 3, '<=': 3, '>=': 3, '==': 3, '!=': 3,
    '+': 4, '-': 4,
    '*': 5, '/': 5,
    '^': 6
  };

  const parentPrec = precedence[parentOp] || 0;
  const childPrec = precedence[childOp] || 0;

  if (childPrec < parentPrec) return true;
  if (childPrec > parentPrec) return false;

  if (parentOp === '-' && side === 'right') return true;
  if (parentOp === '/' && side === 'right') return true;
  if (parentOp === '^' && side === 'left') return true;

  return false;
}

export function evaluateFunction(compiled: CompiledExpression, x: number): number | null {
  try {
    return compiled.evaluate(x);
  } catch {
    return null;
  }
}
