import { Token, TokenType, tokenize } from './lexer';

export type NodeType =
  | 'Number'
  | 'Identifier'
  | 'Unary'
  | 'Binary'
  | 'Call'
  | 'Factorial';

export interface ASTNode {
  type: NodeType;
  [key: string]: unknown;
}

export interface NumberNode extends ASTNode {
  type: 'Number';
  value: string;
}

export interface IdentifierNode extends ASTNode {
  type: 'Identifier';
  name: string;
}

export interface UnaryNode extends ASTNode {
  type: 'Unary';
  op: '+' | '-';
  operand: ASTNode;
}

export interface BinaryNode extends ASTNode {
  type: 'Binary';
  op: '+' | '-' | '*' | '/' | '^';
  left: ASTNode;
  right: ASTNode;
}

export interface CallNode extends ASTNode {
  type: 'Call';
  name: string;
  args: ASTNode[];
}

export interface FactorialNode extends ASTNode {
  type: 'Factorial';
  operand: ASTNode;
}

export interface ParseError {
  message: string;
  pos: number;
}

export interface ParseContext {
  knownFunctions?: Set<string>;
  knownIdentifiers?: Set<string>;
  allowFreeVariables?: boolean;
}

const BUILTIN_FUNCTIONS = new Set([
  'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
  'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
  'log', 'ln', 'log2', 'log10',
  'sqrt', 'cbrt', 'abs', 'exp',
  'floor', 'ceil', 'round', 'sign',
  'min', 'max', 'pow', 'mod',
  'gcd', 'lcm',
]);

const BUILTIN_CONSTANTS = new Set(['pi', 'e', 'ans']);

function isBuiltinFunction(name: string): boolean {
  return BUILTIN_FUNCTIONS.has(name);
}

function isBuiltinConstant(name: string): boolean {
  return BUILTIN_CONSTANTS.has(name);
}

export function getAllBuiltinFunctions(): string[] {
  return Array.from(BUILTIN_FUNCTIONS);
}

class Parser {
  private tokens: Token[];
  private pos = 0;
  private context: ParseContext;

  constructor(tokens: Token[], context: ParseContext = {}) {
    this.tokens = tokens;
    this.context = context;
  }

  private peek(): Token {
    return this.tokens[this.pos];
  }

  private advance(): Token {
    const t = this.tokens[this.pos];
    this.pos++;
    return t;
  }

  private expect(type: TokenType): Token {
    const t = this.peek();
    if (t.type !== type) {
      throw {
        message: `期望 ${type}，实际 '${t.value || t.type}'`,
        pos: t.pos,
      } as ParseError;
    }
    return this.advance();
  }

  private isKnownFunction(name: string): boolean {
    if (isBuiltinFunction(name)) return true;
    if (this.context.knownFunctions?.has(name)) return true;
    return false;
  }

  private isKnownIdentifier(name: string): boolean {
    if (isBuiltinConstant(name)) return true;
    if (isBuiltinFunction(name)) return true;
    if (this.context.knownFunctions?.has(name)) return true;
    if (this.context.knownIdentifiers?.has(name)) return true;
    if (this.context.allowFreeVariables) return true;
    return false;
  }

  parse(): ASTNode {
    const node = this.parseExpression();
    if (this.peek().type !== 'EOF') {
      throw {
        message: `意外的 token '${this.peek().value}'`,
        pos: this.peek().pos,
      } as ParseError;
    }
    return node;
  }

  private parseExpression(): ASTNode {
    return this.parseAdditive();
  }

  private parseAdditive(): ASTNode {
    let left = this.parseMultiplicative();
    while (this.peek().type === 'PLUS' || this.peek().type === 'MINUS') {
      const op = this.advance().type === 'PLUS' ? '+' : '-';
      const right = this.parseMultiplicative();
      left = { type: 'Binary', op, left, right } as BinaryNode;
    }
    return left;
  }

  private parseMultiplicative(): ASTNode {
    let left = this.parseUnary();
    while (this.peek().type === 'STAR' || this.peek().type === 'SLASH') {
      const op = this.advance().type === 'STAR' ? '*' : '/';
      const right = this.parseUnary();
      left = { type: 'Binary', op, left, right } as BinaryNode;
    }
    return left;
  }

  private parseUnary(): ASTNode {
    if (this.peek().type === 'PLUS') {
      this.advance();
      return { type: 'Unary', op: '+', operand: this.parseUnary() } as UnaryNode;
    }
    if (this.peek().type === 'MINUS') {
      this.advance();
      return { type: 'Unary', op: '-', operand: this.parseUnary() } as UnaryNode;
    }
    return this.parsePower();
  }

  private parsePower(): ASTNode {
    const base = this.parsePostfix();
    if (this.peek().type === 'CARET') {
      this.advance();
      const exponent = this.parseUnary();
      return { type: 'Binary', op: '^', left: base, right: exponent } as BinaryNode;
    }
    return base;
  }

  private parsePostfix(): ASTNode {
    let node = this.parsePrimary();
    while (this.peek().type === 'BANG') {
      this.advance();
      node = { type: 'Factorial', operand: node } as FactorialNode;
    }
    return node;
  }

  private parsePrimary(): ASTNode {
    const t = this.peek();
    if (t.type === 'NUMBER') {
      this.advance();
      return { type: 'Number', value: t.value } as NumberNode;
    }
    if (t.type === 'LPAREN') {
      this.advance();
      const node = this.parseExpression();
      this.expect('RPAREN');
      return node;
    }
    if (t.type === 'IDENT') {
      this.advance();
      const name = t.value.toLowerCase();
      if (!this.isKnownIdentifier(name) && !this.isKnownFunction(name)) {
        throw {
          message: `未知标识符 '${t.value}'`,
          pos: t.pos,
        } as ParseError;
      }
      if (this.peek().type === 'LPAREN') {
        if (!this.isKnownFunction(name)) {
          throw {
            message: `'${t.value}' 不是函数`,
            pos: t.pos,
          } as ParseError;
        }
        this.advance();
        const args: ASTNode[] = [];
        if (this.peek().type !== 'RPAREN') {
          args.push(this.parseExpression());
          while (this.peek().type === 'COMMA') {
            this.advance();
            args.push(this.parseExpression());
          }
        }
        this.expect('RPAREN');
        return { type: 'Call', name, args } as CallNode;
      }
      if (this.isKnownFunction(name)) {
        throw {
          message: `函数 '${t.value}' 需要括号`,
          pos: t.pos,
        } as ParseError;
      }
      return { type: 'Identifier', name } as IdentifierNode;
    }
    throw {
      message: `意外的 token '${t.value || t.type}'`,
      pos: t.pos,
    } as ParseError;
  }
}

export function parse(
  input: string,
  context: ParseContext = {},
): { ast?: ASTNode; error?: ParseError } {
  const { tokens, error } = tokenize(input);
  if (error) {
    return { error };
  }
  try {
    const parser = new Parser(tokens, context);
    return { ast: parser.parse() };
  } catch (e) {
    return { error: e as ParseError };
  }
}
