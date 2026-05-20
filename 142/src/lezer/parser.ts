import { LRParser } from '@lezer/lr';
import { Tree, SyntaxNode, NodeType, Input, TreeFragment } from '@lezer/common';
import { parser as javascriptParser } from '@lezer/javascript';
import { parser as pythonParser } from '@lezer/python';
import { parser as cssParser } from '@lezer/css';
import { parser as jsonParser } from '@lezer/json';
import type { Language, ParseResult, IncrementalUpdate, SyntaxNodeInfo } from './types';

export class LezerParser {
  private parser: LRParser;
  private language: Language;
  private lastTree: Tree | null = null;
  private lastText: string = '';

  constructor(language: Language) {
    this.language = language;
    this.parser = this.getParserForLanguage(language);
  }

  private getParserForLanguage(lang: Language): LRParser {
    switch (lang) {
      case 'javascript':
      case 'typescript':
        return javascriptParser.configure({ dialect: 'ts' });
      case 'python':
        return pythonParser;
      case 'css':
        return cssParser;
      case 'json':
        return jsonParser;
      case 'java':
        return javascriptParser;
      case 'rust':
        return javascriptParser;
      default:
        return javascriptParser;
    }
  }

  parse(text: string): ParseResult {
    const startTime = performance.now();
    const tree = this.parser.parse(text);
    const duration = performance.now() - startTime;

    this.lastTree = tree;
    this.lastText = text;

    let nodeCount = 0;
    tree.iterate({ enter: () => { nodeCount++; }});

    return { tree, duration, nodeCount };
  }

  parseIncremental(text: string, changes: { from: number; to: number; insert: string }[]): ParseResult {
    if (!this.lastTree || changes.length === 0) {
      return this.parse(text);
    }

    const startTime = performance.now();

    let fragments = [TreeFragment.addTree(this.lastTree)];
    for (const change of changes) {
      fragments = TreeFragment.applyChanges(fragments[0], [change]);
    }

    const tree = this.parser.parse(text, fragments[0]);
    const duration = performance.now() - startTime;

    this.lastTree = tree;
    this.lastText = text;

    let nodeCount = 0;
    tree.iterate({ enter: () => { nodeCount++; }});

    return { tree, duration, nodeCount };
  }

  getSyntaxTree(): Tree | null {
    return this.lastTree;
  }

  getNodeAtPosition(pos: number): SyntaxNode | null {
    if (!this.lastTree) return null;
    return this.lastTree.resolve(pos, 1);
  }

  getNodeInfo(node: SyntaxNode, text: string): SyntaxNodeInfo {
    const children: SyntaxNodeInfo[] = [];
    let child = node.firstChild;
    while (child) {
      children.push(this.getNodeInfo(child, text));
      child = child.nextSibling;
    }

    return {
      type: node.type.name,
      name: node.name || node.type.name,
      from: node.from,
      to: node.to,
      text: text.slice(node.from, node.to),
      children,
    };
  }

  getRootNodeInfo(): SyntaxNodeInfo | null {
    if (!this.lastTree || !this.lastText) return null;
    return this.getNodeInfo(this.lastTree.topNode, this.lastText);
  }

  findNodesByType(type: string): SyntaxNodeInfo[] {
    const results: SyntaxNodeInfo[] = [];
    if (!this.lastTree) return results;

    this.lastTree.iterate({
      enter: (node) => {
        if (node.type.name === type && node.node) {
          results.push(this.getNodeInfo(node.node, this.lastText));
        }
      },
    });

    return results;
  }

  findParentNode(node: SyntaxNode, parentType: string): SyntaxNode | null {
    let current: SyntaxNode | null = node.parent;
    while (current) {
      if (current.type.name === parentType) {
        return current;
      }
      current = current.parent;
    }
    return null;
  }

  getLastText(): string {
    return this.lastText;
  }

  reset(): void {
    this.lastTree = null;
    this.lastText = '';
  }

  static createInput(text: string): Input {
    return {
      read: (pos: number) => (pos < text.length ? text.charCodeAt(pos) : -1),
      chunk: (from: number) => text.slice(from, from + 1024),
      length: text.length,
    };
  }
}

export class SyntaxTreeWalker {
  private tree: Tree;
  private text: string;

  constructor(tree: Tree, text: string) {
    this.tree = tree;
    this.text = text;
  }

  walk(visitor: {
    enter?: (node: SyntaxNode, depth: number) => void | boolean;
    leave?: (node: SyntaxNode, depth: number) => void;
  }): void {
    const walk = (node: SyntaxNode, depth: number): boolean => {
      if (visitor.enter) {
        const result = visitor.enter(node, depth);
        if (result === false) return false;
      }

      let child = node.firstChild;
      while (child) {
        if (!walk(child, depth + 1)) return false;
        child = child.nextSibling;
      }

      if (visitor.leave) {
        visitor.leave(node, depth);
      }

      return true;
    };

    walk(this.tree.topNode, 0);
  }

  collect(predicate: (node: SyntaxNode) => boolean): SyntaxNode[] {
    const results: SyntaxNode[] = [];
    this.walk({
      enter: (node) => {
        if (predicate(node)) {
          results.push(node);
        }
      },
    });
    return results;
  }
}
