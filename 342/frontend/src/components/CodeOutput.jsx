import React, { useState } from 'react';

const LANG_LABELS = {
  pseudocode: '伪代码',
  plantuml: 'PlantUML',
  stateMachine: 'JavaScript 状态机',
  python: 'Python',
  java: 'Java',
  go: 'Go',
  javascript: 'JavaScript',
};

const LANG_EXTENSIONS = {
  pseudocode: 'txt',
  plantuml: 'puml',
  stateMachine: 'js',
  python: 'py',
  java: 'java',
  go: 'go',
  javascript: 'js',
  text: 'txt',
};

export default function CodeOutput({ code, language, label }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = code;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    const ext = LANG_EXTENSIONS[language] || 'txt';
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `flowchart_${language}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const displayLabel = label || LANG_LABELS[language] || language;

  return (
    <div className="code-output-container">
      <div className="code-toolbar">
        <span className="code-lang-label">{displayLabel}</span>
        <div className="code-actions">
          <span className="code-stats">
            {code.split('\n').length} 行 | {(code.length / 1024).toFixed(1)} KB
          </span>
          <button className="action-btn" onClick={handleCopy}>
            {copied ? '已复制!' : '复制'}
          </button>
          <button className="action-btn" onClick={handleDownload}>
            下载
          </button>
        </div>
      </div>
      <pre className="code-block">
        <code>{code}</code>
      </pre>
    </div>
  );
}
