import * as math from 'mathjs';
import { validateExpression, parseAndCompile, computeDerivative, evaluateFunction, preprocessExpression } from '../utils/expressionParser';

export const validateMathExpression = async (expression: string) => {
  return validateExpression(expression);
};

export const compileExpression = async (expression: string) => {
  return parseAndCompile(expression);
};

export const calculateDerivative = async (expression: string, variable: string = 'x') => {
  return computeDerivative(expression, variable);
};

export const evaluateAtPoint = (compiled: any, x: number): number | null => {
  return evaluateFunction(compiled, x);
};

export const evaluateRange = (
  compiled: any,
  xMin: number,
  xMax: number,
  numPoints: number
): { x: number; y: number | null }[] => {
  const points: { x: number; y: number | null }[] = [];
  const step = (xMax - xMin) / (numPoints - 1);
  
  for (let i = 0; i < numPoints; i++) {
    const x = xMin + i * step;
    const y = evaluateFunction(compiled, x);
    points.push({ x, y });
  }
  
  return points;
};

export const evaluateArray = (compiled: any, xValues: number[]): number[] => {
  return xValues.map(x => {
    const y = evaluateFunction(compiled, x);
    return y ?? NaN;
  });
};

export const simplifyExpression = (expression: string): string => {
  try {
    const processed = preprocessExpression(expression);
    const simplified = math.simplify(processed);
    return simplified.toString();
  } catch {
    return expression;
  }
};
