export type TokenType =
  | 'NUMBER'
  | 'IDENT'
  | 'PLUS'
  | 'MINUS'
  | 'STAR'
  | 'SLASH'
  | 'CARET'
  | 'BANG'
  | 'LPAREN'
  | 'RPAREN'
  | 'COMMA'
  | 'EOF';

export interface Token {
  type: TokenType;
  value: string;
  pos: number;
}

export interface LexerError {
  message: string;
  pos: number;
}

const KEYWORDS = new Set([
  'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
  'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
  'log', 'ln', 'log2', 'log10',
  'sqrt', 'cbrt', 'abs', 'exp',
  'floor', 'ceil', 'round', 'sign',
  'min', 'max', 'pow', 'mod',
  'gcd', 'lcm',
  'pi', 'e', 'ans',
]);

const RULES: Array<{ re: RegExp; type: TokenType | null; keyword?: boolean }> = [
  { re: /\s+/y, type: null },
  { re: /(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?/y, type: 'NUMBER' },
  { re: /[A-Za-z_][A-Za-z0-9_]*/y, type: 'IDENT', keyword: true },
  { re: /\+/y, type: 'PLUS' },
  { re: /-/y, type: 'MINUS' },
  { re: /\*/y, type: 'STAR' },
  { re: /\//y, type: 'SLASH' },
  { re: /\^/y, type: 'CARET' },
  { re: /!/y, type: 'BANG' },
  { re: /\(/y, type: 'LPAREN' },
  { re: /\)/y, type: 'RPAREN' },
  { re: /,/y, type: 'COMMA' },
];

export function tokenize(input: string): { tokens: Token[]; error?: LexerError } {
  const tokens: Token[] = [];
  let i = 0;
  while (i < input.length) {
    let matched = false;
    for (const rule of RULES) {
      rule.re.lastIndex = i;
      const m = rule.re.exec(input);
      if (m && m.index === i) {
        if (rule.type) {
          tokens.push({ type: rule.type, value: m[0], pos: i });
        }
        i += m[0].length;
        matched = true;
        break;
      }
    }
    if (!matched) {
      return {
        tokens,
        error: { message: `非法字符 '${input[i]}'`, pos: i },
      };
    }
  }
  tokens.push({ type: 'EOF', value: '', pos: i });
  return { tokens };
}

export function isKeyword(name: string): boolean {
  return KEYWORDS.has(name.toLowerCase());
}
