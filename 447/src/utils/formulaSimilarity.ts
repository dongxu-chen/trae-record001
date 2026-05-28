import type { Formula } from '@/db/database';

interface FeatureVector {
  commands: Map<string, number>;
  symbols: Map<string, number>;
  tokens: Map<string, number>;
  structure: number[];
}

const COMMANDS: string[] = [
  'frac', 'sqrt', 'sum', 'prod', 'int', 'iint', 'iiint', 'oint',
  'sin', 'cos', 'tan', 'log', 'ln', 'exp', 'lim', 'sup', 'inf',
  'alpha', 'beta', 'gamma', 'delta', 'theta', 'lambda', 'mu', 'pi',
  'sigma', 'omega', 'phi', 'psi', 'epsilon', 'nabla', 'partial',
  'begin', 'end', 'left', 'right', 'mathbb', 'mathbf', 'mathcal',
  'rightarrow', 'leftarrow', 'Rightarrow', 'Leftarrow', 'leftrightarrow',
  'in', 'notin', 'subset', 'subseteq', 'cap', 'cup', 'emptyset',
  'infty', 'pm', 'mp', 'times', 'div', 'cdot', 'neq', 'approx',
  'leq', 'geq', 'implies', 'iff', 'exists', 'forall',
];

const tokenizeLatex = (latex: string): string[] => {
  const tokens: string[] = [];
  let i = 0;
  while (i < latex.length) {
    if (latex[i] === '\\') {
      i++;
      let cmd = '';
      while (i < latex.length && /[a-zA-Z]/.test(latex[i])) {
        cmd += latex[i];
        i++;
      }
      if (cmd) {
        tokens.push('\\' + cmd);
      } else if (i < latex.length) {
        tokens.push('\\' + latex[i]);
        i++;
      }
    } else if (/[{}()\[\]|]/.test(latex[i])) {
      tokens.push(latex[i]);
      i++;
    } else if (/[+\-*/^_=<>]/.test(latex[i])) {
      tokens.push(latex[i]);
      i++;
    } else if (/\s/.test(latex[i])) {
      i++;
    } else {
      let sym = '';
      while (i < latex.length && !/[\s\\{}()\[\]|+\-*/^_=<>]/.test(latex[i])) {
        sym += latex[i];
        i++;
      }
      if (sym) tokens.push(sym);
    }
  }
  return tokens;
};

const extractFeatureVector = (latex: string): FeatureVector => {
  const commands = new Map<string, number>();
  const symbols = new Map<string, number>();
  const tokens = new Map<string, number>();

  const tokenList = tokenizeLatex(latex);

  let depth = 0;
  const depthHistory: number[] = [];
  let fracCount = 0;
  let sqrtCount = 0;
  let subSupCount = 0;

  for (const token of tokenList) {
    tokens.set(token, (tokens.get(token) || 0) + 1);

    if (token.startsWith('\\')) {
      const cmd = token.slice(1);
      commands.set(cmd, (commands.get(cmd) || 0) + 1);
      if (cmd === 'frac') fracCount++;
      if (cmd === 'sqrt') sqrtCount++;
    } else if (token === '{' || token === '(' || token === '[') {
      depth++;
      depthHistory.push(depth);
    } else if (token === '}' || token === ')' || token === ']') {
      depthHistory.push(depth);
      depth = Math.max(0, depth - 1);
    } else if (token === '^' || token === '_') {
      subSupCount++;
      depthHistory.push(depth + 1);
    } else {
      symbols.set(token, (symbols.get(token) || 0) + 1);
      depthHistory.push(depth);
    }
  }

  const avgDepth = depthHistory.length > 0 ? depthHistory.reduce((a, b) => a + b, 0) / depthHistory.length : 0;
  const maxDepth = depthHistory.length > 0 ? Math.max(...depthHistory) : 0;

  const structure: number[] = [
    tokenList.length,
    depth,
    avgDepth,
    maxDepth,
    fracCount,
    sqrtCount,
    subSupCount,
    commands.size,
    symbols.size,
  ];

  return { commands, symbols, tokens, structure };
};

const cosineSimilarity = (vecA: Map<string, number>, vecB: Map<string, number>): number => {
  const allKeys = new Set([...vecA.keys(), ...vecB.keys()]);
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;

  for (const key of allKeys) {
    const a = vecA.get(key) || 0;
    const b = vecB.get(key) || 0;
    dotProduct += a * b;
    normA += a * a;
    normB += b * b;
  }

  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom === 0 ? 0 : dotProduct / denom;
};

const euclideanDistance = (vecA: number[], vecB: number[]): number => {
  const maxLen = Math.max(vecA.length, vecB.length);
  let sum = 0;
  for (let i = 0; i < maxLen; i++) {
    const a = vecA[i] ?? 0;
    const b = vecB[i] ?? 0;
    sum += (a - b) ** 2;
  }
  return Math.sqrt(sum);
};

