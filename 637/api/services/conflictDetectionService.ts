import type { ConflictInfo, ConflictDetectionRequest, ConflictDetectionResult } from '../../shared/types';

const JS_RESERVED = new Set([
  'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
  'default', 'delete', 'do', 'else', 'export', 'extends', 'finally',
  'for', 'function', 'if', 'import', 'in', 'instanceof', 'new',
  'return', 'super', 'switch', 'this', 'throw', 'try', 'typeof',
  'var', 'void', 'while', 'with', 'yield', 'let', 'static', 'enum',
  'await', 'async', 'implements', 'interface', 'package', 'private',
  'protected', 'public', 'abstract', 'as', 'boolean', 'byte', 'char',
  'double', 'final', 'float', 'goto', 'int', 'long', 'native',
  'short', 'synchronized', 'throws', 'transient', 'volatile',
  'true', 'false', 'null', 'undefined', 'NaN', 'Infinity',
  'arguments', 'eval', 'arguments', 'Array', 'Date', 'Math', 'Number',
  'Object', 'String', 'RegExp', 'Error', 'Promise', 'Map', 'Set',
  'WeakMap', 'WeakSet', 'JSON', 'console', 'window', 'document',
  'navigator', 'location', 'history', 'screen', 'event', 'window'
]);

const PY_RESERVED = new Set([
  'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
  'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
  'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
  'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
  'while', 'with', 'yield'
]);

const JAVA_RESERVED = new Set([
  'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch',
  'char', 'class', 'const', 'continue', 'default', 'do', 'double',
  'else', 'enum', 'extends', 'final', 'finally', 'float', 'for',
  'goto', 'if', 'implements', 'import', 'instanceof', 'int', 'interface',
  'long', 'native', 'new', 'package', 'private', 'protected', 'public',
  'return', 'short', 'static', 'strictfp', 'super', 'switch',
  'synchronized', 'this', 'throw', 'throws', 'transient', 'try',
  'void', 'volatile', 'while', 'true', 'false', 'null'
]);

const GO_RESERVED = new Set([
  'break', 'case', 'chan', 'const', 'continue', 'default', 'defer',
  'else', 'fallthrough', 'for', 'func', 'go', 'goto', 'if',
  'import', 'interface', 'map', 'package', 'range', 'return', 'select',
  'struct', 'switch', 'type', 'var', 'true', 'false', 'nil', 'iota',
  'append', 'cap', 'close', 'complex', 'copy', 'delete', 'imag',
  'len', 'make', 'new', 'panic', 'print', 'println', 'real', 'recover'
]);

const LANGUAGE_KEYWORDS: Record<string, Set<string>> = {
  javascript: JS_RESERVED,
  typescript: JS_RESERVED,
  python: PY_RESERVED,
  java: JAVA_RESERVED,
  go: GO_RESERVED
};

function isReservedKeyword(name: string, language: string = 'javascript'): boolean {
  const keywords = LANGUAGE_KEYWORDS[language] || JS_RESERVED;
  return keywords.has(name);
}

function extractIdentifiers(code: string): Array<{ name: string; type: ConflictInfo['type'] }> {
  const identifiers: Array<{ name: string; type: ConflictInfo['type'] }> = [];
  
  const varPattern = /(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)/g;
  let match;
  while ((match = varPattern.exec(code)) !== null) {
    identifiers.push({ name: match[2], type: 'variable' });
  }
  
  const funcPattern = /function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(/g;
  while ((match = funcPattern.exec(code)) !== null) {
    identifiers.push({ name: match[1], type: 'function' });
  }
  
  const classPattern = /class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)/g;
  while ((match = classPattern.exec(code)) !== null) {
    identifiers.push({ name: match[1], type: 'class' });
  }
  
  const importPattern = /import\s+.*from\s+['"]([^'"]+)['"]/g;
  while ((match = importPattern.exec(code)) !== null) {
    const importPath = match[1];
    const importName = importPath.split('/').pop() || importPath;
    if (importName && !isReservedKeyword(importName)) {
      identifiers.push({ name: importName, type: 'import' });
    }
  }
  
  return identifiers;
}

function generateAlternativeNames(name: string, existingNames: Set<string>): string[] {
  const alternatives: string[] = [];
  const suffixes = ['1', '2', '3', 'New', 'Updated', 'V2', 'Alt'];
  
  for (const suffix of suffixes) {
    const alt = name + suffix;
    if (!existingNames.has(alt)) {
      alternatives.push(alt);
    }
  }
  
  const prefixes = ['my', 'the', 'local', 'temp'];
  for (const prefix of prefixes) {
    const alt = prefix + name.charAt(0).toUpperCase() + name.slice(1);
    if (!existingNames.has(alt)) {
      alternatives.push(alt);
    }
  }
  
  return alternatives.slice(0, 5);
}

