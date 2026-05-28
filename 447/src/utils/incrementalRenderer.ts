interface MatrixRegion {
  startIndex: number;
  endIndex: number;
  envName: string;
  content: string;
  id: string;
}

interface DiffResult {
  unchangedRegions: { start: number; end: number }[];
  changedRegions: { start: number; end: number; content: string }[];
  matrixRegionsChanged: string[];
  needsFullRerender: boolean;
}

function extractMatrixRegions(latex: string): MatrixRegion[] {
  const regions: MatrixRegion[] = [];
  const envPattern = /\\begin\{(pmatrix|bmatrix|vmatrix|Vmatrix|array|cases|aligned|gathered|matrix)\}/g;
  let match: RegExpExecArray | null;

  while ((match = envPattern.exec(latex)) !== null) {
    const envName = match[1];
    const contentStart = match.index + match[0].length;
    const endMarker = `\\end{${envName}}`;
    const endIndex = latex.indexOf(endMarker, contentStart);

    if (endIndex !== -1) {
      const fullStart = match.index;
      const fullEnd = endIndex + endMarker.length;
      regions.push({
        startIndex: fullStart,
        endIndex: fullEnd,
        envName,
        content: latex.slice(fullStart, fullEnd),
        id: `matrix_${fullStart}_${fullEnd}`,
      });
    }
  }

  return regions;
}

function findLCS(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  return dp[m][n];
}

function computeCellDiff(oldContent: string, newContent: string): {
  rowChanged: boolean[];
  totalRows: number;
} {
  const oldRows = oldContent.split('\\\\').map((r) => r.trim());
  const newRows = newContent.split('\\\\').map((r) => r.trim());

  const maxRows = Math.max(oldRows.length, newRows.length);
  const rowChanged: boolean[] = [];

  for (let i = 0; i < maxRows; i++) {
    const oldRow = oldRows[i] ?? '';
    const newRow = newRows[i] ?? '';

    if (oldRow === newRow) {
      rowChanged.push(false);
    } else {
      const lcsLen = findLCS(oldRow, newRow);
      const maxLen = Math.max(oldRow.length, newRow.length);
      const similarity = maxLen > 0 ? lcsLen / maxLen : 1;
      rowChanged.push(similarity < 0.85);
    }
  }

  return { rowChanged, totalRows: maxRows };
}

export function diffLatex(oldLatex: string, newLatex: string): DiffResult {
  if (oldLatex === newLatex) {
    return {
      unchangedRegions: [{ start: 0, end: oldLatex.length }],
      changedRegions: [],
      matrixRegionsChanged: [],
      needsFullRerender: false,
    };
  }

  if (!oldLatex || !newLatex) {
    return {
      unchangedRegions: [],
      changedRegions: [{ start: 0, end: newLatex.length, content: newLatex }],
      matrixRegionsChanged: [],
      needsFullRerender: true,
    };
  }

  const oldRegions = extractMatrixRegions(oldLatex);
  const newRegions = extractMatrixRegions(newLatex);

  const matrixRegionsChanged: string[] = [];

  const matchedPairs: { oldIdx: number; newIdx: number; cellChanges: boolean[] }[] = [];

  for (let ni = 0; ni < newRegions.length; ni++) {
    const newR = newRegions[ni];

    const oldContentStart = newR.startIndex < oldLatex.length
      ? oldLatex.indexOf(`\\begin{${newR.envName}}`, newR.startIndex)
      : -1;

    let bestOldIdx = -1;
    let bestSimilarity = -1;

    for (let oi = 0; oi < oldRegions.length; oi++) {
      if (oldRegions[oi].envName !== newR.envName) continue;
      if (matchedPairs.some((p) => p.oldIdx === oi)) continue;

      const lcsLen = findLCS(oldRegions[oi].content, newR.content);
      const maxLen = Math.max(oldRegions[oi].content.length, newR.content.length);
      const similarity = maxLen > 0 ? lcsLen / maxLen : 1;

      if (similarity > bestSimilarity) {
        bestSimilarity = similarity;
        bestOldIdx = oi;
      }
    }

    if (bestOldIdx >= 0 && bestSimilarity > 0.3) {
      const oldR = oldRegions[bestOldIdx];
      const oldInner = oldR.content.replace(/\\begin\{[^}]+\}/, '').replace(/\\end\{[^}]+\}$/, '');
      const newInner = newR.content.replace(/\\begin\{[^}]+\}/, '').replace(/\\end\{[^}]+\}$/, '');

      const { rowChanged } = computeCellDiff(oldInner, newInner);
      matchedPairs.push({ oldIdx: bestOldIdx, newIdx: ni, cellChanges: rowChanged });

      const changedCount = rowChanged.filter(Boolean).length;
      if (changedCount > 0) {
        matrixRegionsChanged.push(newR.id);
      }
    } else {
      matrixRegionsChanged.push(newR.id);
    }
  }

  for (let ni = 0; ni < newRegions.length; ni++) {
    if (!matchedPairs.some((p) => p.newIdx === ni)) {
      matrixRegionsChanged.push(newRegions[ni].id);
    }
  }

  const nonMatrixChanged = hasNonMatrixChanges(oldLatex, newLatex, oldRegions, newRegions);

  return {
    unchangedRegions: [],
    changedRegions: [{ start: 0, end: newLatex.length, content: newLatex }],
    matrixRegionsChanged,
    needsFullRerender: nonMatrixChanged || matrixRegionsChanged.length === 0,
  };
}

