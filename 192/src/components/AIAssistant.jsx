import React, { useState, useCallback, useEffect } from 'react';
import {
  getAICompletion,
  checkGrammar,
  getWritingSuggestions,
  rewriteSentence,
  insertCompletion,
  applySuggestion,
  getEditorText,
  debounceAI,
  AI_STYLES,
} from '../utils/aiService';

export const AIAssistant = ({ editor, isVisible, onClose }) => {
  const [activeTab, setActiveTab] = useState('completion');
  const [completion, setCompletion] = useState(null);
  const [grammarIssues, setGrammarIssues] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [rewriteText, setRewriteText] = useState('');
  const [rewriteStyle, setRewriteStyle] = useState('professional');
  const [rewriteResult, setRewriteResult] = useState(null);
  const [loading, setLoading] = useState({
    completion: false,
    grammar: false,
    suggestions: false,
    rewrite: false,
  });

  const triggerCompletion = useCallback(
    debounceAI(async () => {
      if (!editor || !editor.selection) return;
      
      setLoading(prev => ({ ...prev, completion: true }));
      const text = getEditorText(editor);
      const result = await getAICompletion(text, editor.selection.anchor);
      setCompletion(result);
      setLoading(prev => ({ ...prev, completion: false }));
    }),
    [editor]
  );

  const checkGrammarIssues = async () => {
    if (!editor) return;
    
    setLoading(prev => ({ ...prev, grammar: true }));
    const text = getEditorText(editor);
    const issues = await checkGrammar(text);
    setGrammarIssues(issues);
    setLoading(prev => ({ ...prev, grammar: false }));
  };

  const getSuggestions = async () => {
    if (!editor) return;
    
    setLoading(prev => ({ ...prev, suggestions: true }));
    const text = getEditorText(editor);
    const result = await getWritingSuggestions(text);
    setSuggestions(result);
    setLoading(prev => ({ ...prev, suggestions: false }));
  };

  const handleRewrite = async () => {
    if (!rewriteText.trim()) return;
    
    setLoading(prev => ({ ...prev, rewrite: true }));
    const result = await rewriteSentence(rewriteText, rewriteStyle);
    setRewriteResult(result);
    setLoading(prev => ({ ...prev, rewrite: false }));
  };

  const handleInsertCompletion = () => {
    if (completion && editor) {
      insertCompletion(editor, completion.text);
      setCompletion(null);
    }
  };

  const handleApplySuggestion = (suggestion) => {
    if (editor) {
      applySuggestion(editor, suggestion);
      setSuggestions(prev => prev.filter(s => s !== suggestion));
    }
  };

  const handleInsertRewrite = () => {
    if (rewriteResult && editor) {
      insertCompletion(editor, rewriteResult.rewritten);
    }
  };

  useEffect(() => {
    if (isVisible && editor && editor.selection) {
      triggerCompletion();
    }
  }, [isVisible, editor, triggerCompletion]);

  if (!isVisible) return null;

  return (
    <div className="ai-assistant-panel">
      <div className="ai-assistant-header">
        <h3>🤖 AI 写作助手</h3>
        <button onClick={onClose} className="close-btn">×</button>
      </div>

      <div className="ai-tabs">
        <button
          className={`ai-tab ${activeTab === 'completion' ? 'active' : ''}`}
          onClick={() => setActiveTab('completion')}
        >
          ✨ 智能补全
        </button>
        <button
          className={`ai-tab ${activeTab === 'grammar' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('grammar');
            checkGrammarIssues();
          }}
        >
          📝 语法检查
        </button>
        <button
          className={`ai-tab ${activeTab === 'suggest' ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('suggest');
            getSuggestions();
          }}
        >
          💡 优化建议
        </button>
        <button
          className={`ai-tab ${activeTab === 'rewrite' ? 'active' : ''}`}
          onClick={() => setActiveTab('rewrite')}
        >
          🔄 改写
        </button>
      </div>

      <div className="ai-tab-content">
        {activeTab === 'completion' && (
          <div className="ai-section">
            <button
              onClick={triggerCompletion}
              disabled={loading.completion}
              className="ai-action-btn"
            >
              {loading.completion ? '生成中...' : '🔄 生成补全建议'}
            </button>
            
            {completion && (
              <div className="completion-result">
                <div className="completion-text">{completion.text}</div>
                <div className="completion-meta">
                  <span className="confidence">
                    置信度: {(completion.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <button onClick={handleInsertCompletion} className="insert-btn">
                  插入
                </button>
                
                {completion.alternatives && completion.alternatives.length > 0 && (
                  <div className="alternatives">
                    <h4>其他建议:</h4>
                    {completion.alternatives.map((alt, idx) => (
                      <div
                        key={idx}
                        className="alternative-item"
                        onClick={() => {
                          if (editor) insertCompletion(editor, alt);
                          setCompletion(null);
                        }}
                      >
                        {alt}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'grammar' && (
          <div className="ai-section">
            <button
              onClick={checkGrammarIssues}
              disabled={loading.grammar}
              className="ai-action-btn"
            >
              {loading.grammar ? '检查中...' : '🔍 检查语法'}
            </button>
            
            {grammarIssues.length > 0 ? (
              <div className="grammar-issues">
                {grammarIssues.map((issue, idx) => (
                  <div key={idx} className={`grammar-issue ${issue.severity}`}>
                    <div className="issue-header">
                      <span className={`severity-badge ${issue.severity}`}>
                        {issue.severity === 'error' ? '❌ 错误' : 
                         issue.severity === 'warning' ? '⚠️ 警告' : 'ℹ️ 提示'}
                      </span>
                      <span className="issue-text">"{issue.text}"</span>
                    </div>
                    <div className="issue-suggestion">{issue.suggestion}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-issues">
                ✅ 未发现语法问题
              </div>
            )}
          </div>
        )}

        {activeTab === 'suggest' && (
          <div className="ai-section">
            <button
              onClick={getSuggestions}
              disabled={loading.suggestions}
              className="ai-action-btn"
            >
              {loading.suggestions ? '分析中...' : '💡 获取优化建议'}
            </button>
            
            {suggestions.length > 0 ? (
              <div className="suggestions-list">
                {suggestions.map((suggestion, idx) => (
                  <div key={idx} className="suggestion-item">
                    <div className="suggestion-original">
                      原文: <strong>"{suggestion.original}"</strong>
                    </div>
                    <div className="suggestion-reason">{suggestion.reason}</div>
                    <div className="suggestion-options">
                      {suggestion.suggestions.map((opt, optIdx) => (
                        <button
                          key={optIdx}
                          onClick={() => handleApplySuggestion({ ...suggestion, suggestions: [opt] })}
                          className="suggestion-opt-btn"
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-issues">
                ✨ 暂无优化建议
              </div>
            )}
          </div>
        )}

        {activeTab === 'rewrite' && (
          <div className="ai-section">
            <textarea
              value={rewriteText}
              onChange={(e) => setRewriteText(e.target.value)}
              placeholder="输入要改写的句子..."
              className="rewrite-input"
              rows={3}
            />
            
            <div className="style-selector">
              <label>选择风格:</label>
              <div className="style-buttons">
                {AI_STYLES.map(style => (
                  <button
                    key={style.id}
                    className={`style-btn ${rewriteStyle === style.id ? 'active' : ''}`}
                    onClick={() => setRewriteStyle(style.id)}
                  >
                    {style.icon} {style.name}
                  </button>
                ))}
              </div>
            </div>
            
            <button
              onClick={handleRewrite}
              disabled={loading.rewrite || !rewriteText.trim()}
              className="ai-action-btn"
            >
              {loading.rewrite ? '改写中...' : '🔄 开始改写'}
            </button>
            
            {rewriteResult && (
              <div className="rewrite-result">
                <div className="rewrite-comparison">
                  <div className="rewrite-original">
                    <strong>原文:</strong> {rewriteResult.original}
                  </div>
                  <div className="rewrite-arrow">↓</div>
                  <div className="rewrite-new">
                    <strong>改写:</strong> {rewriteResult.rewritten}
                  </div>
                </div>
                <button onClick={handleInsertRewrite} className="insert-btn">
                  插入改写结果
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
