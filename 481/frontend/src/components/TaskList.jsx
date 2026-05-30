import React from 'react';

function getLevelClass(level) {
  return (level || '').toLowerCase();
}

function getImportanceClass(importance) {
  switch (importance?.toUpperCase()) {
    case 'CRITICAL': return 'importance-critical';
    case 'HIGH': return 'importance-high';
    case 'MEDIUM': return 'importance-medium';
    default: return 'importance-low';
  }
}

function getImportanceLabel(importance) {
  switch (importance?.toUpperCase()) {
    case 'CRITICAL': return '关键';
    case 'HIGH': return '高';
    case 'MEDIUM': return '中';
    default: return '低';
  }
}

export default function TaskList({ tasks, selectedTask, onSelect }) {
  return (
    <div className="card">
      <div className="card-title">🎯 任务健康度总览</div>
      <div className="task-list">
        {tasks.map(task => (
          <div
            key={task.taskName}
            className={`task-item ${selectedTask === task.taskName ? 'selected' : ''}`}
            onClick={() => onSelect(task.taskName)}
          >
            <div className="task-item-left">
              <div className={`score-ring ${getLevelClass(task.scoreLevel)}`}>
                {task.overallScore}
              </div>
              <div>
                <div className="task-name">
                  {task.taskName}
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span className={`task-level ${getLevelClass(task.scoreLevel)}`}>
                    {task.scoreLevel}
                  </span>
                  {task.importanceLevel && (
                    <span className={`importance-badge ${getImportanceClass(task.importanceLevel)}`}>
                      {getImportanceLabel(task.importanceLevel)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
