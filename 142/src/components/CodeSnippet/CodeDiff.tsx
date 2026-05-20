import React, { useState, useEffect, useMemo, useRef } from 'react';
import { computeDiff, computeInlineDiff, DiffLine } from '../../utils/diff';
import { detectFoldableBlocks, getFoldedLines, findBlockAtLine } from '../../utils/folding';
import { HighlightToken, findCustomTokens } from '../../utils/customTokens';
import { MinimapMarker, scrollToLine, addDiffMarkers, addFoldMarkers, addTokenMarkers } from '../../utils/minimap';
import './CodeDiff.css';

export interface CodeDiffProps {
  oldCode: string;
  newCode: string;
  language: string;
  showLineNumbers?: boolean;
  showInlineDiff?: boolean;
  enableFolding?: boolean;
  customTokens?: HighlightToken[];
  showMinimap?: boolean;
  theme?: 'dark' | 'light';
}

const CodeDiff: React.FC<CodeDiffProps> = ({
  oldCode,
  newCode,
  language,
  showLineNumbers = true,
  showInlineDiff = true,
  enableFolding = true,
  customTokens = [],
  showMinimap = true,
  theme = 'dark',
}) => {
  const [foldedIds, setFoldedIds] = useState<Set<string>>(new Set());
  const [currentLine, setCurrentLine] = useState(1);
  const codeContainerRef = useRef<HTMLDivElement>(null);

  const diffResult = useMemo(() => computeDiff(oldCode, newCode), [oldCode, newCode]);
  const foldableBlocks = useMemo(() => detectFoldableBlocks(newCode), [newCode]);
  const foldedLines = useMemo(() => getFoldedLines(foldableBlocks, foldedIds), [foldableBlocks, foldedIds]);

  const markers = useMemo(() => {
    let result: MinimapMarker[] = [];
    result = addDiffMarkers(result, diffResult.lines);
    result = addFoldMarkers(result, foldableBlocks);
    result = addTokenMarkers(result, newCode.split('\n'), customTokens);
    return result;
  }, [diffResult.lines, foldableBlocks, newCode, customTokens]);

  const handleToggleFold = (lineNumber: number) => {
    const block = findBlockAtLine(foldableBlocks, lineNumber);
    if (block) {
      setFoldedIds((prev) => {
        const next = new Set(prev);
        if (next.has(block.id)) {
          next.delete(block.id);
        } else {
          next.add(block.id);
        }
        return next;
      });
    }
  };

  const handleMinimapClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!codeContainerRef.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickY = e.clientY - rect.top;
    const percentage = clickY / rect.height;
    const lineNumber = Math.floor(percentage * diffResult.lines.length) + 1;
    scrollToLine(codeContainerRef.current, lineNumber, diffResult.lines.length);
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    const line = Math.floor((target.scrollTop / (target.scrollHeight - target.clientHeight)) * diffResult.lines.length) + 1;
    setCurrentLine(line);
  };

  const renderInlineDiff = (oldLine: string, newLine: string, type: 'old' | 'new') => {
    if (!showInlineDiff) {
      return type === 'old' ? oldLine : newLine;
    }

    const { oldSegments, newSegments } = computeInlineDiff(oldLine, newLine);
    const segments = type === 'old' ? oldSegments : newSegments;

    return segments.map((segment, index) => {
      if (segment.modified) {
        return (
          <span key={index} className={`inline-diff-${type === 'old' ? 'remove' : 'add'}`}>
            {segment.text}
          </span>
        );
      }
      return <span key={index}>{segment.text}</span>;
    });
  };

  const renderLine = (line: DiffLine, index: number) => {
    const isFolded = line.type === 'unchanged' && foldedLines.has(line.lineNumber);
    if (isFolded) return null;

    const block = enableFolding ? findBlockAtLine(foldableBlocks, line.lineNumber) : null;
    const isBlockStart = block !== null;
    const isFoldedBlock = block ? foldedIds.has(block.id) : false;

    const tokensInLine = customTokens.length > 0 && line.content
      ? findCustomTokens(line.content, customTokens)
      : [];

    let content = line.content;
    if (tokensInLine.length > 0) {
      let result = '';
      let lastIndex = 0;
      for (const match of tokensInLine) {
        if (match.start > lastIndex) {
          result += content.slice(lastIndex, match.start);
        }
        const style = `color: ${match.token.color}; font-weight: ${match.token.fontWeight || 'normal'};`;
        result += `<span style="${style}">${match.text}</span>`;
        lastIndex = match.end;
      }
      if (lastIndex < content.length) {
        result += content.slice(lastIndex);
      }
      content = result;
    }

    return (
      <div key={index} className={`diff-row diff-${line.type}`}>
        {showLineNumbers && (
          <div className="line-number-cell">
            {enableFolding && isBlockStart && (
              <button
                className={`fold-button ${isFoldedBlock ? 'folded' : ''}`}
                onClick={() => handleToggleFold(line.lineNumber)}
                title={isFoldedBlock ? '展开' : '折叠'}
              >
                {isFoldedBlock ? '▶' : '▼'}
              </button>
            )}
            <span className="line-number">{line.originalLineNumber > 0 ? line.originalLineNumber : ''}</span>
            <span className="line-number">{line.lineNumber > 0 ? line.lineNumber : ''}</span>
          </div>
        )}
        <div className="code-cell">
          {isFoldedBlock && (
            <span className="fold-placeholder" onClick={() => handleToggleFold(line.lineNumber)}>
              {' '}
              {/* ... */} {block?.label} ({block?.endLine - block?.startLine} 行)
            </span>
          )}
          {!isFoldedBlock && (
            <code
              dangerouslySetInnerHTML={{
                __html: content,
              }}
            />
          )}
        </div>
      </div>
    );
  };

  const themeClass = theme === 'light' ? 'light-theme' : '';

  return (
    <div className={`code-diff-container ${themeClass}`}>
      <div className="diff-header">
        <div className="diff-stats">
          <span className="stat added">+ {diffResult.addedCount}</span>
          <span className="stat removed">- {diffResult.removedCount}</span>
          <span className="stat unchanged">~ {diffResult.unchangedCount}</span>
        </div>
      </div>
      <div className="diff-content">
        <div
          ref={codeContainerRef}
          className="code-container"
          onScroll={handleScroll}
        >
          {showLineNumbers && (
            <div className="line-number-header">
              <span>原始</span>
              <span>新</span>
            </div>
          )}
          {diffResult.lines.map((line, index) => renderLine(line, index))}
        </div>
        {showMinimap && (
          <div className="minimap" onClick={handleMinimapClick}>
            {markers.map((marker, index) => (
              <div
                key={index}
                className="minimap-marker"
                style={{
                  top: `${(marker.lineNumber / diffResult.lines.length) * 100}%`,
                  backgroundColor: marker.color,
                }}
                title={marker.label || `行 ${marker.lineNumber}`}
              />
            ))}
            <div
              className="minimap-viewport"
              style={{
                top: `${(currentLine / diffResult.lines.length) * 100}%`,
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default CodeDiff;
