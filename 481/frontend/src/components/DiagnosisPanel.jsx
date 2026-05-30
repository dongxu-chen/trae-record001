import React from 'react';

export default function DiagnosisPanel({ score }) {
  if (!score) return null;

  const hasIssue = score.diagnosis && !score.diagnosis.includes('healthy');

  return (
    <div className="card">
      <div className="card-title">🩺 异常诊断与优化建议</div>
      <div className="diagnosis-section">
        <div className={`diagnosis-card ${hasIssue ? 'issue' : 'suggestion'}`}>
          <h4>{hasIssue ? '⚠️ 诊断结果' : '✅ 诊断结果'}</h4>
          <p>{score.diagnosis || '未检测到异常'}</p>
        </div>
        <div className="diagnosis-card suggestion">
          <h4>💡 优化建议</h4>
          <p>{score.suggestion || '暂无优化建议'}</p>
        </div>

        <div style={{ marginTop: 16 }}>
          <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: 'var(--text-secondary)' }}>
            📊 各维度评分速览
          </h4>
          {score.dimensions?.map(dim => (
            <div key={dim.name} style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '8px 12px',
              background: 'var(--bg-primary)',
              borderRadius: 8,
              marginBottom: 6,
            }}>
              <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {dim.name === 'duration' ? '执行时长' : dim.name === 'success_rate' ? '成功率' : dim.name === 'frequency' ? '执行频率' : '资源消耗'}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 80, height: 4, background: '#334155', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{
                    width: `${dim.score}%`,
                    height: '100%',
                    borderRadius: 2,
                    background: dim.score >= 80 ? '#22c55e' : dim.score >= 60 ? '#eab308' : '#ef4444',
                  }} />
                </div>
                <span style={{ fontSize: 13, fontWeight: 600, minWidth: 28, textAlign: 'right', color: dim.score >= 80 ? '#22c55e' : dim.score >= 60 ? '#eab308' : '#ef4444' }}>
                  {dim.score}
                </span>
              </div>
            </div>
          ))}
        </div>

        {score.calculatedAt && (
          <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)', textAlign: 'right' }}>
            最后计算时间: {score.calculatedAt}
          </div>
        )}
      </div>
    </div>
  );
}
