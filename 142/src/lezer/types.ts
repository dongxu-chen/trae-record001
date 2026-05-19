import type { Tree, SyntaxNode } from '@lezer/common';

export type Language = 'javascript' | 'typescript' | 'python' | 'css' | 'json' | 'java' | 'rust';

export interface SyntaxNodeInfo {
  type: string;
  name: string;
  from: number;
  to: number;
  text: string;
  children: SyntaxNodeInfo[];
}

export interface ParseResult {
  tree: Tree;
  duration: number;
  nodeCount: number;
}

export interface IncrementalUpdate {
  start: number;
  end: number;
  newText: string;
}

export interface HighlightToken {
  type: string;
  from: number;
  to: number;
  className: string;
}

export interface Definition {
  name: string;
  type: 'function' | 'class' | 'variable' | 'method' | 'interface' | 'type';
  from: number;
  to: number;
  selectionStart: number;
  selectionEnd: number;
}

export interface CompletionItem {
  label: string;
  kind: 'function' | 'class' | 'variable' | 'keyword' | 'property' | 'method';
  detail?: string;
  documentation?: string;
  insertText?: string;
}

export interface Diagnostic {
  from: number;
  to: number;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

export interface TextDocument {
  uri: string;
  text: string;
  version: number;
  languageId: Language;
}

export interface Position {
  line: number;
  character: number;
}

export interface Range {
  start: Position;
  end: Position;
}

export interface LSPRequest {
  method: string;
  params: any;
}

export interface LSPResponse<T = any> {
  result?: T;
  error?: {
    code: number;
    message: string;
  };
}

export interface CodeSnippetOptions {
  language: Language;
  enableIncremental?: boolean;
  enableLSP?: boolean;
  enableFolding?: boolean;
  theme?: 'dark' | 'light';
  lineNumbers?: boolean;
  minimap?: boolean;
  readOnly?: boolean;
}

export interface ParsePerformanceMetrics {
  parseTime: number;
  highlightTime: number;
  totalTime: number;
  nodeCount: number;
  tokenCount: number;
}
