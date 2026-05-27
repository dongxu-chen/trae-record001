import Decimal from 'decimal.js';
import { ASTNode, NumberNode, IdentifierNode, UnaryNode, BinaryNode, CallNode, FactorialNode, parse } from './parser';

Decimal.set({ precision: 40, toExpPos: 1e9, toExpNeg: -1e9 });

export interface UserFunction {
  name: string;
  params: string[];
  expression: string;
}

export interface EvaluateOptions {
  angleMode: 'deg' | 'rad';
  ans?: string;
  variables?: Record<string, string | number | Decimal>;
  userFunctions?: UserFunction[];
}

const DEG_TO_RAD = Decimal.acos(-1).div(180);
const RAD_TO_DEG = new Decimal(180).div(Decimal.acos(-1));

function factorial(n: Decimal): Decimal {
  if (!n.isInteger() || n.lt(0)) {
    throw new Error('阶乘仅适用于非负整数');
  }
  if (n.gt(170)) {
    throw new Error('阶乘数值过大');
  }
  const num = n.toNumber();
  let result = new Decimal(1);
  for (let i = 2; i <= num; i++) {
    result = result.mul(i);
  }
  return result;
}

function toDecimal(val: string | number | Decimal): Decimal {
  return new Decimal(val);
}

function gcd(a: Decimal, b: Decimal): Decimal {
  a = a.abs();
  b = b.abs();
  while (!b.isZero()) {
    const t = b;
    b = a.mod(b);
    a = t;
  }
  return a;
}

function callBuiltinFunction(name: string, args: Decimal[], options: EvaluateOptions): Decimal {
  const angle = options.angleMode;
  switch (name) {
    case 'sin':
      return angle === 'deg' ? Decimal.sin(args[0].mul(DEG_TO_RAD)) : Decimal.sin(args[0]);
    case 'cos':
      return angle === 'deg' ? Decimal.cos(args[0].mul(DEG_TO_RAD)) : Decimal.cos(args[0]);
    case 'tan':
      return angle === 'deg' ? Decimal.tan(args[0].mul(DEG_TO_RAD)) : Decimal.tan(args[0]);
    case 'asin':
      return angle === 'deg' ? Decimal.asin(args[0]).mul(RAD_TO_DEG) : Decimal.asin(args[0]);
    case 'acos':
      return angle === 'deg' ? Decimal.acos(args[0]).mul(RAD_TO_DEG) : Decimal.acos(args[0]);
    case 'atan':
      return angle === 'deg' ? Decimal.atan(args[0]).mul(RAD_TO_DEG) : Decimal.atan(args[0]);
    case 'sinh':
      return Decimal.sinh(args[0]);
    case 'cosh':
      return Decimal.cosh(args[0]);
    case 'tanh':
      return Decimal.tanh(args[0]);
    case 'asinh':
      return Decimal.asinh(args[0]);
    case 'acosh':
      return Decimal.acosh(args[0]);
    case 'atanh':
      return Decimal.atanh(args[0]);
    case 'log':
      return Decimal.log10(args[0]);
    case 'ln':
    case 'log2':
      return name === 'log2' ? Decimal.log2(args[0]) : Decimal.ln(args[0]);
    case 'log10':
      return Decimal.log10(args[0]);
    case 'sqrt':
      return Decimal.sqrt(args[0]);
    case 'cbrt':
      return args[0].cbrt();
    case 'abs':
      return Decimal.abs(args[0]);
    case 'exp':
      return Decimal.exp(args[0]);
    case 'floor':
      return Decimal.floor(args[0]);
    case 'ceil':
      return Decimal.ceil(args[0]);
    case 'round':
      return Decimal.round(args[0]);
    case 'sign':
      return args[0].isNeg() ? new Decimal(-1) : args[0].isZero() ? new Decimal(0) : new Decimal(1);
    case 'min':
      return args.reduce((a, b) => Decimal.min(a, b));
    case 'max':
      return args.reduce((a, b) => Decimal.max(a, b));
    case 'pow':
      return Decimal.pow(args[0], args[1]);
    case 'mod':
      return args[0].mod(args[1]);
    case 'gcd':
      return gcd(args[0], args[1]);
    case 'lcm': {
      const g = gcd(args[0], args[1]);
      return args[0].abs().mul(args[1].abs()).div(g);
    }
    default:
      throw new Error(`未知内置函数: ${name}`);
  }
}

