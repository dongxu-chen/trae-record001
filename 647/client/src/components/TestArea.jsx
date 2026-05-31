import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { testPattern, testPatternChunked, highlightMatches } from '../utils/regexEngine';

const CHUNK_SIZE_THRESHOLD = 50000;
const CHUNK_SIZE = 10000;

const TestArea = ({ pattern, testText, onTestTextChange }) => {
  const [flags, setFlags] = useState({
    g: true,
    i: false,
    m: false
  });
  const [useChunked, setUseChunked] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [asyncResult, setAsyncResult] = useState(null);
  const [progress, setProgress] = useState(0);

  const flagString = useMemo(() => {
    return Object.entries(flags)
      .filter(([, value]) => value)
      .map(([key]) => key)
      .join('');
  }, [flags]);

  const textLength = useMemo(() => testText?.length || 0, [testText]);
  const shouldUseChunked = textLength > CHUNK_SIZE_THRESHOLD;

  const syncResult = useMemo(() => {
    if (useChunked || isTesting) return null;
    return testPattern(pattern, testText, flagString);
  }, [pattern, testText, flagString, useChunked, isTesting]);

  const runChunkedTest = useCallback(async () => {
    if (!pattern || !testText) {
      setAsyncResult({ matches: [], isValid: true, chunks: 0 });
      return;
    }

    setIsTesting(true);
    setProgress(0);
    
    try {
      const result = await testPatternChunked(pattern, testText, flagString, CHUNK_SIZE);
      setAsyncResult(result);
    } catch (error) {
      setAsyncResult({ matches: [], isValid: false, error: error.message, chunks: 0 });
    } finally {
      setIsTesting(false);
      setProgress(100);
    }
  }, [pattern, testText, flagString]);

  useEffect(() => {
    if (useChunked && pattern && testText) {
      const timer = setTimeout(() => {
        runChunkedTest();
      }, 500);
      return () => clearTimeout(timer);
    } else {
      setAsyncResult(null);
    }
  }, [pattern, testText, useChunked, runChunkedTest]);

  const result = useChunked ? asyncResult : syncResult;

  const toggleFlag = (flag) => {
    setFlags(prev => ({
      ...prev,
      [flag]: !prev[flag]
    }));
  };

  const highlightedText = useMemo(() => {
    if (!result || !result.isValid || result.matches.length === 0) {
      return testText;
    }
    return highlightMatches(testText, result.matches);
  }, [testText, result]);

  const displayText = useMemo(() => {
    if (textLength <= 2000 || !result || result.matches.length === 0) {
      return highlightedText;
    }
    const firstMatchIndex = result.matches[0]?.index || 0;
    const start = Math.max(0, firstMatchIndex - 100);
    const end = Math.min(testText.length, start + 2000);
    const preview = testText.slice(start, end);
    const offsetMatches = result.matches
      .filter(m => m.index >= start && m.index + m.length <= end)
      .map(m => ({ ...m, index: m.index - start }));
    return highlightMatches(preview, offsetMatches) + 
      (end < testText.length ? `<span style="color:#999">... (共 ${textLength} 字符，仅显示匹配附近内容)</span>` : '');
  }, [testText, highlightedText, textLength, result]);

  return (
    <div className="test-area">
      <div className="flags-section">
        <label className="flag-item">
          <input
            type="checkbox"
            checked={flags.g}
            onChange={() => toggleFlag('g')}
          />
          <span>全局匹配 (g)</span>
        </label>
        <label className="flag-item">
          <input
            type="checkbox"
            checked={flags.i}
            onChange={() => toggleFlag('i')}
          />
          <span>忽略大小写 (i)</span>
        </label>
        <label className="flag-item">
          <input
            type="checkbox"
            checked={flags.m}
            onChange={() => toggleFlag('m')}
          />
          <span>多行模式 (m)</span>
        </label>
      </div>

      {shouldUseChunked && (
        <div style={{ 
          padding: '10px 14px', 
          background: '#dbeafe', 
          border: '1px solid #3b82f6', 
          borderRadius: '6px', 
          marginBottom: '12px',
          fontSize: '12px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span style={{ color: '#1e40af' }}>
            📝 检测到大文本 ({(textLength / 1000).toFixed(1)}KB)，建议启用分块测试
          </span>
          <label className="flag-item" style={{ margin: 0 }}>
            <input
              type="checkbox"
              checked={useChunked}
              onChange={(e) => setUseChunked(e.target.checked)}
            />
            <span>启用分块</span>
          </label>
        </div>
      )}

      <textarea
        className="test-input"
        placeholder="在此输入测试文本，系统将实时显示匹配结果..."
        value={testText}
        onChange={(e) => onTestTextChange(e.target.value)}
      />

      {useChunked && isTesting && (
        <div style={{ marginTop: '12px', textAlign: 'center' }}>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '6px' }}>
            正在分块测试中... {progress}%
          </div>
          <div style={{ 
            width: '100%', 
            height: '6px', 
            background: '#e5e7eb', 
            borderRadius: '3px',
            overflow: 'hidden'
          }}>
            <div style={{ 
              width: `${progress}%`, 
              height: '100%', 
              background: 'linear-gradient(90deg, #667eea, #764ba2)',
              transition: 'width 0.3s ease'
            }} />
          </div>
        </div>
      )}

      {result && !result.isValid && (
        <div style={{ marginTop: '16px', padding: '12px', background: '#fee2e2', color: '#dc2626', borderRadius: '8px', fontSize: '13px' }}>
          ⚠️ 正则表达式语法错误: {result.error}
        </div>
      )}

      {result && result.isValid && pattern && testText && (
        <div className="test-results">
          <div className="results-header">
            <span>匹配结果 {useChunked && result.chunks && <span style={{ color: '#667eea', marginLeft: '8px' }}>({result.chunks} 块)</span>}</span>
            <span className="match-count">
              找到 {result.matches.length} 个匹配
            </span>
          </div>

          {result.matches.length > 0 ? (
            <>
              <div style={{ marginBottom: '12px', padding: '12px', background: 'white', borderRadius: '6px', fontSize: '13px', lineHeight: '1.8', wordBreak: 'break-all' }}
                dangerouslySetInnerHTML={{ __html: displayText }}
              />
              <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                {result.matches.slice(0, 50).map((match, index) => (
                  <div key={index} className="match-item">
                    <span style={{ fontFamily: 'monospace' }}>"{match.text.length > 50 ? match.text.slice(0, 50) + '...' : match.text}"</span>
                    <span className="match-position">
                      位置: {match.index}
                      {match.chunk && <span style={{ marginLeft: '8px', color: '#667eea' }}>[块 {match.chunk}]</span>}
                    </span>
                  </div>
                ))}
                {result.matches.length > 50 && (
                  <div style={{ textAlign: 'center', padding: '8px', color: '#999', fontSize: '12px' }}>
                    ... 还有 {result.matches.length - 50} 个匹配结果
                  </div>
                )}
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '20px', color: '#999', fontSize: '13px' }}>
              未找到匹配项
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TestArea;
