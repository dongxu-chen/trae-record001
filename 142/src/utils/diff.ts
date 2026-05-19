export type DiffLineType = 'added' | 'removed' | 'unchanged' | 'modified';

export interface DiffLine {
  type: DiffLineType;
  content: string;
  lineNumber: number;
  originalLineNumber?: number;
}

export interface DiffResult {
  lines: DiffLine[];
  addedCount: number;
  removedCount: number;
  unchangedCount: number;
}

function longestCommonSubsequence<T>(a: T[], b: T[], compare?: (x: T, y: T) => boolean): T[] {
  const cmp = compare || ((x, y) => x === y);
  const m = a.length;
  const n = b.length;
  const dp: number[][] = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (cmp(a[i - 1], b[j - 1])) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  const lcs: T[] = [];
  let i = m, j = n;
  while (i > 0 && j > 0) {
    if (cmp(a[i - 1], b[j - 1])) {
      lcs.unshift(a[i - 1]);
      i--;
      j--;
    } else if (dp[i - 1][j] > dp[i][j - 1]) {
      i--;
    } else {
      j--;
    }
  }

  return lcs;
}

export function computeDiff(oldCode: string, newCode: string): DiffResult {
  const oldLines = oldCode.split('\n');
  const newLines = newCode.split('\n');

  const normalize = (line: string) => line.trim().replace(/\s+/g, ' ');
  const lcs = longestCommonSubsequence(oldLines, newLines, (a, b) => normalize(a) === normalize(b));

  const result: DiffLine[] = [];
  let oldIdx = 0;
  let newIdx = 0;
  let lcsIdx = 0;

  let addedCount = 0;
  let removedCount = 0;
  let unchangedCount = 0;

  while (oldIdx < oldLines.length || newIdx < newLines.length) {
    const oldLine = oldLines[oldIdx];
    const newLine = newLines[newIdx];
    const lcsLine = lcs[lcsIdx];

    const isOldMatch = lcsLine !== undefined && normalize(oldLine || '') === normalize(lcsLine);
    const isNewMatch = lcsLine !== undefined && normalize(newLine || '') === normalize(lcsLine);

    if (isOldMatch && isNewMatch) {
      result.push({
        type: 'unchanged',
        content: newLine,
        lineNumber: newIdx + 1,
        originalLineNumber: oldIdx + 1,
      });
      unchangedCount++;
      oldIdx++;
      newIdx++;
      lcsIdx++;
    } else if (!isOldMatch && !isNewMatch && oldLine !== undefined && newLine !== undefined) {
      result.push({
        type: 'removed',
        content: oldLine,
        lineNumber: -1,
        originalLineNumber: oldIdx + 1,
      });
      result.push({
        type: 'added',
        content: newLine,
        lineNumber: newIdx + 1,
        originalLineNumber: -1,
      });
      removedCount++;
      addedCount++;
      oldIdx++;
      newIdx++;
    } else if (!isOldMatch && oldLine !== undefined) {
      result.push({
        type: 'removed',
        content: oldLine,
        lineNumber: -1,
        originalLineNumber: oldIdx + 1,
      });
      removedCount++;
      oldIdx++;
    } else if (!isNewMatch && newLine !== undefined) {
      result.push({
        type: 'added',
        content: newLine,
        lineNumber: newIdx + 1,
        originalLineNumber: -1,
      });
      addedCount++;
      newIdx++;
    } else {
      break;
    }
  }

  return {
    lines: result,
    addedCount,
    removedCount,
    unchangedCount,
  };
}

export function computeInlineDiff(oldLine: string, newLine: string): {
  oldSegments: { text: string; modified: boolean }[];
  newSegments: { text: string; modified: boolean }[];
} {
  const oldChars = oldLine.split('');
  const newChars = newLine.split('');
  const lcs = longestCommonSubsequence(oldChars, newChars);

  const oldSegments: { text: string; modified: boolean }[] = [];
  const newSegments: { text: string; modified: boolean }[] = [];

  let oldIdx = 0;
  let newIdx = 0;
  let lcsIdx = 0;

  let oldModified = '';
  let oldUnmodified = '';
  let newModified = '';
  let newUnmodified = '';

  while (oldIdx < oldChars.length || newIdx < newChars.length) {
    const oldChar = oldChars[oldIdx];
    const newChar = newChars[newIdx];
    const lcsChar = lcs[lcsIdx];

    const isOldMatch = lcsChar !== undefined && oldChar === lcsChar;
    const isNewMatch = lcsChar !== undefined && newChar === lcsChar;

    if (isOldMatch && isNewMatch) {
      if (oldModified) {
        oldSegments.push({ text: oldModified, modified: true });
        oldModified = '';
      }
      if (newModified) {
        newSegments.push({ text: newModified, modified: true });
        newModified = '';
      }
      oldUnmodified += oldChar;
      newUnmodified += newChar;
      oldIdx++;
      newIdx++;
      lcsIdx++;
    } else {
      if (oldUnmodified || newUnmodified) {
        oldSegments.push({ text: oldUnmodified, modified: false });
        newSegments.push({ text: newUnmodified, modified: false });
        oldUnmodified = '';
        newUnmodified = '';
      }
      if (!isOldMatch && oldChar !== undefined) {
        oldModified += oldChar;
        oldIdx++;
      }
      if (!isNewMatch && newChar !== undefined) {
        newModified += newChar;
        newIdx++;
      }
    }
  }

  if (oldModified) oldSegments.push({ text: oldModified, modified: true });
  if (oldUnmodified) oldSegments.push({ text: oldUnmodified, modified: false });
  if (newModified) newSegments.push({ text: newModified, modified: true });
  if (newUnmodified) newSegments.push({ text: newUnmodified, modified: false });

  return { oldSegments, newSegments };
}
