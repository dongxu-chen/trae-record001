import React, { useState, useEffect, useRef, useCallback } from 'react';
import { LezerParser } from '../lezer/parser';
import { SyntaxHighlighter, highlightCSS } from '../lezer/highlighter';
import { LSPProvider } from '../lezer/lsp';
import type { Language, CodeSnippetOptions, CompletionItem, Definition } from '../lezer/types';

interface LezerCodeSnippetProps {
  code: string;
  language: Language;
  showLineNumbers?: boolean;
  theme?: 'dark' | 'light';
  enableFolding?: boolean;
  enableLSP?: boolean;
  showMinimap?: boolean;
  height?: string | number;
  width?: string | number;
  readOnly?: boolean;
}

const LezerCodeSnippet: React.FC<LezerCodeSnippetProps> = ({
  code,
  language,
  showLineNumbers = true,
  theme = 'dark',
  enableFolding = true,
  enableLSP = false,
  showMinimap = false,
  height = 'auto',
  width = '100%',
  readOnly = true,
}) => {
  const [highlightedLines, setHighlightedLines] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [foldedBlocks, setFoldedBlocks] = useState<Set<string>>(new Set());
  const [showCompletions, setShowCompletions] = useState(false);
  const [completions, setCompletions] = useState<CompletionItem[]>([]);
  const [cursorPosition, setCursorPosition] = useState({ line: 0, column: 0 });

  const parserRef = useRef<LezerParser | null>(null);
  const lspRef = useRef<LSPProvider | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!parserRef.current) {
      parserRef.current = new LezerParser(language);
    }
    if (enableLSP && !lspRef.current) {
      lspRef.current = new LSPProvider(language);
    }
  }, [language, enableLSP]);

  useEffect(() => {
    const startTime = performance.now();
    setIsLoading(true);

    try {
      if (parserRef.current) {
        const parseStart = performance.now();
        const parseResult = parserRef.current.parse(code);
        const parseTime = performance.now() - parseStart;

        const highlightStart = performance.now();
        const highlighter = new SyntaxHighlighter(parseResult.tree, code);
        const lines = highlighter.renderToLines();
        const highlightTime = performance.now() - highlightStart;

        setHighlightedLines(lines);

        console.log(`[Lezer] Parse: ${parseTime.toFixed(2)}ms, Highlight: ${highlightTime.toFixed(2)}ms, Nodes: ${parseResult.nodeCount}`);

        if (lspRef.current) {
          lspRef.current.updateText(code);
        }
      }
    } catch (error) {
      console.error('Syntax highlighting error:', error);
      setHighlightedLines(code.split('\n'));
    } finally {
      setIsLoading(false);
    }
  }, [code, language]);

  const handleToggleFold = useCallback((blockId: string) => {
    setFoldedBlocks((prev) => {
      const next = new Set(prev);
      if (next.has(blockId)) {
        next.delete(blockId);
      } else {
        next.add(blockId);
      }
      return next;
    });
  }, []);

  const handleGoToDefinition = useCallback(() => {
    if (!lspRef.current) return;

    const position = lspRef.current.positionToOffset(cursorPosition);
    const definition = lspRef.current.getDefinition(position);

    if (definition) {
      const defPos = lspRef.current.offsetToPosition(definition.selectionStart);
      console.log(`Definition found at line ${defPos.line + 1}, column ${defPos.character + 1}`);
    }
  }, [cursorPosition]);

  const handleGetCompletions = useCallback(() => {
    if (!lspRef.current) return;

    const position = lspRef.current.positionToOffset(cursorPosition);
    const items = lspRef.current.getCompletions(position);
    setCompletions(items);
    setShowCompletions(true);
  }, [cursorPosition]);

  const themeClass = theme === 'light' ? 'light-theme' : 'dark-theme';
  const lineCount = highlightedLines.length;

  return (
    <div
      ref={containerRef}
      className={`lezer-code-snippet ${themeClass}`}
      style={{
        width,
        height,
        overflow: height !== 'auto' ? 'auto' : undefined,
      }}
    >
      <style>{highlightCSS}</style>

      {isLoading && (
        <div className="code-loading">
          <div className="loading-spinner"></div>
          <span>解析代码中...</span>
        </div>
      )}

      <div className="code-container" style={{ opacity: isLoading ? 0.5 : 1 }}>
        {showLineNumbers && (
          <div className="line-numbers" aria-hidden="true">
            {Array.from({ length: lineCount }, (_, i) => (
              <div key={i} className="line-number">
                {enableFolding && (
                  <button
                    className="fold-button"
                    onClick={() => handleToggleFold(`line-${i}`)}
                    title="折叠/展开"
                  >
                    {foldedBlocks.has(`line-${i}`) ? '▶' : '▼'}
                  </button>
                )}
                {i + 1}
              </div>
            ))}
          </div>
        )}

        <div className="code-content">
          {highlightedLines.map((lineHtml, index) => (
            <div
              key={index}
              className="code-line"
              data-line={index + 1}
            >
              <code dangerouslySetInnerHTML={{ __html: lineHtml || ' ' }} />
            </div>
          ))}
        </div>

        {showMinimap && (
          <div className="minimap">
            <div className="minimap-content">
              {highlightedLines.map((_, i) => (
                <div key={i} className="minimap-line" style={{ opacity: Math.min(1, 10 / lineCount) }} />
              ))}
            </div>
            <div className="minimap-viewport" />
          </div>
        )}
      </div>

      {enableLSP && showCompletions && (
        <div className="completion-dropdown">
          {completions.slice(0, 10).map((item, index) => (
            <div key={index} className="completion-item">
              <span className={`completion-kind ${item.kind}`}>{item.kind[0].toUpperCase()}</span>
              <span className="completion-label">{item.label}</span>
              {item.detail && <span className="completion-detail">{item.detail}</span>}
            </div>
          ))}
        </div>
      )}

      <style>{`
        .lezer-code-snippet {
          font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
          font-size: 14px;
          line-height: 1.6;
          border-radius: 8px;
          overflow: hidden;
          position: relative;
        }

        .dark-theme {
          background: #1e1e1e;
          color: #d4d4d4;
        }

        .light-theme {
          background: #ffffff;
          color: #333333;
        }

        .code-loading {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(30, 30, 30, 0.8);
          z-index: 10;
          gap: 8px;
        }

        .light-theme .code-loading {
          background: rgba(255, 255, 255, 0.8);
        }

        .loading-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid #555;
          border-top-color: #007acc;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .code-container {
          display: flex;
          min-height: 100%;
        }

        .line-numbers {
          display: flex;
          flex-direction: column;
          padding: 16px 8px;
          background: #1e1e1e;
          border-right: 1px solid #333;
          user-select: none;
          text-align: right;
          min-width: 60px;
          color: #858585;
        }

        .light-theme .line-numbers {
          background: #f5f5f5;
          border-right-color: #ddd;
          color: #999;
        }

        .line-number {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 4px;
          padding-right: 4px;
        }

        .fold-button {
          background: none;
          border: none;
          color: #858585;
          cursor: pointer;
          font-size: 10px;
          padding: 0;
          width: 14px;
          height: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: transform 0.2s ease;
        }

        .fold-button:hover {
          color: #ccc;
        }

        .code-content {
          flex: 1;
          padding: 16px;
          overflow-x: auto;
        }

        .code-line {
          white-space: pre;
          min-height: 1.6em;
        }

        .code-line code {
          display: inline;
        }

        .minimap {
          width: 80px;
          min-width: 80px;
          position: relative;
          background: #252526;
          border-left: 1px solid #333;
          overflow: hidden;
        }

        .light-theme .minimap {
          background: #f0f0f0;
          border-left-color: #ddd;
        }

        .minimap-content {
          transform: scale(0.125);
          transform-origin: top left;
          width: 800%;
          overflow: hidden;
        }

        .minimap-line {
          height: 1.6em;
          background: rgba(255, 255, 255, 0.1);
        }

        .light-theme .minimap-line {
          background: rgba(0, 0, 0, 0.05);
        }

        .minimap-viewport {
          position: absolute;
          left: 0;
          right: 0;
          height: 60px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          top: 20%;
        }

        .light-theme .minimap-viewport {
          background: rgba(0, 0, 0, 0.05);
          border-color: rgba(0, 0, 0, 0.1);
        }

        .completion-dropdown {
          position: absolute;
          background: #252526;
          border: 1px solid #333;
          border-radius: 4px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
          max-height: 300px;
          overflow-y: auto;
          z-index: 100;
          min-width: 200px;
        }

        .light-theme .completion-dropdown {
          background: #ffffff;
          border-color: #ddd;
        }

        .completion-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 12px;
          cursor: pointer;
          transition: background 0.15s ease;
        }

        .completion-item:hover {
          background: #007acc;
        }

        .completion-kind {
          font-size: 12px;
          font-weight: bold;
          padding: 2px 6px;
          border-radius: 3px;
          background: #007acc;
          color: white;
          min-width: 16px;
          text-align: center;
        }

        .completion-kind.function {
          background: #61afef;
        }

        .completion-kind.class {
          background: #e5c07b;
        }

        .completion-kind.variable {
          background: #e06c75;
        }

        .completion-kind.property {
          background: #98c379;
        }

        .completion-kind.method {
          background: #56b6c2;
        }

        .completion-label {
          flex: 1;
        }

        .completion-detail {
          color: #858585;
          font-size: 12px;
        }
      `}</style>
    </div>
  );
};

export default LezerCodeSnippet;
