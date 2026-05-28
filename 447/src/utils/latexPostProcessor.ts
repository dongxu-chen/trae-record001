interface StructureNode {
  type: 'root' | 'command' | 'group' | 'text' | 'environment';
  content?: string;
  children?: StructureNode[];
  command?: string;
  envName?: string;
  startIndex: number;
  endIndex: number;
}

function parseStructure(latex: string): StructureNode {
  let pos = 0;

  function parseGroup(): StructureNode {
    const start = pos;
    pos++;
    const children: StructureNode[] = [];
    while (pos < latex.length && latex[pos] !== '}') {
      if (latex[pos] === '{') {
        children.push(parseGroup());
      } else if (latex[pos] === '\\') {
        children.push(parseCommand());
      } else {
        children.push(parseText());
      }
    }
    if (pos < latex.length) pos++;
    return { type: 'group', children, startIndex: start, endIndex: pos };
  }

  function parseCommand(): StructureNode {
    const start = pos;
    pos++;
    let cmd = '';
    while (pos < latex.length && /[a-zA-Z]/.test(latex[pos])) {
      cmd += latex[pos];
      pos++;
    }
    if (!cmd && pos < latex.length) {
      cmd = latex[pos];
      pos++;
    }

    if (cmd === 'begin') {
      return parseEnvironment(start);
    }

    const children: StructureNode[] = [];
    if (cmd === 'frac' || cmd === 'dfrac' || cmd === 'tfrac' || cmd === 'sqrt') {
      if (pos < latex.length && latex[pos] === '[') {
        children.push(parseOptionalArg());
      }
      if (pos < latex.length && latex[pos] === '{') {
        children.push(parseGroup());
      }
      if (cmd === 'frac' || cmd === 'dfrac' || cmd === 'tfrac') {
        if (pos < latex.length && latex[pos] === '{') {
          children.push(parseGroup());
        }
      }
    } else if (cmd === 'left' || cmd === 'right') {
      // skip delimiter
      if (pos < latex.length) pos++;
    }

    return { type: 'command', command: cmd, children, startIndex: start, endIndex: pos };
  }

  function parseOptionalArg(): StructureNode {
    const start = pos;
    pos++;
    let content = '';
    while (pos < latex.length && latex[pos] !== ']') {
      content += latex[pos];
      pos++;
    }
    if (pos < latex.length) pos++;
    return { type: 'group', content, startIndex: start, endIndex: pos };
  }

  function parseEnvironment(start: number): StructureNode {
    if (pos < latex.length && latex[pos] === '{') {
      pos++;
      let envName = '';
      while (pos < latex.length && latex[pos] !== '}') {
        envName += latex[pos];
        pos++;
      }
      if (pos < latex.length) pos++;

      const children: StructureNode[] = [];
      const endMarker = `\\end{${envName}}`;
      while (pos < latex.length && !latex.substring(pos).startsWith(endMarker)) {
        if (latex[pos] === '{') {
          children.push(parseGroup());
        } else if (latex[pos] === '\\') {
          children.push(parseCommand());
        } else {
          children.push(parseText());
        }
      }
      if (pos < latex.length) {
        pos += endMarker.length;
      }
      return { type: 'environment', envName, children, startIndex: start, endIndex: pos };
    }
    return { type: 'command', command: 'begin', children: [], startIndex: start, endIndex: pos };
  }

  function parseText(): StructureNode {
    const start = pos;
    let content = '';
    while (pos < latex.length && latex[pos] !== '\\' && latex[pos] !== '{' && latex[pos] !== '}') {
      content += latex[pos];
      pos++;
    }
    return { type: 'text', content, startIndex: start, endIndex: pos };
  }

  const children: StructureNode[] = [];
  while (pos < latex.length) {
    if (latex[pos] === '{') {
      children.push(parseGroup());
    } else if (latex[pos] === '\\') {
      children.push(parseCommand());
    } else {
      children.push(parseText());
    }
  }

  return { type: 'root', children, startIndex: 0, endIndex: latex.length };
}

