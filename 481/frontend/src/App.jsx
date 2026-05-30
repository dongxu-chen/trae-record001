import React, { useState, useEffect, useCallback } from 'react';
import { fetchDashboard, fetchScoreTrend, fetchUnhealthyTasks, triggerCalculation, fetchTaskScore } from './api';
import TaskList from './components/TaskList';
import ScoreDetail from './components/ScoreDetail';
import TrendChart from './components/TrendChart';
import DiagnosisPanel from './components/DiagnosisPanel';
import UnhealthyPanel from './components/UnhealthyPanel';
import HealthPrediction from './components/HealthPrediction';
import AutoRepairPanel from './components/AutoRepairPanel';
import SlaPredictionPanel from './components/SlaPredictionPanel';

export default function App() {
  const [dashboard, setDashboard] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedTaskDetail, setSelectedTaskDetail] = useState(null);
  const [trend, setTrend] = useState([]);
  const [unhealthy, setUnhealthy] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showPrediction, setShowPrediction] = useState(false);
  const [showAutoRepair, setShowAutoRepair] = useState(false);
  const [showSlaPrediction, setShowSlaPrediction] = useState(false);

  const loadDashboard = useCallback(async () => {
    try {
      const data = await fetchDashboard();
      setDashboard(data);
      if (!selectedTask && data.taskScores?.length > 0) {
        setSelectedTask(data.taskScores[0].taskName);
      }
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    }
  }, [selectedTask]);

  const loadData = useCallback(async () => {
    setLoading(true);
    await loadDashboard();
    try {
      const data = await fetchUnhealthyTasks(60);
      setUnhealthy(data);
    } catch (err) {
      console.error('Failed to load unhealthy tasks:', err);
    }
    setLoading(false);
  }, [loadDashboard]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadDashboard, 60000);
    return () => clearInterval(interval);
  }, [loadData, loadDashboard]);

  useEffect(() => {
    if (!selectedTask) return;
    setShowPrediction(false);
    setShowAutoRepair(false);
    setShowSlaPrediction(false);
    fetchScoreTrend(selectedTask, 24).then(setTrend).catch(console.error);
    fetchTaskScore(selectedTask).then(setSelectedTaskDetail).catch(console.error);
  }, [selectedTask]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await triggerCalculation();
      await loadData();
      if (selectedTask) {
        const trendData = await fetchScoreTrend(selectedTask, 24);
        setTrend(trendData);
        const detail = await fetchTaskScore(selectedTask);
        setSelectedTaskDetail(detail);
      }
    } catch (err) {
      console.error('Refresh failed:', err);
    }
    setRefreshing(false);
  };

  if (loading || !dashboard) {
    return (
      <div className="app">
        <div className="loading">
          <div className="spinner" />
          正在加载健康度数据...
        </div>
      </div>
    );
  }

  const selectedScore = selectedTaskDetail || dashboard.taskScores?.find(t => t.taskName === selectedTask);

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <h1>定时任务健康度评分工具</h1>
          <p>实时监控 · 智能评分 · 异常诊断 · 优化建议</p>
        </div>
        <button className="refresh-btn" onClick={handleRefresh} disabled={refreshing}>
          <span style={{ display: 'inline-flex', alignItems: 'center' }}>↻</span>
          {refreshing ? '计算中...' : '重新评分'}
        </button>
      </header>

      <div className="summary-cards">
        <div className="summary-card total">
          <div className="label">监控任务数</div>
          <div className="value">{dashboard.totalTasks}</div>
          <div className="sub">定时任务总数</div>
        </div>
        <div className="summary-card avg">
          <div className="label">平均健康度</div>
          <div className="value">{dashboard.avgScore}</div>
          <div className="sub">综合评分 0-100</div>
        </div>
        <div className="summary-card healthy">
          <div className="label">健康任务</div>
          <div className="value">{dashboard.healthyCount}</div>
          <div className="sub">评分 ≥ 80</div>
        </div>
        <div className="summary-card critical">
          <div className="label">异常任务</div>
          <div className="value">{dashboard.warningCount + dashboard.criticalCount}</div>
          <div className="sub">评分 &lt; 80</div>
        </div>
      </div>

      <div className="main-grid">
        <TaskList
          tasks={dashboard.taskScores || []}
          selectedTask={selectedTask}
          onSelect={setSelectedTask}
        />
        {selectedScore && <ScoreDetail score={selectedScore} />}
      </div>

      <div className="main-grid">
        <div className="card">
          <div className="card-title">
            📈 评分趋势
            <div className="card-actions">
              <button 
                className={`action-btn ${showPrediction ? 'active' : ''}`}
                onClick={() => { setShowPrediction(!showPrediction); setShowAutoRepair(false); setShowSlaPrediction(false); }}
              >
                🔮 预测
              </button>
              <button 
                className={`action-btn ${showAutoRepair ? 'active' : ''}`}
                onClick={() => { setShowAutoRepair(!showAutoRepair); setShowPrediction(false); setShowSlaPrediction(false); }}
              >
                🔧 自动修复
              </button>
              <button 
                className={`action-btn ${showSlaPrediction ? 'active' : ''}`}
                onClick={() => { setShowSlaPrediction(!showSlaPrediction); setShowPrediction(false); setShowAutoRepair(false); }}
              >
                🎯 SLA预测
              </button>
            </div>
          </div>
          <TrendChart trend={trend} />
        </div>
        <DiagnosisPanel score={selectedScore} />
      </div>

      {selectedTaskDetail && selectedTaskDetail.actionableItems && selectedTaskDetail.actionableItems.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-title">⚙️ 可执行优化建议</div>
          <div className="actionable-items">
            {selectedTaskDetail.actionableItems.map((item, idx) => (
              <div key={idx} className="actionable-item-card">
                <div className="actionable-header">
                  <div className="actionable-title">
                    <span className="actionable-priority">{item.priority}</span>
                    {item.title}
                  </div>
                  <span className={`risk-badge risk-${item.riskLevel?.toLowerCase()}`}>
                    {item.riskLevel === 'HIGH' ? '高风险' : item.riskLevel === 'MEDIUM' ? '中风险' : '低风险'}
                  </span>
                </div>
                <div className="actionable-description">{item.description}</div>
                <div className="actionable-script">
                  <div className="actionable-script-header">
                    <span className="script-type-badge">{item.scriptType}</span>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{item.scriptName}</span>
                  </div>
                  <pre className="actionable-script-content">{item.scriptContent}</pre>
                </div>
                <div className="actionable-exec">
                  <strong>执行步骤：</strong>
                  <p>{item.executionCommand}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {selectedTaskDetail && selectedTaskDetail.upstreamIssues && selectedTaskDetail.upstreamIssues.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-title">🔗 依赖任务异常关联分析</div>
          <div className="upstream-issues">
            {selectedTaskDetail.upstreamIssues.map((issue, idx) => (
              <div key={idx} className="upstream-issue-card">
                <div className="upstream-header">
                  <span className="upstream-task-name">⬆️ {issue.upstreamTaskName}</span>
                  <span className="upstream-dependency-type">{issue.dependencyType} 依赖</span>
                </div>
                <div className="upstream-score">
                  上游健康度: <span style={{ color: issue.upstreamScore < 60 ? 'var(--accent-red)' : 'var(--accent-yellow)', fontWeight: 600 }}>
                    {issue.upstreamScore} ({issue.upstreamScoreLevel})
                  </span>
                </div>
                <div className="upstream-issue-desc">
                  {issue.issue}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showPrediction && selectedTask && (
        <div className="card" style={{ marginBottom: 24 }}>
          <HealthPrediction taskName={selectedTask} onClose={() => setShowPrediction(false)} />
        </div>
      )}

      {showAutoRepair && selectedTask && (
        <div className="card" style={{ marginBottom: 24 }}>
          <AutoRepairPanel taskName={selectedTask} onClose={() => setShowAutoRepair(false)} />
        </div>
      )}

      {showSlaPrediction && selectedTask && (
        <div className="card" style={{ marginBottom: 24 }}>
          <SlaPredictionPanel taskName={selectedTask} onClose={() => setShowSlaPrediction(false)} />
        </div>
      )}

      {unhealthy.length > 0 && (
        <UnhealthyPanel tasks={unhealthy} />
      )}
    </div>
  );
}
