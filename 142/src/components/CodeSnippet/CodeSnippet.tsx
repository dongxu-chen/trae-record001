import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { copyToClipboard } from '../../utils/clipboard';
import { loadTheme } from '../../utils/themeLoader';
import { detectFoldableBlocks, getFoldedLines, findBlockAtLine } from '../../utils/folding';
import { HighlightToken, findCustomTokens } from '../../utils/customTokens';
import { MinimapMarker, scrollToLine, addFoldMarkers, addTokenMarkers } from '../../utils/minimap';
import Prism from 'prismjs';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-markup';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/components/prism-go';
import 'prismjs/components/prism-rust';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-bash';
import './CodeSnippet.css';

export interface CodeSnippetProps {
  code: string;
  language: string;
  showLineNumbers?: boolean;
  showCopyButton?: boolean;
  showThemeToggle?: boolean;
  defaultTheme?: 'dark' | 'light';
  useWorker?: boolean;
  enableFolding?: boolean;
  customTokens?: HighlightToken[];
  showMinimap?: boolean;
}

interface HighlightResponse {
  html: string;
  id: string;
  success: boolean;
  error?: string;
}

let worker: Worker | null = null;
let requestIdCounter = 0;
const pendingRequests = new Map<string, (response: HighlightResponse) => void>();

function getWorker(): Worker | null {
  if (typeof window === 'undefined' || !window.Worker) {
    return null;
  }

  if (!worker) {
    try {
      const workerBlob = new Blob([
        `
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-typescript.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-css.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-markup.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-java.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-c.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-cpp.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-go.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-rust.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-sql.min.js');
        importScripts('https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js');

        self.onmessage = (e) => {
          const { code, language, id } = e.data;
          try {
            const grammar = Prism.languages[language];
            if (!grammar) {
              throw new Error('Unsupported language: ' + language);
            }
            const html = Prism.highlight(code, grammar, language);
            self.postMessage({ html, id, success: true });
          } catch (error) {
            self.postMessage({
              html: '',
              id,
              success: false,
              error: error.message || 'Unknown error'
            });
          }
        };
      `,
      ], { type: 'application/javascript' });

      const workerUrl = URL.createObjectURL(workerBlob);
      worker = new Worker(workerUrl);

      worker.onmessage = (e: MessageEvent<HighlightResponse>) => {
        const callback = pendingRequests.get(e.data.id);
        if (callback) {
          callback(e.data);
          pendingRequests.delete(e.data.id);
        }
      };
    } catch (error) {
      console.warn('Failed to create Web Worker, falling back to main thread highlighting');
      return null;
    }
  }

  return worker;
}