function countBraces(latex: string): { open: number; close: number } {
  let open = 0;
  let close = 0;
  let escaped = false;
  for (let i = 0; i < latex.length; i++) {
    if (escaped) { escaped = false; continue; }
    if (latex[i] === '\\') { escaped = true; continue; }
    if (latex[i] === '{') open++;
    if (latex[i] === '}') close++;
  }
  return { open, close };
}

const COMMAND_ARG_COUNT: Record<string, number> = {
  frac: 2, dfrac: 2, tfrac: 2, sqrt: 1, hat: 1, bar: 1, vec: 1, dot: 1,
  tilde: 1, widehat: 1, overline: 1, underline: 1, overrightarrow: 1,
  overleftarrow: 1, text: 1, mathrm: 1, mathbf: 1, mathit: 1,
  mathsf: 1, mathtt: 1, mathbb: 1, mathcal: 1, mathscr: 1,
  operatorname: 1, binom: 2, tbinom: 2, dbinom: 2,
  overset: 2, underset: 2, stackrel: 2,
  sum: 0, prod: 0, int: 0, iint: 0, iiint: 0, oint: 0,
  lim: 0, sup: 0, inf: 0, max: 0, min: 0,
};

function fixMissingArguments(latex: string): string {
  let result = latex;

  for (const [cmd, argCount] of Object.entries(COMMAND_ARG_COUNT)) {
    const cmdPattern = `\\${cmd}`;
    let searchPos = 0;
    while (true) {
      const idx = result.indexOf(cmdPattern, searchPos);
      if (idx === -1) break;

      const cmdEnd = idx + cmdPattern.length;
      if (cmd === 'sqrt' && cmdEnd < result.length && result[cmdEnd] === '[') {
        searchPos = cmdEnd;
        continue;
      }

      let argStart = cmdEnd;
      while (argStart < result.length && result[argStart] === ' ') argStart++;

      let foundArgs = 0;
      let checkPos = argStart;
      for (let a = 0; a < argCount; a++) {
        if (checkPos < result.length && result[checkPos] === '{') {
          foundArgs++;
          let depth = 1;
          checkPos++;
          while (checkPos < result.length && depth > 0) {
            if (result[checkPos] === '{') depth++;
            if (result[checkPos] === '}') depth--;
            checkPos++;
          }
        } else {
          break;
        }
      }

      const missing = argCount - foundArgs;
      if (missing > 0) {
        const insertion = '{}'.repeat(missing);
        result = result.slice(0, cmdEnd) + insertion + result.slice(cmdEnd);
        searchPos = cmdEnd + insertion.length;
      } else {
        searchPos = cmdEnd;
      }
    }
  }

  return result;
}

function fixMismatchedEnvironments(latex: string): string {
  const beginPattern = /\\begin\{(\w+)\}/g;
  const endPattern = /\\end\{(\w+)\}/g;

  const beginStack: { name: string; index: number }[] = [];
  let match: RegExpExecArray | null;

  while ((match = beginPattern.exec(latex)) !== null) {
    beginStack.push({ name: match[1], index: match.index });
  }

  const endNames: { name: string; index: number }[] = [];
  while ((match = endPattern.exec(latex)) !== null) {
    endNames.push({ name: match[1], index: match.index });
  }

  let result = latex;

  for (let i = beginStack.length - 1; i >= 0; i--) {
    const hasMatchingEnd = endNames.some(
      (e) => e.name === beginStack[i].name
    );
    if (!hasMatchingEnd) {
      const insertPos = result.length;
      result = result.slice(0, insertPos) + `\\end{${beginStack[i].name}}` + result.slice(insertPos);
    }
  }

  for (let i = endNames.length - 1; i >= 0; i--) {
    const hasMatchingBegin = beginStack.some(
      (b) => b.name === endNames[i].name
    );
    if (!hasMatchingBegin) {
      const insertPos = 0;
      result = `\\begin{${endNames[i].name}}` + result;
    }
  }

  return result;
}

