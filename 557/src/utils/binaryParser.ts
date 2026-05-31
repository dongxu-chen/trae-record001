import type { ASTNode, CompiledExpression } from './recursiveParser';
import { parseExpression, compileExpression, differentiateAST, simplifyAST } from './recursiveParser';
import type { CompiledBinaryFunction } from '../types';

export function parseBinaryExpression(expr: string): { success: boolean; ast?: ASTNode; error?: string } {
  try {
    const result = parseExpression(expr);
    if (!result.success) {
      return result;
    }
    return result;
  } catch (e) {
    return { success: false, error: (e as Error).message };
  }
}

export function compileBinaryExpression(expr: string): { success: boolean; compiled?: CompiledBinaryFunction; error?: string } {
  try {
    const result = compileExpression(expr, ['x', 'y']);
    if (!result.success || !result.compiled) {
      return { success: false, error: result.error };
    }

    const ast = result.compiled.ast;

    const compiled: CompiledBinaryFunction = {
      evaluate: (x: number, y: number): number | null => {
        try {
          return evaluateBinaryAST(ast, x, y);
        } catch {
          return null;
        }
      }
    };

    return { success: true, compiled };
  } catch (e) {
    return { success: false, error: (e as Error).message };
  }
}

function evaluateBinaryAST(node: ASTNode, x: number, y: number): number | null {
  switch (node.type) {
    case 'number':
      return node.value;
    case 'variable':
      if (node.name === 'x') return x;
      if (node.name === 'y') return y;
      return NaN;
    case 'constant':
      return node.value;
    case 'unary': {
      const arg = evaluateBinaryAST(node.arg, x, y);
      if (arg === null) return null;
      if (node.op === '-') return -arg;
      if (node.op === '!') return arg === 0 ? 1 : 0;
      return null;
    }
    case 'binary': {
      const left = evaluateBinaryAST(node.left, x, y);
      const right = evaluateBinaryAST(node.right, x, y);
      if (left === null || right === null) return null;
      switch (node.op) {
        case '+': return left + right;
        case '-': return left - right;
        case '*': return left * right;
        case '/': return right !== 0 ? left / right : null;
        case '^': return Math.pow(left, right);
        default: return null;
      }
    }
    case 'function': {
      const args = node.args.map(a => evaluateBinaryAST(a, x, y));
      if (args.some(a => a === null)) return null;
      const arg = args[0]!;
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
        case 'sqrt': return arg >= 0 ? Math.sqrt(arg) : null;
        case 'log':
        case 'ln': return arg > 0 ? Math.log(arg) : null;
        case 'log10': return arg > 0 ? Math.log10(arg) : null;
        case 'log2': return arg > 0 ? Math.log2(arg) : null;
        case 'exp': return Math.exp(arg);
        case 'abs': return Math.abs(arg);
        case 'ceil': return Math.ceil(arg);
        case 'floor': return Math.floor(arg);
        case 'round': return Math.round(arg);
        case 'sign': return Math.sign(arg);
        default: return null;
      }
    }
    case 'piecewise': {
      for (const branch of node.branches) {
        const cond = evaluateBinaryAST(branch.condition, x, y);
        if (cond !== null && cond !== 0) {
          return evaluateBinaryAST(branch.expr, x, y);
        }
      }
      return evaluateBinaryAST(node.elseExpr, x, y);
    }
  }
}

export function substituteParameter(
  expr: string,
  paramName: string,
  paramValue: number
): string {
  const regex = new RegExp(`\\b${paramName}\\b`, 'g');
  return expr.replace(regex, `(${paramValue})`);
}

export function compileExpressionWithParameter(
  expr: string,
  paramName: string,
  paramValue: number
): { success: boolean; compiled?: CompiledExpression; error?: string } {
  const validateResult = compileExpression(expr, ['x', paramName]);
  if (!validateResult.success) {
    return { success: false, error: validateResult.error };
  }

  const substituted = substituteParameter(expr, paramName, paramValue);
  return compileExpression(substituted, ['x']);
}

