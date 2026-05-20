import { Tree, SyntaxNode } from '@lezer/common';
import { classHighlighter, styleTags, tags as t } from '@lezer/highlight';
import type { HighlightToken } from './types';

const javascriptHighlightStyles = styleTags({
  'async function export default class extends implements interface type enum const let var void null undefined true false new this super static get set constructor': t.keyword,
  'if else switch for while do try catch throw return break continue with case default finally': t.controlKeyword,
  'import from as of await yield': t.moduleKeyword,
  'typeof instanceof in delete typeof': t.operatorKeyword,
  'string StringTemplate StringContent TemplateString': t.string,
  'number BigInt': t.number,
  'LineComment BlockComment': t.comment,
  'VariableName PropertyName': t.variableName,
  'Definition': t.definition,
  '( )': t.paren,
  '[ ]': t.squareBracket,
  '{ }': t.brace,
  '.': t.derefOperator,
  ';': t.separator,
  ',': t.separator,
  '=>': t.arrowOperator,
  '++ --': t.updateOperator,
  '** * / % + - << >> >>> < <= > >= == != === !== & ^ | && || ?? ? :': t.operator,
  '= **= *= /= %= += -= <<= >>= >>>= &= ^= |= &&= ||= ??=': t.definitionOperator,
  '! ~': t.prefixOperator,
  'TypeDefinition': t.typeName,
  'ClassName': t.className,
  'Function': t.function(t.variableName),
  'CallExpression/VariableName': t.function(t.variableName),
  'NewExpression/VariableName': t.standard(t.variableName),
  'MemberExpression/PropertyName': t.propertyName,
  'True False': t.bool,
  'Null Undefined': t.null,
  'Regex': t.regexp,
  'Attribute': t.attributeName,
  'Namespace': t.namespace,
  'Label': t.labelName,
});

const tokenClassMap: Record<string, string> = {
  'keyword': 'token-keyword',
  'controlKeyword': 'token-control',
  'moduleKeyword': 'token-module',
  'operatorKeyword': 'token-operator',
  'string': 'token-string',
  'number': 'token-number',
  'comment': 'token-comment',
  'variableName': 'token-variable',
  'definition': 'token-definition',
  'paren': 'token-paren',
  'squareBracket': 'token-bracket',
  'brace': 'token-brace',
  'derefOperator': 'token-operator',
  'separator': 'token-separator',
  'arrowOperator': 'token-arrow',
  'updateOperator': 'token-operator',
  'operator': 'token-operator',
  'definitionOperator': 'token-operator',
  'prefixOperator': 'token-operator',
  'typeName': 'token-type',
  'className': 'token-class',
  'function': 'token-function',
  'bool': 'token-bool',
  'null': 'token-null',
  'regexp': 'token-regex',
  'attributeName': 'token-attribute',
  'namespace': 'token-namespace',
  'labelName': 'token-label',
  'propertyName': 'token-property',
};

export class SyntaxHighlighter {
  private tree: Tree;
  private text: string;
  private tokens: HighlightToken[] = [];

  constructor(tree: Tree, text: string) {
    this.tree = tree;
    this.text = text;
  }

  generateTokens(): HighlightToken[] {
    this.tokens = [];
    this.collectTokens(this.tree.topNode);
    return this.tokens.sort((a, b) => a.from - b.from);
  }

  private collectTokens(node: SyntaxNode): void {
    if (node.type.name !== 'Program' && node.type.name !== '⚠' && node.from < node.to) {
      const tag = this.getTagForNode(node);
      if (tag) {
        this.tokens.push({
          type: node.type.name,
          from: node.from,
          to: node.to,
          className: tokenClassMap[tag] || `token-${tag}`,
        });
      }
    }

    let child = node.firstChild;
    while (child) {
      this.collectTokens(child);
      child = child.nextSibling;
    }
  }

  private getTagForNode(node: SyntaxNode): string | null {
    const name = node.type.name;
    
    if (name.includes('Comment')) return 'comment';
    if (name.includes('String') || name.includes('Template')) return 'string';
    if (name.includes('Number') || name.includes('Int') || name.includes('Float')) return 'number';
    if (name.includes('Boolean') || name === 'True' || name === 'False') return 'bool';
    if (name === 'Null' || name === 'Undefined') return 'null';
    if (name.includes('Regex') || name.includes('RegExp')) return 'regexp';
    
    if (name.includes('Function')) return 'function';
    if (name.includes('Class')) return 'className';
    if (name.includes('Type') || name.includes('Interface')) return 'typeName';
    if (name.includes('Variable') || name.includes('Identifier')) return 'variableName';
    if (name.includes('Property')) return 'propertyName';
    
    const keywords = ['if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 
                      'break', 'continue', 'return', 'try', 'catch', 'finally', 'throw',
                      'function', 'class', 'interface', 'type', 'enum', 'const', 'let',
                      'var', 'new', 'this', 'super', 'async', 'await', 'yield', 'export',
                      'import', 'from', 'default', 'extends', 'implements', 'static',
                      'get', 'set', 'constructor', 'with'];
    
    if (keywords.some(k => name.toLowerCase().includes(k))) return 'keyword';
    
    if (['(', ')', '[', ']', '{', '}'].some(p => name.includes(p))) return 'paren';
    
    if (['+', '-', '*', '/', '%', '=', '==', '===', '!', '!=', '!==',
         '>', '<', '>=', '<=', '&&', '||', '??', '=>', '?', ':'].some(op => name.includes(op))) {
      return 'operator';
    }
    
    return null;
  }

