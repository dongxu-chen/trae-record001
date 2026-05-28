export interface LatexPreset {
  id: string;
  name: string;
  description: string;
  packages: string[];
  preamble: string;
  transform: (latex: string) => string;
}

export const latexPresets: LatexPreset[] = [
  {
    id: 'plain',
    name: '纯LaTeX',
    description: '不添加任何宏包，仅使用基础LaTeX命令',
    packages: [],
    preamble: '',
    transform: (latex) => latex,
  },
  {
    id: 'amsmath',
    name: 'AMS Math',
    description: 'amsmath + amssymb + amsfonts，学术论文标准配置',
    packages: ['amsmath', 'amssymb', 'amsfonts'],
    preamble: '\\usepackage{amsmath}\n\\usepackage{amssymb}\n\\usepackage{amsfonts}',
    transform: (latex) => latex,
  },
  {
    id: 'mathtools',
    name: 'Mathtools',
    description: 'mathtools（含amsmath）+ amssymb，增强数学排版',
    packages: ['mathtools', 'amssymb'],
    preamble: '\\usepackage{mathtools}\n\\usepackage{amssymb}',
    transform: (latex) => {
      let result = latex;
      result = result.replace(/\\frac\{([^}]*)\}\{([^}]*)\}/g, '\\dfrac{$1}{$2}');
      result = result.replace(/\\left\(/g, '\\lparen');
      result = result.replace(/\\right\)/g, '\\rparen');
      return result;
    },
  },
  {
    id: 'physics',
    name: 'Physics',
    description: 'physics宏包，适合物理公式，含导数/积分简写',
    packages: ['physics', 'amsmath', 'amssymb'],
    preamble: '\\usepackage{physics}\n\\usepackage{amsmath}\n\\usepackage{amssymb}',
    transform: (latex) => {
      let result = latex;
      result = result.replace(/\\frac\{d\s*\}\\{d\s*([a-zA-Z]+)\}/g, '\\dv{$1}');
      result = result.replace(/\\frac\{\\partial\}\\{\\partial\s*([a-zA-Z]+)\}/g, '\\pdv{$1}');
      result = result.replace(/\\frac\{d\s*\}\\{d\s*([a-zA-Z]+)\s*\}\s*\(([^)]*)\)/g, '\\dv{$1}{$2}');
      result = result.replace(/\\frac\{\\partial\}\\{\\partial\s*([a-zA-Z]+)\s*\}\s*\(([^)]*)\)/g, '\\pdv{$1}{$2}');
      return result;
    },
  },
  {
    id: 'unicode-math',
    name: 'Unicode Math',
    description: 'unicode-math + fontspec，LuaLaTeX/XeLaTeX专用',
    packages: ['unicode-math', 'fontspec'],
    preamble: '\\usepackage{fontspec}\n\\usepackage{unicode-math}',
    transform: (latex) => {
      let result = latex;
      const symbolMap: [RegExp, string][] = [
        [/\\mathbb\{R\}/g, 'ℝ'],
        [/\\mathbb\{Z\}/g, 'ℤ'],
        [/\\mathbb\{N\}/g, 'ℕ'],
        [/\\mathbb\{Q\}/g, 'ℚ'],
        [/\\mathbb\{C\}/g, 'ℂ'],
        [/\\alpha/g, 'α'],
        [/\\beta/g, 'β'],
        [/\\gamma/g, 'γ'],
        [/\\delta/g, 'δ'],
        [/\\theta/g, 'θ'],
        [/\\lambda/g, 'λ'],
        [/\\mu/g, 'μ'],
        [/\\pi/g, 'π'],
        [/\\sigma/g, 'σ'],
        [/\\phi/g, 'φ'],
        [/\\omega/g, 'ω'],
        [/\\infty/g, '∞'],
        [/\\nabla/g, '∇'],
        [/\\partial/g, '∂'],
      ];
      for (const [pattern, replacement] of symbolMap) {
        result = result.replace(pattern, replacement);
      }
      return result;
    },
  },
];

export function generateLatexDocument(latex: string, preset: LatexPreset): string {
  const transformed = preset.transform(latex);
  const hasDisplayEnv = /\\begin\{(equation|align|gather|multline|cases|pmatrix|bmatrix|vmatrix)\}/.test(transformed);
  const displayLatex = hasDisplayEnv ? transformed : `\\[\n${transformed}\n\\]`;

  if (preset.id === 'plain') {
    return `\\documentclass{article}
${displayLatex}`;
  }

  return `\\documentclass{article}
${preset.preamble}
\\begin{document}
${displayLatex}
\\end{document}`;
}

export function generateSnippet(latex: string, preset: LatexPreset): string {
  const transformed = preset.transform(latex);
  if (preset.id === 'plain') {
    return transformed;
  }

  const lines: string[] = [];
  if (preset.preamble) {
    lines.push(`% Required packages: ${preset.packages.join(', ')}`);
    lines.push(preset.preamble);
    lines.push('');
  }
  lines.push(transformed);
  return lines.join('\n');
}