const CodeSnippet: React.FC<CodeSnippetProps> = ({
  code,
  language,
  showLineNumbers = true,
  showCopyButton = true,
  showThemeToggle = true,
  defaultTheme = 'dark',
  useWorker = true,
  enableFolding = true,
  customTokens = [],
  showMinimap = true,
}) => {
  const [theme, setTheme] = useState<'dark' | 'light'>(defaultTheme);
  const [copied, setCopied] = useState(false);
  const [highlightedHtml, setHighlightedHtml] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [foldedIds, setFoldedIds] = useState<Set<string>>(new Set());
  const [currentLine, setCurrentLine] = useState(1);
  const componentIdRef = useRef(`code-snippet-${Date.now()}`);
  const codeContainerRef = useRef<HTMLDivElement>(null);

  const lines = useMemo(() => code.split('\n'), [code]);
  const highlightedLines = useMemo(() => highlightedHtml.split('\n'), [highlightedHtml]);
  const foldableBlocks = useMemo(() => detectFoldableBlocks(code), [code]);
  const foldedLines = useMemo(() => getFoldedLines(foldableBlocks, foldedIds), [foldableBlocks, foldedIds]);

  const markers = useMemo(() => {
    let result: MinimapMarker[] = [];
    result = addFoldMarkers(result, foldableBlocks);
    result = addTokenMarkers(result, lines, customTokens);
    return result;
  }, [foldableBlocks, lines, customTokens]);

  useEffect(() => {
    loadTheme('dark');
    loadTheme('light');
  }, []);

  const highlightWithWorker = useCallback(async (codeToHighlight: string, lang: string): Promise<string> => {
    const workerInstance = useWorker ? getWorker() : null;

    if (!workerInstance) {
      const grammar = Prism.languages[lang];
      if (!grammar) {
        return codeToHighlight;
      }
      return Prism.highlight(codeToHighlight, grammar, lang);
    }

    return new Promise((resolve) => {
      const requestId = `${componentIdRef.current}-${++requestIdCounter}`;

      const timeoutId = setTimeout(() => {
        console.warn('Worker timeout, falling back to main thread');
        const grammar = Prism.languages[lang];
        if (!grammar) {
          resolve(codeToHighlight);
        } else {
          resolve(Prism.highlight(codeToHighlight, grammar, lang));
        }
        pendingRequests.delete(requestId);
      }, 5000);

      pendingRequests.set(requestId, (response) => {
        clearTimeout(timeoutId);
        if (response.success) {
          resolve(response.html);
        } else {
          console.warn('Worker highlighting failed:', response.error);
          const grammar = Prism.languages[lang];
          if (!grammar) {
            resolve(codeToHighlight);
          } else {
            resolve(Prism.highlight(codeToHighlight, grammar, lang));
          }
        }
      });

      workerInstance.postMessage({
        code: codeToHighlight,
        language: lang,
        id: requestId,
      });
    });
  }, [useWorker]);

  useEffect(() => {
    let mounted = true;

    const highlight = async () => {
      setIsLoading(true);
      try {
        const html = await highlightWithWorker(code, language);
        if (mounted) {
          setHighlightedHtml(html);
        }
      } catch (error) {
        console.error('Highlighting error:', error);
        if (mounted) {
          setHighlightedHtml(code);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    highlight();

    return () => {
      mounted = false;
    };
  }, [code, language, highlightWithWorker]);

  const handleCopy = async () => {
    const success = await copyToClipboard(code);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const toggleTheme = () => {
    setTheme((prev) => {
      const newTheme = prev === 'dark' ? 'light' : 'dark';
      return newTheme;
    });
  };

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
    const lineNumber = Math.floor(percentage * lines.length) + 1;
    scrollToLine(codeContainerRef.current, lineNumber, lines.length);
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    const line = Math.floor((target.scrollTop / (target.scrollHeight - target.clientHeight)) * lines.length) + 1;
    setCurrentLine(line);
  };

  const applyCustomTokens = (lineContent: string, lineIndex: number) => {
    if (customTokens.length === 0) return lineContent;

    const matches = findCustomTokens(lineContent, customTokens);
    if (matches.length === 0) return lineContent;

    let result = '';
    let lastIndex = 0;

    for (const match of matches) {
      if (match.start > lastIndex) {
        result += lineContent.slice(lastIndex, match.start);
      }

      const styleParts: string[] = [];
      if (match.token.color) styleParts.push(`color: ${match.token.color}`);
      if (match.token.backgroundColor) styleParts.push(`background-color: ${match.token.backgroundColor}`);
      if (match.token.fontWeight) styleParts.push(`font-weight: ${match.token.fontWeight}`);
      if (match.token.fontStyle) styleParts.push(`font-style: ${match.token.fontStyle}`);

      const className = match.token.className || 'custom-token';
      const style = styleParts.length > 0 ? ` style="${styleParts.join('; ')}"` : '';

      result += `<span class="${className}"${style}>${match.text}</span>`;
      lastIndex = match.end;
    }

    if (lastIndex < lineContent.length) {
      result += lineContent.slice(lastIndex);
    }

    return result;
  };

  const themeClass = theme === 'light' ? 'light-theme' : '';

  const renderLine = (lineContent: string, lineIndex: number) => {
    const lineNumber = lineIndex + 1;
    const isFolded = foldedLines.has(lineNumber);
    if (isFolded) return null;

    const block = enableFolding ? findBlockAtLine(foldableBlocks, lineNumber) : null;
    const isBlockStart = block !== null;
    const isFoldedBlock = block ? foldedIds.has(block.id) : false;

    const processedContent = applyCustomTokens(highlightedLines[lineIndex] || lineContent, lineIndex);

    return (
      <div key={lineIndex} className="code-row">
        {showLineNumbers && (
          <div className="line-number-cell">
            {enableFolding && isBlockStart && (
              <button
                className={`fold-button ${isFoldedBlock ? 'folded' : ''}`}
                onClick={() => handleToggleFold(lineNumber)}
                title={isFoldedBlock ? '展开' : '折叠'}
              >
                {isFoldedBlock ? '▶' : '▼'}
              </button>
            )}
            {lineNumber}
          </div>
        )}
        <div className="code-cell">
          {isFoldedBlock && (
            <span className="fold-placeholder" onClick={() => handleToggleFold(lineNumber)}>
              {' '}
              {/* ... */} {block?.label} ({block?.endLine - block?.startLine} 行)
            </span>
          )}
          {!isFoldedBlock && (
            <code
              dangerouslySetInnerHTML={{
                __html: processedContent,
              }}
            />
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`code-snippet-container ${themeClass}`}>
      <div className="code-snippet-header">
        <span className="language-label">{language}</span>
        <div className="header-actions">
          {showCopyButton && (
            <button
              className={`copy-btn ${copied ? 'copied' : ''}`}
              onClick={handleCopy}
            >
              {copied ? '✓ 已复制' : '📋 复制'}
            </button>
          )}
          {showThemeToggle && (
            <button className="theme-btn" onClick={toggleTheme}>
              {theme === 'dark' ? '☀️ 亮色' : '🌙 暗色'}
            </button>
          )}
        </div>
      </div>
      <div className="code-wrapper">
        {isLoading && (
          <div className="loading-overlay">
            <div className="loading-spinner"></div>
            <span>正在解析...</span>
          </div>
        )}
        <div className="code-content">
          <div
            ref={codeContainerRef}
            className="code-table"
            style={{ opacity: isLoading ? 0.3 : 1 }}
            onScroll={handleScroll}
          >
            {lines.map((line, index) => renderLine(line, index))}
          </div>
          {showMinimap && (
            <div className="minimap" onClick={handleMinimapClick}>
              {markers.map((marker, index) => (
                <div
                  key={index}
                  className="minimap-marker"
                  style={{
                    top: `${(marker.lineNumber / lines.length) * 100}%`,
                    backgroundColor: marker.color,
                  }}
                  title={marker.label || `行 ${marker.lineNumber}`}
                />
              ))}
              <div
                className="minimap-viewport"
                style={{
                  top: `${(currentLine / lines.length) * 100}%`,
                }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CodeSnippet;