const normalizeVector = (vec: number[]): number[] => {
  const maxAbs = Math.max(...vec.map(Math.abs), 1);
  return vec.map((v) => v / maxAbs);
};

interface SimilarityResult {
  formula: Formula;
  similarity: number;
  components: {
    commandSim: number;
    symbolSim: number;
    tokenSim: number;
    structureSim: number;
  };
}

export function computeSimilarity(latexA: string, latexB: string): number {
  if (latexA === latexB) return 1;
  if (!latexA.trim() || !latexB.trim()) return 0;

  const featA = extractFeatureVector(latexA);
  const featB = extractFeatureVector(latexB);

  const commandSim = cosineSimilarity(featA.commands, featB.commands);
  const symbolSim = cosineSimilarity(featA.symbols, featB.symbols);
  const tokenSim = cosineSimilarity(featA.tokens, featB.tokens);

  const structA = normalizeVector(featA.structure);
  const structB = normalizeVector(featB.structure);
  const structDist = euclideanDistance(structA, structB);
  const structureSim = 1 / (1 + structDist);

  const hasCommonEnvironment = detectCommonEnvironment(latexA, latexB);
  const hasSameMatrixSize = detectMatrixSizeMatch(latexA, latexB);

  let total = 0.3 * commandSim + 0.25 * symbolSim + 0.25 * tokenSim + 0.2 * structureSim;

  if (hasCommonEnvironment) total += 0.05;
  if (hasSameMatrixSize) total += 0.05;

  return Math.min(1, Math.max(0, total));
}

function detectCommonEnvironment(a: string, b: string): boolean {
  const envPattern = /\\begin\{(\w+)\}/g;
  const envsA = new Set<string>();
  const envsB = new Set<string>();

  let match: RegExpExecArray | null;
  while ((match = envPattern.exec(a)) !== null) envsA.add(match[1]);
  envPattern.lastIndex = 0;
  while ((match = envPattern.exec(b)) !== null) envsB.add(match[1]);

  for (const env of envsA) {
    if (envsB.has(env)) return true;
  }
  return false;
}

function detectMatrixSizeMatch(a: string, b: string): boolean {
  const getMatrixSize = (latex: string): { rows: number; cols: number }[] => {
    const envPattern = /\\begin\{(pmatrix|bmatrix|vmatrix|Vmatrix|array|cases)\}([\s\S]*?)\\end\{\1\}/g;
    const sizes: { rows: number; cols: number }[] = [];
    let match: RegExpExecArray | null;

    while ((match = envPattern.exec(latex)) !== null) {
      const content = match[2];
      const rows = content.split('\\\\').filter((r) => r.trim()).length;
      const firstRow = content.split('\\\\')[0] || '';
      const cols = firstRow.split('&').length;
      sizes.push({ rows, cols });
    }
    return sizes;
  };

  const sizesA = getMatrixSize(a);
  const sizesB = getMatrixSize(b);

  for (const sa of sizesA) {
    for (const sb of sizesB) {
      if (sa.rows === sb.rows && sa.cols === sb.cols) return true;
    }
  }
  return false;
}

export function findSimilarFormulas(
  targetLatex: string,
  formulaLibrary: Formula[],
  threshold: number = 0.4,
  limit: number = 5,
): SimilarityResult[] {
  if (!targetLatex.trim()) return [];

  const results: SimilarityResult[] = [];

  for (const formula of formulaLibrary) {
    if (formula.latex === targetLatex) continue;

    const similarity = computeSimilarity(targetLatex, formula.latex);

    if (similarity >= threshold) {
      const featA = extractFeatureVector(targetLatex);
      const featB = extractFeatureVector(formula.latex);

      results.push({
        formula,
        similarity,
        components: {
          commandSim: cosineSimilarity(featA.commands, featB.commands),
          symbolSim: cosineSimilarity(featA.symbols, featB.symbols),
          tokenSim: cosineSimilarity(featA.tokens, featB.tokens),
          structureSim: (() => {
            const structA = normalizeVector(featA.structure);
            const structB = normalizeVector(featB.structure);
            const dist = euclideanDistance(structA, structB);
            return 1 / (1 + dist);
          })(),
        },
      });
    }
  }

  return results
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, limit);
}

export function getSimilarityLabel(similarity: number): { label: string; color: string } {
  if (similarity >= 0.9) return { label: '极高', color: 'text-accent' };
  if (similarity >= 0.7) return { label: '高', color: 'text-accent' };
  if (similarity >= 0.5) return { label: '中', color: 'text-warning' };
  if (similarity >= 0.3) return { label: '低', color: 'text-danger' };
  return { label: '极低', color: 'text-danger' };
}
