import React from 'react';

function Summary({ summary, report }) {
  return (
    <div className="summary">
      <div className="summary-card passed">
        <div className="number">{summary.passed}</div>
        <div className="label">通过</div>
      </div>
      <div className="summary-card errors">
        <div className="number">{summary.errors}</div>
        <div className="label">错误</div>
      </div>
      <div className="summary-card warnings">
        <div className="number">{summary.warnings}</div>
        <div className="label">警告</div>
      </div>
      <div className="summary-card infos">
        <div className="number">{summary.skipped}</div>
        <div className="label">跳过</div>
      </div>
      {report && (
        <div className="summary-card" style={{ borderColor: '#888' }}>
          <div className="number" style={{ color: '#888' }}>{summary.total_checks}</div>
          <div className="label">总检查项</div>
        </div>
      )}
    </div>
  );
}

export default Summary;
