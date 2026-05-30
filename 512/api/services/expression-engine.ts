import { Parser } from 'expr-eval';
import type { ThresholdRule, AlertCondition } from '../types.js';

const parser = new Parser();

type CompiledExpr = {
  evaluate: (vars: Record<string, number>) => number;
};

const compiledCache = new Map<string, { expr: CompiledExpr; expression: string; conditionsHash: string }>();

function hashConditions(conditions: AlertCondition[]): string {
  return conditions.map(c => `${c.field}|${c.operator}|${c.value}|${c.logic || ''}`).join('||');
}

export function buildExpression(conditions: AlertCondition[]): string {
  if (conditions.length === 0) return 'false';
  const parts: string[] = [];
  for (let i = 0; i < conditions.length; i++) {
    const c = conditions[i];
    const part = `value ${c.operator} ${c.value}`;
    if (i === 0) {
      parts.push(part);
    } else {
      const logic = c.logic || 'AND';
      parts.push(`${logic.toLowerCase()} ${part}`);
    }
  }
  return parts.join(' ');
}

function compileExpression(expression: string): CompiledExpr | null {
  try {
    return parser.parse(expression);
  } catch {
    try {
      const jsExpr = expression.replace(/and/gi, '&&').replace(/or/gi, '||');
      const fn = new Function('value', `return ${jsExpr}`) as (value: number) => number;
      return { evaluate: ({ value }) => fn(value) };
    } catch {
      return null;
    }
  }
}

export function precompileRule(rule: ThresholdRule): void {
  const hash = hashConditions(rule.conditions);
  const cached = compiledCache.get(rule.id);
  if (cached && cached.conditionsHash === hash) return;
  const expression = buildExpression(rule.conditions);
  const compiled = compileExpression(expression);
  if (compiled) {
    compiledCache.set(rule.id, { expr: compiled, expression, conditionsHash: hash });
  }
}

export function invalidateRuleCache(ruleId: string): void {
  compiledCache.delete(ruleId);
}

export function clearCache(): void {
  compiledCache.clear();
}

export function evaluateRule(
  rule: ThresholdRule,
  metricValue: number,
): { triggered: boolean; expression: string; triggerValue: number } {
  let cached = compiledCache.get(rule.id);
  const hash = hashConditions(rule.conditions);
  if (!cached || cached.conditionsHash !== hash) {
    const expression = buildExpression(rule.conditions);
    const compiled = compileExpression(expression);
    if (compiled) {
      cached = { expr: compiled, expression, conditionsHash: hash };
      compiledCache.set(rule.id, cached);
    } else {
      return { triggered: false, expression, triggerValue: metricValue };
    }
  }
  try {
    const result = cached.expr.evaluate({ value: metricValue });
    return {
      triggered: Boolean(result),
      expression: cached.expression,
      triggerValue: metricValue,
    };
  } catch {
    return {
      triggered: false,
      expression: cached.expression,
      triggerValue: metricValue,
    };
  }
}