  renderToHTML(): string {
    const tokens = this.generateTokens();
    let html = '';
    let lastPos = 0;

    for (const token of tokens) {
      if (token.from > lastPos) {
        html += this.escapeHtml(this.text.slice(lastPos, token.from));
      }
      
      const content = this.escapeHtml(this.text.slice(token.from, token.to));
      html += `<span class="${token.className}">${content}</span>`;
      lastPos = token.to;
    }

    if (lastPos < this.text.length) {
      html += this.escapeHtml(this.text.slice(lastPos));
    }

    return html;
  }

  renderToLines(): string[] {
    const lines: string[] = [];
    const tokens = this.generateTokens();
    const textLines = this.text.split('\n');
    
    let tokenIndex = 0;
    let currentPos = 0;

    for (let lineIdx = 0; lineIdx < textLines.length; lineIdx++) {
      const lineText = textLines[lineIdx];
      const lineEnd = currentPos + lineText.length;
      let lineHtml = '';
      let linePos = currentPos;

      while (tokenIndex < tokens.length && tokens[tokenIndex].from < lineEnd) {
        const token = tokens[tokenIndex];
        
        if (token.from > linePos) {
          lineHtml += this.escapeHtml(this.text.slice(linePos, Math.min(token.from, lineEnd)));
        }
        
        const tokenStartInLine = Math.max(token.from, currentPos);
        const tokenEndInLine = Math.min(token.to, lineEnd);
        if (tokenStartInLine < tokenEndInLine) {
          const content = this.escapeHtml(this.text.slice(tokenStartInLine, tokenEndInLine));
          lineHtml += `<span class="${token.className}">${content}</span>`;
        }
        
        if (token.to <= lineEnd) {
          tokenIndex++;
        }
        linePos = tokenEndInLine;
      }

      if (linePos < lineEnd) {
        lineHtml += this.escapeHtml(this.text.slice(linePos, lineEnd));
      }

      lines.push(lineHtml);
      currentPos = lineEnd + 1;
    }

    return lines;
  }

  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  getTokenAtPosition(pos: number): HighlightToken | null {
    for (const token of this.tokens) {
      if (pos >= token.from && pos <= token.to) {
        return token;
      }
    }
    return null;
  }

  getTokensInRange(from: number, to: number): HighlightToken[] {
    return this.tokens.filter(t => t.from < to && t.to > from);
  }
}

export const highlightCSS = `
.token-keyword {
  color: #c678dd;
}

.token-control {
  color: #c678dd;
}

.token-module {
  color: #c678dd;
}

.token-operator {
  color: #56b6c2;
}

.token-string {
  color: #98c379;
}

.token-number {
  color: #d19a66;
}

.token-comment {
  color: #5c6370;
  font-style: italic;
}

.token-variable {
  color: #e06c75;
}

.token-definition {
  color: #61afef;
}

.token-paren, .token-bracket, .token-brace {
  color: #abb2bf;
}

.token-separator {
  color: #abb2bf;
}

.token-arrow {
  color: #56b6c2;
}

.token-type {
  color: #e5c07b;
}

.token-class {
  color: #e5c07b;
}

.token-function {
  color: #61afef;
}

.token-bool {
  color: #d19a66;
}

.token-null {
  color: #d19a66;
}

.token-regex {
  color: #e06c75;
}

.token-attribute {
  color: #d19a66;
}

.token-namespace {
  color: #e5c07b;
}

.token-label {
  color: #e06c75;
}

.token-property {
  color: #61afef;
}

.light-theme .token-keyword,
.light-theme .token-control,
.light-theme .token-module {
  color: #a626a4;
}

.light-theme .token-operator {
  color: #0431fa;
}

.light-theme .token-string {
  color: #50a14f;
}

.light-theme .token-number {
  color: #986801;
}

.light-theme .token-comment {
  color: #a0a1a7;
  font-style: italic;
}

.light-theme .token-variable {
  color: #e45649;
}

.light-theme .token-definition {
  color: #4078f2;
}

.light-theme .token-paren,
.light-theme .token-bracket,
.light-theme .token-brace {
  color: #383a42;
}

.light-theme .token-type,
.light-theme .token-class {
  color: #c18401;
}

.light-theme .token-function {
  color: #4078f2;
}

.light-theme .token-bool,
.light-theme .token-null {
  color: #986801;
}

.light-theme .token-property {
  color: #4078f2;
}
`;
