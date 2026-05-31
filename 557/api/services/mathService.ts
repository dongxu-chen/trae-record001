import {
  parseExpression,
  compileExpression,
  differentiateAST,
  simplifyAST,
  type CompiledExpression,
  type ASTNode
} from '../utils/recursiveParser.js';

export function validateExpression(expression: string): { valid: boolean; error?: string } {
  try {
    const result = parseExpression(expression);
    if (!result.success) {
      return { valid: false, error: result.error };
    }
    return { valid: true };
  } catch (e) {
    return { valid: false, error: (e as Error).message };
  }
}

export function computeDerivative(
  expression: string,
  variable: string = 'x'
): { success: boolean; derivative?: string; error?: string; confidence?: number } {
  try {
    const parseResult = parseExpression(expression);
    if (!parseResult.success || !parseResult.ast) {
      return { success: false, error: parseResult.error };
    }

    const derivativeAst = differentiateAST(parseResult.ast, variable);
    const simplifiedDerivative = simplifyAST(derivativeAst);

    const derivativeStr = astToHumanString(simplifiedDerivative);

    const originalCompiled = compileExpression(expression);
    let confidence = 1;
    if (originalCompiled.success && originalCompiled.compiled) {
      const derivativeEvaluate = compileFromAST(simplifiedDerivative);
      confidence = calculateConfidence(
        originalCompiled.compiled.evaluate,
        derivativeEvaluate
      );
    }

    return { success: true, derivative: derivativeStr, confidence };
  } catch (e) {
    return { success: false, error: (e as Error).message };
  }
}

export function evaluateExpression(
  expression: string,
  xValues: number[]
): { success: boolean; yValues?: (number | null)[]; error?: string } {
  try {
    const result = compileExpression(expression);
    if (!result.success || !result.compiled) {
      return { success: false, error: result.error };
    }

    const yValues = xValues.map(x => result.compiled!.evaluate(x));
    return { success: true, yValues };
  } catch (e) {
    return { success: false, error: (e as Error).message };
  }
}

function compileFromAST(ast: ASTNode): (x: number) => number | null {
  return (x: number): number | null => {
    const result = evaluateAST(ast, x);
    return Number.isFinite(result) ? result : null;
  };
}

function evaluateAST(node: ASTNode, x: number): number {
  switch (node.type) {
    case 'number': return node.value;
    case 'variable': return node.name === 'x' ? x : NaN;
    case 'constant': return node.value;
    case 'unary': {
      const arg = evaluateAST(node.arg, x);
      if (node.op === '-') return -arg;
      if (node.op === '!') return arg === 0 ? 1 : 0;
      return NaN;
    }
    case 'binary': {
      const left = evaluateAST(node.left, x);
      const right = evaluateAST(node.right, x);
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
      const args = node.args.map(a => evaluateAST(a, x));
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
        const cond = evaluateAST(branch.condition, x);
        if (cond !== 0) {
          return evaluateAST(branch.expr, x);
        }
      }
      return evaluateAST(node.elseExpr, x);
    }
  }
}

function numericalDerivative(
  evaluate: (x: number) => number | null,
  x: number,
  h: number = 1e-5
): number | null {
  const y1 = evaluate(x + h);
  const y2 = evaluate(x - h);
  if (y1 === null || y2 === null) return null;
  return (y1 - y2) / (2 * h);
}

function calculateConfidence(
  originalEvaluate: (x: number) => number | null,
  derivativeEvaluate: (x: number) => number | null,
  testPoints: number[] = [-2, -1, 0, 1, 2, 0.5, -0.5]
): number {
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

  return totalCount > 0 ? validCount / totalCount : 1;
}

function astToHumanString(node: ASTNode): string {
  switch (node.type) {
    case 'number': {
      if (Number.isInteger(node.value)) return node.value.toString();
      const rounded = Math.round(node.value * 10000) / 10000;
      return rounded.toString();
    }
    case 'variable': return node.name;
    case 'constant': return node.name;
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
