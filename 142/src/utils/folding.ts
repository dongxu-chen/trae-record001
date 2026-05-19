export interface FoldableBlock {
  id: string;
  startLine: number;
  endLine: number;
  type: 'function' | 'if' | 'for' | 'while' | 'class' | 'try' | 'switch' | 'object' | 'array';
  isFolded: boolean;
  label: string;
}

export interface FoldingState {
  blocks: FoldableBlock[];
  foldedIds: Set<string>;
}

const BLOCK_PATTERNS: { type: FoldableBlock['type']; pattern: RegExp }[] = [
  {
    type: 'function',
    pattern: /^(?:(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s+|const\s+\w+\s*=\s*(?:async\s+)?\(|let\s+\w+\s*=\s*(?:async\s+)?\(|\w+\s*:\s*(?:async\s+)?\(|[a-zA-Z_$][\w$]*\s*\([^)]*\)\s*\{))/,
  },
  { type: 'if', pattern: /^\s*(?:}?\s*)?\b(if|else\s+if)\s*\(/ },
  { type: 'for', pattern: /^\s*\bfor\s*\(/ },
  { type: 'while', pattern: /^\s*\bwhile\s*\(/ },
  { type: 'class', pattern: /^\s*(?:export\s+)?\bclass\s+\w+/ },
  { type: 'try', pattern: /^\s*\btry\s*\{/ },
  { type: 'switch', pattern: /^\s*\bswitch\s*\(/ },
];

function countBraces(line: string): { open: number; close: number } {
  let open = 0;
  let close = 0;
  let inString = false;
  let stringChar = '';
  let inComment = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const nextChar = line[i + 1];

    if (inComment) {
      if (char === '*' && nextChar === '/') {
        inComment = false;
        i++;
      }
      continue;
    }

    if (char === '/' && nextChar === '*') {
      inComment = true;
      i++;
      continue;
    }

    if (char === '/' && nextChar === '/') {
      break;
    }

    if (inString) {
      if (char === stringChar && line[i - 1] !== '\\') {
        inString = false;
      }
      continue;
    }

    if (char === '"' || char === "'" || char === '`') {
      inString = true;
      stringChar = char;
      continue;
    }

    if (char === '{') open++;
    if (char === '}') close++;
  }

  return { open, close };
}

function extractLabel(line: string, type: FoldableBlock['type']): string {
  const trimmed = line.trim();
  
  switch (type) {
    case 'function': {
      const funcMatch = trimmed.match(/function\s+([a-zA-Z_$][\w$]*)/);
      if (funcMatch) return funcMatch[1];
      const arrowMatch = trimmed.match(/(?:const|let|var)\s+([a-zA-Z_$][\w$]*)/);
      if (arrowMatch) return arrowMatch[1];
      const methodMatch = trimmed.match(/([a-zA-Z_$][\w$]*)\s*\(/);
      if (methodMatch) return methodMatch[1];
      return 'function';
    }
    case 'if':
      return 'if';
    case 'for':
      return 'for';
    case 'while':
      return 'while';
    case 'class': {
      const match = trimmed.match(/class\s+([a-zA-Z_$][\w$]*)/);
      return match ? match[1] : 'class';
    }
    case 'try':
      return 'try';
    case 'switch':
      return 'switch';
    default:
      return '{...}';
  }
}

export function detectFoldableBlocks(code: string): FoldableBlock[] {
  const lines = code.split('\n');
  const blocks: FoldableBlock[] = [];
  const stack: { type: FoldableBlock['type']; startLine: number; braceCount: number; label: string }[] = [];

  lines.forEach((line, lineIndex) => {
    const { open, close } = countBraces(line);

    for (const { type, pattern } of BLOCK_PATTERNS) {
      if (pattern.test(line)) {
        const label = extractLabel(line, type);
        stack.push({ type, startLine: lineIndex + 1, braceCount: open, label });
        break;
      }
    }

    for (let i = stack.length - 1; i >= 0; i--) {
      const item = stack[i];
      item.braceCount = item.braceCount - close + open;

      if (item.braceCount <= 0 && item.startLine < lineIndex + 1) {
        blocks.push({
          id: `fold-${item.type}-${item.startLine}-${lineIndex + 1}`,
          startLine: item.startLine,
          endLine: lineIndex + 1,
          type: item.type,
          isFolded: false,
          label: item.label,
        });
        stack.splice(i, 1);
      }
    }
  });

  while (stack.length > 0) {
    const item = stack.pop()!;
    if (item.startLine < lines.length) {
      blocks.push({
        id: `fold-${item.type}-${item.startLine}-${lines.length}`,
        startLine: item.startLine,
        endLine: lines.length,
        type: item.type,
        isFolded: false,
        label: item.label,
      });
    }
  }

  return blocks.sort((a, b) => a.startLine - b.startLine);
}

export function getFoldedLines(blocks: FoldableBlock[], foldedIds: Set<string>): Set<number> {
  const foldedLines = new Set<number>();

  for (const block of blocks) {
    if (foldedIds.has(block.id)) {
      for (let i = block.startLine + 1; i <= block.endLine; i++) {
        foldedLines.add(i);
      }
    }
  }

  return foldedLines;
}

export function findBlockAtLine(blocks: FoldableBlock[], lineNumber: number): FoldableBlock | null {
  for (const block of blocks) {
    if (block.startLine === lineNumber) {
      return block;
    }
  }
  return null;
}

export function getInnermostBlockAtLine(blocks: FoldableBlock[], lineNumber: number): FoldableBlock | null {
  const containingBlocks = blocks.filter(
    (b) => b.startLine <= lineNumber && b.endLine >= lineNumber
  );

  if (containingBlocks.length === 0) return null;

  return containingBlocks.reduce((innermost, current) => {
    const currentSize = current.endLine - current.startLine;
    const innermostSize = innermost.endLine - innermost.startLine;
    return currentSize < innermostSize ? current : innermost;
  });
}
