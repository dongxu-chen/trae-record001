import { DiffLine } from './diff';
import { FoldableBlock } from './folding';
import { HighlightToken } from './customTokens';

export interface MinimapMarker {
  lineNumber: number;
  type: 'error' | 'warning' | 'info' | 'custom' | 'diff-add' | 'diff-remove';
  color?: string;
  label?: string;
}

export interface MinimapConfig {
  width?: number;
  lineHeight?: number;
  showMarkers?: boolean;
  showDiffMarkers?: boolean;
  showFoldMarkers?: boolean;
}

export function generateMinimapData(
  lines: string[],
  config: MinimapConfig = {}
): {
  lineHeights: number[];
  markers: MinimapMarker[];
  totalHeight: number;
} {
  const { lineHeight = 2 } = config;

  const lineHeights = lines.map(() => lineHeight);
  const totalHeight = lineHeights.reduce((sum, h) => sum + h, 0);

  return {
    lineHeights,
    markers: [],
    totalHeight,
  };
}

export function addDiffMarkers(
  markers: MinimapMarker[],
  diffLines: DiffLine[]
): MinimapMarker[] {
  const result = [...markers];

  diffLines.forEach((line, index) => {
    if (line.type === 'added') {
      result.push({
        lineNumber: line.lineNumber > 0 ? line.lineNumber : index + 1,
        type: 'diff-add',
        color: '#28a745',
      });
    } else if (line.type === 'removed') {
      result.push({
        lineNumber: line.originalLineNumber > 0 ? line.originalLineNumber : index + 1,
        type: 'diff-remove',
        color: '#dc3545',
      });
    }
  });

  return result;
}

export function addFoldMarkers(
  markers: MinimapMarker[],
  blocks: FoldableBlock[]
): MinimapMarker[] {
  const result = [...markers];

  blocks.forEach((block) => {
    result.push({
      lineNumber: block.startLine,
      type: 'custom',
      color: '#6c757d',
      label: `${block.type}: ${block.label}`,
    });
  });

  return result;
}

export function addTokenMarkers(
  markers: MinimapMarker[],
  lines: string[],
  tokens: HighlightToken[]
): MinimapMarker[] {
  const result = [...markers];

  lines.forEach((line, index) => {
    for (const token of tokens) {
      const pattern = typeof token.pattern === 'string' ? new RegExp(`\\b${token.pattern}\\b`) : token.pattern;
      if (pattern.test(line)) {
        result.push({
          lineNumber: index + 1,
          type: 'custom',
          color: token.color,
        });
        break;
      }
    }
  });

  return result;
}

export function scrollToLine(
  container: HTMLElement,
  lineNumber: number,
  totalLines: number
): void {
  const scrollPercentage = (lineNumber - 1) / Math.max(1, totalLines - 1);
  const scrollTop = scrollPercentage * (container.scrollHeight - container.clientHeight);
  container.scrollTo({ top: scrollTop, behavior: 'smooth' });
}

export function getLineFromScrollPosition(
  scrollTop: number,
  container: HTMLElement,
  totalLines: number
): number {
  const scrollPercentage = scrollTop / Math.max(1, container.scrollHeight - container.clientHeight);
  return Math.floor(scrollPercentage * (totalLines - 1)) + 1;
}