const BUILTIN_NAMES = new Set([
  'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
  'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
  'log', 'ln', 'log2', 'log10',
  'sqrt', 'cbrt', 'abs', 'exp',
  'floor', 'ceil', 'round', 'sign',
  'min', 'max', 'pow', 'mod',
  'gcd', 'lcm',
]);

function isBuiltinFunction(name: string): boolean {
  return BUILTIN_NAMES.has(name);
}

function evalNode(
  node: ASTNode,
  options: EvaluateOptions,
  localVars: Record<string, Decimal> = {},
): Decimal {
  switch (node.type) {
    case 'Number': {
      const n = node as NumberNode;
      return toDecimal(n.value);
    }
    case 'Identifier': {
      const ident = node as IdentifierNode;
      if (ident.name === 'pi') return Decimal.acos(-1);
      if (ident.name === 'e') return Decimal.exp(1);
      if (ident.name === 'ans') return toDecimal(options.ans ?? '0');
      if (localVars[ident.name] !== undefined) {
        return localVars[ident.name];
      }
      if (options.variables?.[ident.name] !== undefined) {
        return toDecimal(options.variables[ident.name]);
      }
      throw new Error(`未知变量: ${ident.name}`);
    }
    case 'Unary': {
      const u = node as UnaryNode;
      const operand = evalNode(u.operand, options, localVars);
      return u.op === '-' ? operand.neg() : operand;
    }
    case 'Binary': {
      const b = node as BinaryNode;
      const left = evalNode(b.left, options, localVars);
      const right = evalNode(b.right, options, localVars);
      switch (b.op) {
        case '+': return left.add(right);
        case '-': return left.sub(right);
        case '*': return left.mul(right);
        case '/':
          if (right.isZero()) throw new Error('除数不能为零');
          return left.div(right);
        case '^': return left.pow(right);
        default: throw new Error(`未知运算符: ${b.op}`);
      }
    }
    case 'Call': {
      const c = node as CallNode;
      const evaluatedArgs = c.args.map((a) => evalNode(a, options, localVars));
      if (isBuiltinFunction(c.name)) {
        return callBuiltinFunction(c.name, evaluatedArgs, options);
      }
      const userFn = options.userFunctions?.find((f) => f.name === c.name);
      if (userFn) {
        if (evaluatedArgs.length !== userFn.params.length) {
          throw new Error(`函数 '${c.name}' 需要 ${userFn.params.length} 个参数，实际 ${evaluatedArgs.length}`);
        }
        const fnLocalVars: Record<string, Decimal> = {};
        userFn.params.forEach((p, i) => {
          fnLocalVars[p] = evaluatedArgs[i];
        });
        const { ast, error } = parse(userFn.expression);
        if (error || !ast) {
          throw new Error(`函数 '${c.name}' 表达式解析失败: ${error?.message}`);
        }
        return evalNode(ast, options, fnLocalVars);
      }
      throw new Error(`未知函数: ${c.name}`);
    }
    case 'Factorial': {
      const f = node as FactorialNode;
      const operand = evalNode(f.operand, options, localVars);
      return factorial(operand);
    }
    default:
      throw new Error('未知 AST 节点类型');
  }
}

function formatResult(d: Decimal): string {
  if (d.isNaN()) return 'NaN';
  if (!d.isFinite()) return d.isNeg() ? '-Infinity' : 'Infinity';
  const s = d.toString();
  if (s.includes('.')) {
    return s.replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
  }
  return s;
}

export function evaluate(
  node: ASTNode,
  options: EvaluateOptions = { angleMode: 'rad' },
): string {
  const result = evalNode(node, options);
  return formatResult(result);
}

export function evaluateToDecimal(
  node: ASTNode,
  options: EvaluateOptions = { angleMode: 'rad' },
  localVars: Record<string, Decimal> = {},
): Decimal {
  return evalNode(node, options, localVars);
}