export function computeDefiniteIntegral(
  compiled: CompiledExpression,
  lowerBound: number,
  upperBound: number,
  numSteps: number = 10000
): number {
  if (lowerBound > upperBound) {
    return -computeDefiniteIntegral(compiled, upperBound, lowerBound, numSteps);
  }

  const h = (upperBound - lowerBound) / numSteps;
  let sum = 0;

  for (let i = 0; i < numSteps; i++) {
    const x1 = lowerBound + i * h;
    const x2 = lowerBound + (i + 1) * h;
    const y1 = compiled.evaluate(x1);
    const y2 = compiled.evaluate(x2);

    if (y1 !== null && y2 !== null && Number.isFinite(y1) && Number.isFinite(y2)) {
      sum += (y1 + y2) / 2 * h;
    }
  }

  return sum;
}

export function computeDefiniteIntegralAdaptive(
  compiled: CompiledExpression,
  lowerBound: number,
  upperBound: number,
  tolerance: number = 1e-6,
  maxRecursion: number = 20
): number {
  function adaptiveSimpson(
    a: number,
    b: number,
    fa: number | null,
    fb: number | null,
    fc: number | null,
    depth: number
  ): number {
    const c = (a + b) / 2;
    const h = b - a;
    const d = (a + c) / 2;
    const e = (c + b) / 2;

    const fd = compiled.evaluate(d);
    const fe = compiled.evaluate(e);

    if (fa === null || fb === null || fc === null || fd === null || fe === null) {
      return 0;
    }

    const S = (h / 6) * (fa + 4 * fc + fb);
    const S2 = (h / 12) * (fa + 4 * fd + 2 * fc + 4 * fe + fb);

    if (Math.abs(S2 - S) <= 15 * tolerance || depth >= maxRecursion) {
      return S2 + (S2 - S) / 15;
    }

    return adaptiveSimpson(a, c, fa, fc, fd, depth + 1) +
           adaptiveSimpson(c, b, fc, fb, fe, depth + 1);
  }

  if (lowerBound > upperBound) {
    return -adaptiveSimpson(upperBound, lowerBound,
      compiled.evaluate(upperBound),
      compiled.evaluate(lowerBound),
      compiled.evaluate((upperBound + lowerBound) / 2),
      0
    );
  }

  return adaptiveSimpson(lowerBound, upperBound,
    compiled.evaluate(lowerBound),
    compiled.evaluate(upperBound),
    compiled.evaluate((lowerBound + upperBound) / 2),
    0
  );
}

export function generateIntegrationPoints(
  compiled: CompiledExpression,
  lowerBound: number,
  upperBound: number,
  numPoints: number = 200
): { x: number; y: number | null }[] {
  const points: { x: number; y: number | null }[] = [];
  const step = (upperBound - lowerBound) / (numPoints - 1);

  for (let i = 0; i < numPoints; i++) {
    const x = lowerBound + i * step;
    const y = compiled.evaluate(x);
    points.push({ x, y });
  }

  return points;
}

export function validateBinaryExpression(expr: string): { valid: boolean; error?: string } {
  const result = compileExpression(expr, ['x', 'y']);
  return {
    valid: result.success,
    error: result.error
  };
}

export function validateParameterizedExpression(
  expr: string,
  paramName: string
): { valid: boolean; error?: string } {
  const result = parseExpression(expr);
  if (!result.success) {
    return { valid: false, error: result.error };
  }

  const variables = new Set<string>();
  const collectVariables = (node: ASTNode) => {
    if (node.type === 'variable') {
      variables.add(node.name);
    }
    if ('left' in node) collectVariables(node.left as ASTNode);
    if ('right' in node) collectVariables(node.right as ASTNode);
    if ('arg' in node) collectVariables(node.arg as ASTNode);
    if ('args' in node) (node.args as ASTNode[]).forEach(collectVariables);
    if ('branches' in node) {
      (node.branches as { condition: ASTNode; expr: ASTNode }[]).forEach(b => {
        collectVariables(b.condition);
        collectVariables(b.expr);
      });
      collectVariables(node.elseExpr as ASTNode);
    }
  };

  if (result.ast) {
    collectVariables(result.ast);
  }

  const allowedVars = new Set(['x', paramName]);
  for (const v of variables) {
    if (!allowedVars.has(v)) {
      return { valid: false, error: `不支持的变量 "${v}"，参数化函数仅允许使用 "x" 和 "${paramName}"` };
    }
  }

  return { valid: true };
}