function hasNonMatrixChanges(
  oldLatex: string,
  newLatex: string,
  oldRegions: MatrixRegion[],
  newRegions: MatrixRegion[],
): boolean {
  const oldNonMatrix = removeMatrixRegions(oldLatex, oldRegions);
  const newNonMatrix = removeMatrixRegions(newLatex, newRegions);
  return oldNonMatrix !== newNonMatrix;
}

function removeMatrixRegions(latex: string, regions: MatrixRegion[]): string {
  if (regions.length === 0) return latex;
  let result = '';
  let lastEnd = 0;
  for (const r of regions) {
    result += latex.slice(lastEnd, r.startIndex);
    lastEnd = r.endIndex;
  }
  result += latex.slice(lastEnd);
  return result;
}

export function incrementalRender(
  oldLatex: string,
  newLatex: string,
  container: HTMLElement,
  renderFn: (latex: string, el: HTMLElement) => void,
): void {
  const diff = diffLatex(oldLatex, newLatex);

  if (diff.needsFullRerender || diff.matrixRegionsChanged.length === 0) {
    renderFn(newLatex, container);
    return;
  }

  const matrixElements = container.querySelectorAll('.katex .mtable, .katex .arraycolsep');

  if (matrixElements.length === 0) {
    renderFn(newLatex, container);
    return;
  }

  const rows = container.querySelectorAll('.katex .mtable .mtr');
  const newRegions = extractMatrixRegions(newLatex);

  if (rows.length === 0) {
    renderFn(newLatex, container);
    return;
  }

  let needsFallback = false;

  for (const region of diff.matrixRegionsChanged) {
    const regionInfo = newRegions.find((r) => r.id === region);
    if (!regionInfo) continue;

    const inner = regionInfo.content.replace(/\\begin\{[^}]+\}/, '').replace(/\\end\{[^}]+\}$/, '');
    const rowStrs = inner.split('\\\\').map((r) => r.trim());

    for (let i = 0; i < rowStrs.length && i < rows.length; i++) {
      const row = rows[i] as HTMLElement;
      if (row) {
        row.style.transition = 'background-color 0.3s ease';
        row.style.backgroundColor = 'rgba(16, 185, 129, 0.15)';
        setTimeout(() => {
          row.style.backgroundColor = 'transparent';
        }, 800);
      }
    }
  }

  if (needsFallback) {
    renderFn(newLatex, container);
    return;
  }

  renderFn(newLatex, container);

  requestAnimationFrame(() => {
    const newRows = container.querySelectorAll('.katex .mtable .mtr');
    for (const region of diff.matrixRegionsChanged) {
      const regionInfo = newRegions.find((r) => r.id === region);
      if (!regionInfo) continue;

      const inner = regionInfo.content.replace(/\\begin\{[^}]+\}/, '').replace(/\\end\{[^}]+\}$/, '');
      const rowStrs = inner.split('\\\\').map((r) => r.trim());

      for (let i = 0; i < rowStrs.length && i < newRows.length; i++) {
        const row = newRows[i] as HTMLElement;
        if (row) {
          row.style.transition = 'background-color 0.4s ease';
          row.style.backgroundColor = 'rgba(16, 185, 129, 0.2)';
          setTimeout(() => {
            row.style.backgroundColor = 'transparent';
          }, 1000);
        }
      }
    }
  });
}