export function detectConflicts(
  request: ConflictDetectionRequest
): ConflictDetectionResult {
  const { name, code, scope = 'global' } = request;
  const conflicts: ConflictInfo[] = [];
  const existingNames = new Set<string>();
  
  if (isReservedKeyword(name, 'javascript')) {
    conflicts.push({
      name,
      type: 'keyword',
      scope,
      suggestion: '请选择其他名称'
    });
  }
  
  const identifiers = extractIdentifiers(code);
  for (const id of identifiers) {
    existingNames.add(id.name);
    if (id.name === name) {
      conflicts.push({
        name: id.name,
        type: id.type,
        scope,
        suggestion: `名称 '${name}' 已存在`
      });
    }
  }
  
  const suggestions = generateAlternativeNames(name, existingNames);
  
  return {
    hasConflict: conflicts.length > 0,
    conflicts,
    suggestions
  };
}

export function detectAllConflicts(code: string): ConflictInfo[] {
  const conflicts: ConflictInfo[] = [];
  const nameCount: Record<string, number> = {};
  
  const identifiers = extractIdentifiers(code);
  
  for (const id of identifiers) {
    nameCount[id.name] = (nameCount[id.name] || 0) + 1;
  }
  
  for (const id of identifiers) {
    if (nameCount[id.name] > 1) {
      conflicts.push({
        name: id.name,
        type: id.type,
        scope: 'global',
        suggestion: `名称 '${id.name}' 被定义了 ${nameCount[id.name]} 次`
      });
    }
  }
  
  return conflicts;
}

export function validateName(
  name: string,
  code?: string,
  language: string = 'javascript'
): {
  valid: boolean;
  issues: Array<{
    type: 'error' | 'warning';
    message: string;
    severity: 'high' | 'medium' | 'low';
  }>;
  suggestions: string[];
} {
  const issues: Array<{
    type: 'error' | 'warning';
    message: string;
    severity: 'high' | 'medium' | 'low';
  }> = [];
  const suggestions: string[] = [];
  
  if (!name || name.length === 0) {
    issues.push({
      type: 'error',
      message: '名称不能为空',
      severity: 'high'
    });
    return { valid: false, issues, suggestions };
  }
  
  if (!/^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(name)) {
    issues.push({
      type: 'error',
      message: '名称格式无效',
      severity: 'high'
    });
  }
  
  if (isReservedKeyword(name, language)) {
    issues.push({
      type: 'error',
      message: `'${name}' 是保留关键字`,
      severity: 'high'
    });
    const existingNames = new Set<string>();
    if (code) {
      const identifiers = extractIdentifiers(code);
      for (const id of identifiers) {
        existingNames.add(id.name);
      }
    }
    suggestions.push(...generateAlternativeNames(name, existingNames));
  }
  
  if (code) {
    const identifiers = extractIdentifiers(code);
    const existingNames = new Set(identifiers.map(i => i.name));
    if (existingNames.has(name)) {
      issues.push({
        type: 'warning',
        message: `'${name}' 已存在于代码中`,
        severity: 'medium'
      });
      suggestions.push(...generateAlternativeNames(name, existingNames));
    }
  }
  
  if (name.length < 2) {
    issues.push({
      type: 'warning',
      message: '名称过短，可能影响可读性',
      severity: 'low'
    });
  }
  
  return {
    valid: issues.filter(i => i.type === 'error').length === 0,
    issues,
    suggestions
  };
}

export function checkScopeConflicts(
  name: string,
  code: string
): {
  scope: string;
  conflicts: ConflictInfo[];
} {
  const functions = code.split(/function\s+\w+\s*\([^)]*\)\s*\{/);
  
  const scopes: string[] = [];
  let braceCount = 0;
  let currentScope = 'global';
  
  const conflicts: ConflictInfo[] = [];
  const scopeConflicts: Record<string, ConflictInfo[]> = {};
  
  for (let i = 0; i < code.length; i++) {
    if (code[i] === '{') {
      braceCount++;
    } else if (code[i] === '}') {
      braceCount--;
      if (braceCount === 0) {
        currentScope = 'global';
      }
    }
    
    const funcMatch = code.substring(i).match(/function\s+(\w+)\s*\(/);
    if (funcMatch && funcMatch.index === 0) {
      currentScope = funcMatch[1];
    }
  }
  
  const result = detectConflicts({ name, code });
  
  return {
    scope: currentScope,
    conflicts: result.conflicts.map(c => ({ ...c, scope: currentScope }))
  };
}
