import type { BatchRenameRequest, BatchRenameResult, VariableType } from '../../shared/types';

const JS_KEYWORDS = new Set([
  'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
  'default', 'delete', 'do', 'else', 'export', 'extends', 'finally',
  'for', 'function', 'if', 'import', 'in', 'instanceof', 'new',
  'return', 'super', 'switch', 'this', 'throw', 'try', 'typeof',
  'var', 'void', 'while', 'with', 'yield', 'let', 'static', 'enum',
  'await', 'async', 'implements', 'interface', 'package', 'private',
  'protected', 'public', 'abstract', 'as', 'boolean', 'byte', 'char',
  'double', 'final', 'float', 'goto', 'int', 'long', 'native',
  'short', 'synchronized', 'throws', 'transient', 'volatile', 'true',
  'false', 'null', 'undefined', 'NaN', 'Infinity', 'arguments'
]);

function isKeyword(name: string): boolean {
  return JS_KEYWORDS.has(name);
}

function escapeRegExp(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function findAllOccurrences(code: string, name: string): Array<{ start: number; end: number; line: number }> {
  const occurrences: Array<{ start: number; end: number; line: number }> = [];
  const pattern = new RegExp(`\\b${escapeRegExp(name)}\\b`, 'g');
  let match;
  
  while ((match = pattern.exec(code)) !== null) {
    const beforeChar = match.index > 0 ? code[match.index - 1] : '';
    const afterChar = match.index + match[0].length < code.length ? code[match.index + match[0].length] : '';
    
    if (!beforeChar.match(/[a-zA-Z0-9_]/) || !afterChar.match(/[a-zA-Z0-9_]/)) {
      const lineNumber = code.substring(0, match.index).split('\n').length;
      occurrences.push({
        start: match.index,
        end: match.index + match[0].length,
        line: lineNumber
      });
    }
  }
  
  return occurrences;
}

function detectVariableType(code: string, name: string): VariableType {
  const patterns = [
    { pattern: new RegExp(`(?:const|let|var)\\s+${escapeRegExp(name)}\\s*[:=]`, 'g'), type: 'variable' as VariableType },
    { pattern: new RegExp(`(?:const|let|var)\\s+${escapeRegExp(name)}\\s*[:=]\\s*`, 'g'), type: 'variable' as VariableType },
    { pattern: new RegExp(`function\\s+${escapeRegExp(name)}\\s*\\(`, 'g'), type: 'function' as VariableType },
    { pattern: new RegExp(`class\\s+${escapeRegExp(name)}`, 'g'), type: 'class' as VariableType },
    { pattern: new RegExp(`const\\s+${escapeRegExp(name)}\\s*=\\s*[A-Z_]+`, 'g'), type: 'constant' as VariableType },
    { pattern: new RegExp(`\\b${escapeRegExp(name)}\\s*[:=]\\s*(?:true|false)`, 'g'), type: 'boolean' as VariableType }
  ];

  for (const { pattern, type } of patterns) {
    if (pattern.test(code)) {
      return type;
    }
  }
  
  return 'variable';
}

export function performBatchRename(request: BatchRenameRequest): BatchRenameResult {
  const { code, items, dryRun = false } = request;
  let modifiedCode = code;
  const results: BatchRenameResult['results'] = [];
  let totalRenamed = 0;
  let totalSkipped = 0;

  const sortedItems = [...items].sort((a, b) => b.oldName.length - a.oldName.length);

  for (const item of sortedItems) {
    const { oldName, newName } = item;
    
    if (oldName === newName) {
      results.push({
        oldName,
        newName,
        renamed: false,
        occurrences: 0,
        error: '新旧名称相同'
      });
      totalSkipped++;
      continue;
    }
    
    if (isKeyword(newName)) {
      results.push({
        oldName,
        newName,
        renamed: false,
        occurrences: 0,
        error: '新名称是保留关键字'
      });
      totalSkipped++;
      continue;
    }
    
    const occurrences = findAllOccurrences(modifiedCode, oldName);
    
    if (occurrences.length === 0) {
      results.push({
        oldName,
        newName,
        renamed: false,
        occurrences: 0,
        error: '未找到匹配项'
      });
      totalSkipped++;
      continue;
    }
    
    const newNameOccurrences = findAllOccurrences(modifiedCode, newName);
    if (newNameOccurrences.length > 0 && !items.some(i => i.oldName === newName)) {
      results.push({
        oldName,
        newName,
        renamed: false,
        occurrences: occurrences.length,
        error: `新名称 ${newName} 已存在于代码中`
      });
      totalSkipped++;
      continue;
    }
    
    if (!dryRun) {
      const regex = new RegExp(`\\b${escapeRegExp(oldName)}\\b`, 'g');
      modifiedCode = modifiedCode.replace(regex, newName);
    }
    
    results.push({
      oldName,
      newName,
      renamed: true,
      occurrences: occurrences.length
    });
    totalRenamed++;
  }

  return {
    success: true,
    modifiedCode,
    results,
    totalRenamed,
    totalSkipped
  };
}

export function detectVariablesInCode(code: string, language: BatchRenameRequest['language']): Array<{
  name: string;
  type: VariableType;
  occurrences: number;
}> {
  const variables: Map<string, { type: VariableType; occurrences: number }> = new Map();
  
  const varPattern = /(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\b/g;
  let match;
  
  while ((match = varPattern.exec(code)) !== null) {
    const name = match[1];
    if (!isKeyword(name)) {
      const existing = variables.get(name) || { type: detectVariableType(code, name), occurrences: 0 };
      variables.set(name, {
        ...existing,
        occurrences: existing.occurrences + 1
      });
    }
  }
  
  const funcPattern = /function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(/g;
  while ((match = funcPattern.exec(code)) !== null) {
    const name = match[1];
    if (!isKeyword(name)) {
      const existing = variables.get(name) || { type: 'function' as VariableType, occurrences: 0 };
      variables.set(name, {
        ...existing,
        type: 'function',
        occurrences: existing.occurrences + 1
      });
    }
  }
  
  const classPattern = /class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\b/g;
  while ((match = classPattern.exec(code)) !== null) {
    const name = match[1];
    if (!isKeyword(name)) {
      const existing = variables.get(name) || { type: 'class' as VariableType, occurrences: 0 };
      variables.set(name, {
        ...existing,
        type: 'class',
        occurrences: existing.occurrences + 1
      });
    }
  }
  
  return Array.from(variables.entries()).map(([name, info]) => ({
    name,
    type: info.type,
    occurrences: info.occurrences
  }));
}

export function generateDiff(oldCode: string, newCode: string): string {
  const oldLines = oldCode.split('\n');
  const newLines = newCode.split('\n');
  const diff: string[] = [];
  
  for (let i = 0; i < Math.max(oldLines.length, newLines.length); i++) {
    const oldLine = oldLines[i];
    const newLine = newLines[i];
    
    if (oldLine !== newLine) {
      if (oldLine !== undefined) {
        diff.push(`- ${oldLine}`);
      }
      if (newLine !== undefined) {
        diff.push(`+ ${newLine}`);
      }
      diff.push('');
    }
  }
  
  return diff.join('\n');
}

export function validateRename(code: string, oldName: string, newName: string): {
  valid: boolean;
  errors: string[];
  warnings: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  if (oldName === newName) {
    errors.push('新旧名称相同');
  }
  
  if (isKeyword(newName)) {
    errors.push(`'${newName}' 是保留关键字`);
  }
  
  if (!/^[a-zA-Z_$][a-zA-Z0-9_$]*$/.test(newName)) {
    errors.push('新名称格式无效');
  }
  
  const occurrences = findAllOccurrences(code, oldName);
  if (occurrences.length === 0) {
    warnings.push('未找到匹配项');
  }
  
  const newNameExists = findAllOccurrences(code, newName);
  if (newNameExists.length > 0) {
    warnings.push(`新名称 ${newName} 已存在`);
  }
  
  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}
