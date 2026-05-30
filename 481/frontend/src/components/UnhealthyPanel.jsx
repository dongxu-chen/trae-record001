import React from 'react';

export default function UnhealthyPanel({ tasks }) {
  if (!tasks || tasks.length === 0) return null;

  return (
    <div className="card" style={{ marginBottom: 24 }}>
      <div className="card-title">🚨 异常任务预警</div>
      <div className="unhealthy-grid">
        {tasks.map(task => (
          <div key={task.taskName} className="unhealthy-card">
            <div className="unhealthy-card-header">
              <span className="unhealthy-card-name">{task.taskName}</span>
              <span className="unhealthy-card-score">{task.overallScore}分</span>
            </div>
            <div className="unhealthy-card-diagnosis">
              <strong>诊断:</strong> {task.diagnosis}
            </div>
            <div className="unhealthy-card-suggestion">
              <strong>建议:</strong> {task.suggestion}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
