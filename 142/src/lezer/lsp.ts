import { Tree, SyntaxNode } from '@lezer/common';
import { LezerParser } from './parser';
import type { Definition, CompletionItem, Language, Position, Range } from './types';

export class LSPProvider {
  private parser: LezerParser;
  private text: string = '';
  private definitions: Map<string, Definition[]> = new Map();

  constructor(language: Language) {
    this.parser = new LezerParser(language);
  }

  updateText(text: string): void {
    this.text = text;
    this.parser.parse(text);
    this.indexDefinitions();
  }

  private indexDefinitions(): void {
    this.definitions.clear();
    const tree = this.parser.getSyntaxTree();
    if (!tree) return;

    const visitor = (node: SyntaxNode, depth: number): boolean => {
      const type = node.type.name;
      const nameNode = node.getChild('VariableName') || 
                       node.getChild('PropertyName') ||
                       node.getChild('Definition');
      
      if (!nameNode) return true;

      const name = this.text.slice(nameNode.from, nameNode.to).trim();
      if (!name) return true;

      let defType: Definition['type'] = 'variable';
      
      if (type.includes('Function') || type.includes('Method')) {
        defType = 'function';
      } else if (type.includes('Class')) {
        defType = 'class';
      } else if (type.includes('Interface') || type.includes('Type')) {
        defType = 'interface';
      } else if (type.includes('Method')) {
        defType = 'method';
      }

      const definition: Definition = {
        name,
        type: defType,
        from: node.from,
        to: node.to,
        selectionStart: nameNode.from,
        selectionEnd: nameNode.to,
      };

      if (!this.definitions.has(name)) {
        this.definitions.set(name, []);
      }
      this.definitions.get(name)!.push(definition);

      return true;
    };

    const walker = (node: SyntaxNode, depth: number): void => {
      if (visitor(node, depth) !== false) {
        let child = node.firstChild;
        while (child) {
          walker(child, depth + 1);
          child = child.nextSibling;
        }
      }
    };

    walker(tree.topNode, 0);
  }

  getDefinition(position: number): Definition | null {
    const node = this.parser.getNodeAtPosition(position);
    if (!node) return null;

    const name = this.text.slice(node.from, node.to).trim();
    if (!name) return null;

    const defs = this.definitions.get(name);
    if (defs && defs.length > 0) {
      return defs[0];
    }

    return null;
  }

  getAllDefinitions(): Definition[] {
    return Array.from(this.definitions.values()).flat();
  }