const OCR_CORRECTIONS: [RegExp, string][] = [
  [/\\f rac/g, '\\frac'],
  [/\\sq rt/g, '\\sqrt'],
  [/\\s qrt/g, '\\sqrt'],
  [/\\s um/g, '\\sum'],
  [/\\p rod/g, '\\prod'],
  [/\\i nt/g, '\\int'],
  [/\\l im/g, '\\lim'],
  [/\\l og/g, '\\log'],
  [/\\l n\b/g, '\\ln'],
  [/\\s in/g, '\\sin'],
  [/\\c os/g, '\\cos'],
  [/\\t an/g, '\\tan'],
  [/\\a lpha/g, '\\alpha'],
  [/\\b eta/g, '\\beta'],
  [/\\g amma/g, '\\gamma'],
  [/\\d elta/g, '\\delta'],
  [/\\t heta/g, '\\theta'],
  [/\\l ambda/g, '\\lambda'],
  [/\\s igma/g, '\\sigma'],
  [/\\o mega/g, '\\omega'],
  [/\\p hi/g, '\\phi'],
  [/\\p si/g, '\\psi'],
  [/\\p i\b/g, '\\pi'],
  [/\\m u\b/g, '\\mu'],
  [/\\e psilon/g, '\\epsilon'],
  [/\\b egin\{/g, '\\begin{'],
  [/\\e nd\{/g, '\\end{'],
  [/\}\s*\\frac/g, '}\\frac'],
  [/\\frac\s*\{([^}]*)\}\s*([^{])/g, '\\frac{$1}{$2'],
  [/\\left\.\s*\\right\)/g, '\\left(\\right)'],
  [/\\left\(\s*\\right\./g, '\\left(\\right)'],
];

function fixOcrErrors(latex: string): string {
  let result = latex;
  for (const [pattern, replacement] of OCR_CORRECTIONS) {
    result = result.replace(pattern, replacement);
  }
  return result;
}

function fixMismatchedBraces(latex: string): string {
  const { open, close } = countBraces(latex);
  if (open > close) {
    return latex + '}'.repeat(open - close);
  }
  if (close > open) {
    return '{'.repeat(close - open) + latex;
  }
  return latex;
}

function fixSplitCommands(latex: string): string {
  let result = latex;

  result = result.replace(/\\\s+([a-zA-Z]+)/g, (_, cmd) => `\\${cmd}`);

  result = result.replace(/\}\s*\{/g, '}{');

  result = result.replace(/\\frac\{([^}]*)\}(?!\{)/g, '\\frac{$1}{}');

  return result;
}

export function postProcessLatex(rawLatex: string): { latex: string; corrections: string[] } {
  const corrections: string[] = [];
  let result = rawLatex.trim();

  const ocrFixed = fixOcrErrors(result);
  if (ocrFixed !== result) {
    corrections.push('修正OCR识别错误');
    result = ocrFixed;
  }

  const splitFixed = fixSplitCommands(result);
  if (splitFixed !== result) {
    corrections.push('修复断裂命令');
    result = splitFixed;
  }

  const braceFixed = fixMismatchedBraces(result);
  const { open, close } = countBraces(result);
  if (open !== close) {
    corrections.push(`补全花括号 (缺${open > close ? open - close : close - open}个${open > close ? '右' : '左'}括号)`);
    result = braceFixed;
  }

  const argFixed = fixMissingArguments(result);
  if (argFixed !== result) {
    corrections.push('补全命令参数');
    result = argFixed;
  }

  const envFixed = fixMismatchedEnvironments(result);
  if (envFixed !== result) {
    corrections.push('修复环境配对');
    result = envFixed;
  }

  try {
    parseStructure(result);
  } catch {
    corrections.push('结构解析异常，请手动检查');
  }

  return { latex: result, corrections };
}