  getCompletions(position: number, triggerCharacter?: string): CompletionItem[] {
    const completions: CompletionItem[] = [];
    const prefix = this.getWordPrefix(position);

    const keywords: CompletionItem[] = [
      { label: 'if', kind: 'keyword', detail: 'Conditional statement' },
      { label: 'else', kind: 'keyword', detail: 'Else clause' },
      { label: 'for', kind: 'keyword', detail: 'For loop' },
      { label: 'while', kind: 'keyword', detail: 'While loop' },
      { label: 'do', kind: 'keyword', detail: 'Do-while loop' },
      { label: 'switch', kind: 'keyword', detail: 'Switch statement' },
      { label: 'case', kind: 'keyword', detail: 'Case clause' },
      { label: 'default', kind: 'keyword', detail: 'Default clause' },
      { label: 'break', kind: 'keyword', detail: 'Break statement' },
      { label: 'continue', kind: 'keyword', detail: 'Continue statement' },
      { label: 'return', kind: 'keyword', detail: 'Return statement' },
      { label: 'try', kind: 'keyword', detail: 'Try block' },
      { label: 'catch', kind: 'keyword', detail: 'Catch clause' },
      { label: 'finally', kind: 'keyword', detail: 'Finally clause' },
      { label: 'throw', kind: 'keyword', detail: 'Throw exception' },
      { label: 'function', kind: 'keyword', detail: 'Function declaration' },
      { label: 'class', kind: 'keyword', detail: 'Class declaration' },
      { label: 'interface', kind: 'keyword', detail: 'Interface declaration' },
      { label: 'type', kind: 'keyword', detail: 'Type alias' },
      { label: 'enum', kind: 'keyword', detail: 'Enumeration' },
      { label: 'const', kind: 'keyword', detail: 'Constant declaration' },
      { label: 'let', kind: 'keyword', detail: 'Let declaration' },
      { label: 'var', kind: 'keyword', detail: 'Var declaration' },
      { label: 'new', kind: 'keyword', detail: 'New operator' },
      { label: 'this', kind: 'keyword', detail: 'This keyword' },
      { label: 'super', kind: 'keyword', detail: 'Super keyword' },
      { label: 'async', kind: 'keyword', detail: 'Async function' },
      { label: 'await', kind: 'keyword', detail: 'Await expression' },
      { label: 'export', kind: 'keyword', detail: 'Export declaration' },
      { label: 'import', kind: 'keyword', detail: 'Import declaration' },
      { label: 'from', kind: 'keyword', detail: 'From clause' },
      { label: 'extends', kind: 'keyword', detail: 'Extends clause' },
      { label: 'implements', kind: 'keyword', detail: 'Implements clause' },
      { label: 'static', kind: 'keyword', detail: 'Static modifier' },
      { label: 'private', kind: 'keyword', detail: 'Private modifier' },
      { label: 'protected', kind: 'keyword', detail: 'Protected modifier' },
      { label: 'public', kind: 'keyword', detail: 'Public modifier' },
      { label: 'readonly', kind: 'keyword', detail: 'Readonly modifier' },
      { label: 'constructor', kind: 'keyword', detail: 'Constructor method' },
      { label: 'get', kind: 'keyword', detail: 'Getter method' },
      { label: 'set', kind: 'keyword', detail: 'Setter method' },
      { label: 'return', kind: 'keyword', detail: 'Return statement' },
      { label: 'void', kind: 'keyword', detail: 'Void type' },
      { label: 'null', kind: 'keyword', detail: 'Null value' },
      { label: 'undefined', kind: 'keyword', detail: 'Undefined value' },
      { label: 'true', kind: 'keyword', detail: 'Boolean true' },
      { label: 'false', kind: 'keyword', detail: 'Boolean false' },
      { label: 'typeof', kind: 'keyword', detail: 'Typeof operator' },
      { label: 'instanceof', kind: 'keyword', detail: 'Instanceof operator' },
      { label: 'in', kind: 'keyword', detail: 'In operator' },
      { label: 'delete', kind: 'keyword', detail: 'Delete operator' },
      { label: 'yield', kind: 'keyword', detail: 'Yield operator' },
    ];

    const snippets: CompletionItem[] = [
      {
        label: 'if',
        kind: 'keyword',
        detail: 'if statement',
        documentation: 'if (condition) { }',
      },
      {
        label: 'ifelse',
        kind: 'keyword',
        detail: 'if-else statement',
        documentation: 'if (condition) { } else { }',
      },
      {
        label: 'for',
        kind: 'keyword',
        detail: 'for loop',
        documentation: 'for (let i = 0; i < length; i++) { }',
      },
      {
        label: 'foreach',
        kind: 'keyword',
        detail: 'for-each loop',
        documentation: 'for (const item of array) { }',
      },
      {
        label: 'fn',
        kind: 'function',
        detail: 'Function declaration',
        documentation: 'function name(params) { }',
      },
      {
        label: 'afn',
        kind: 'function',
        detail: 'Async function declaration',
        documentation: 'async function name(params) { }',
      },
      {
        label: 'cl',
        kind: 'class',
        detail: 'Class declaration',
        documentation: 'class Name { }',
      },
      {
        label: 'trycatch',
        kind: 'keyword',
        detail: 'Try-catch block',
        documentation: 'try { } catch (error) { }',
      },
    ];

    for (const def of this.getAllDefinitions()) {
      completions.push({
        label: def.name,
        kind: def.type,
        detail: `${def.type} ${def.name}`,
      });
    }

    if (prefix) {
      const lowerPrefix = prefix.toLowerCase();
      const filteredKeywords = keywords.filter(k => 
        k.label.toLowerCase().startsWith(lowerPrefix)
      );
      const filteredSnippets = snippets.filter(s => 
        s.label.toLowerCase().startsWith(lowerPrefix)
      );
      const filteredDefs = completions.filter(c => 
        c.label.toLowerCase().startsWith(lowerPrefix)
      );
      return [...filteredKeywords, ...filteredSnippets, ...filteredDefs].slice(0, 50);
    }

    return [...keywords, ...snippets, ...completions].slice(0, 100);
  }

  private getWordPrefix(position: number): string {
    let start = position;
    while (start > 0 && /[\w$]/.test(this.text.charAt(start - 1))) {
      start--;
    }
    return this.text.slice(start, position);
  }

  findReferences(position: number): Definition[] {
    const def = this.getDefinition(position);
    if (!def) return [];

    const results: Definition[] = [];
    const word = this.getWordAtPosition(position);
    if (!word) return [];

    const regex = new RegExp(`\\b${word}\\b`, 'g');
    let match: RegExpExecArray | null;

    while ((match = regex.exec(this.text)) !== null) {
      results.push({
        name: word,
        type: 'variable',
        from: match.index,
        to: match.index + word.length,
        selectionStart: match.index,
        selectionEnd: match.index + word.length,
      });
    }

    return results;
  }

  private getWordAtPosition(position: number): string | null {
    let start = position;
    let end = position;

    while (start > 0 && /[\w$]/.test(this.text.charAt(start - 1))) {
      start--;
    }
    while (end < this.text.length && /[\w$]/.test(this.text.charAt(end))) {
      end++;
    }

    return start < end ? this.text.slice(start, end) : null;
  }

  getSymbolOutline(): Definition[] {
    return this.getAllDefinitions().filter(d => 
      ['function', 'class', 'interface', 'type'].includes(d.type)
    );
  }

  getParser(): LezerParser {
    return this.parser;
  }

  offsetToPosition(offset: number): Position {
    const lines = this.text.slice(0, offset).split('\n');
    return {
      line: lines.length - 1,
      character: lines[lines.length - 1].length,
    };
  }

  positionToOffset(position: Position): number {
    const lines = this.text.split('\n');
    let offset = 0;
    for (let i = 0; i < position.line && i < lines.length; i++) {
      offset += lines[i].length + 1;
    }
    return offset + Math.min(position.character, lines[position.line]?.length || 0);
  }
}

export class CompletionContext {
  private provider: LSPProvider;
  private position: number;
  private triggerCharacter?: string;

  constructor(provider: LSPProvider, position: number, triggerCharacter?: string) {
    this.provider = provider;
    this.position = position;
    this.triggerCharacter = triggerCharacter;
  }

  getCompletions(): CompletionItem[] {
    return this.provider.getCompletions(this.position, this.triggerCharacter);
  }
}
