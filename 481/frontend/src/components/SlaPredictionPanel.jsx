import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, BarChart, Bar, Cell } from 'recharts';
import { fetchSlaPrediction, triggerSlaPredictionAll } from '../api';

function SlaPredictionPanel({ taskName, onClose }) {
  const [slaData, setSlaData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [slaTarget, setSlaTarget] = useState(80);

  useEffect(() => {
    if (taskName) {
      loadSlaPrediction();
    }
  }, [taskName, slaTarget]);

  const loadSlaPrediction = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchSlaPrediction(taskName, slaTarget);
      setSlaData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusClass = (status) => {
    switch (status) {
      case 'ON_TRACK': return 'sla-on-track';
      case 'AT_RISK': return 'sla-at-risk';
      case 'WARNING': return 'sla-warning';
      case 'LIKELY_TO_FAIL': return 'sla-likely-fail';
      default: return 'sla-unknown';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'ON_TRACK': return '正常达成';
      case 'AT_RISK': return '有风险';
      case 'WARNING': return '需警惕';
      case 'LIKELY_TO_FAIL': return '可能无法达成';
      default: return '未知';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'ON_TRACK': return '✅';
      case 'AT_RISK': return '⚠️';
      case 'WARNING': return '🔴';
      case 'LIKELY_TO_FAIL': return '❌';
      default: return '❓';
    }
  };

  const getProbabilityColor = (prob) => {
    if (prob >= 0.8) return '#22c55e';
    if (prob >= 0.5) return '#eab308';
    if (prob >= 0.3) return '#f97316';
    return '#ef4444';
  };

  const getTrendChartData = () => {
    if (!slaData?.trendData) return [];
    const data = [];
    if (slaData.trendData.score30DaysAgo != null) {
      data.push({ label: '30天前', score: slaData.trendData.score30DaysAgo, type: '历史' });
    }
    if (slaData.trendData.score14DaysAgo != null) {
      data.push({ label: '14天前', score: slaData.trendData.score14DaysAgo, type: '历史' });
    }
    if (slaData.trendData.score7DaysAgo != null) {
      data.push({ label: '7天前', score: slaData.trendData.score7DaysAgo, type: '历史' });
    }
    data.push({ label: '当前', score: slaData.currentMonthlyAvg, type: '当前' });
    data.push({ label: '月末预测', score: slaData.trendData.projectedEndOfMonthScore, type: '预测' });
    return data;
  };

  const getDaysBreakdownData = () => {
    if (!slaData) return [];
    return [
      { name: '健康', value: slaData.healthyDays || 0, color: '#22c55e' },
      { name: '警告', value: slaData.warningDays || 0, color: '#eab308' },
      { name: '严重', value: slaData.criticalDays || 0, color: '#ef4444' },
    ].filter(d => d.value > 0);
  };

  const getProbabilityLabel = (prob) => {
    const p = Math.round(prob * 100);
    if (p >= 80) return `${p}% - 极有可能`;
    if (p >= 50) return `${p}% - 有可能`;
    if (p >= 30) return `${p}% - 可能性较低`;
    return `${p}% - 不太可能`;
  };

  const formatTime = (timeStr) => {
    return new Date(timeStr).toLocaleString('zh-CN');
  };

  if (loading) return <div className="loading">加载SLA预测数据中...</div>;
  if (error) return <div className="error">加载失败: {error}</div>;
  if (!slaData) return null;

  return (
    <div className="sla-prediction-panel">
      <div className="panel-header">
        <h3>🎯 SLA 达成预测</h3>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="sla-controls">
        <div className="control-group">
          <label>SLA 目标分数:</label>
          <select value={slaTarget} onChange={(e) => setSlaTarget(Number(e.target.value))}>
            <option value={90}>90分 - 优秀</option>
            <option value={85}>85分 - 良好</option>
            <option value={80}>80分 - 标准</option>
            <option value={75}>75分 - 宽松</option>
            <option value={70}>70分 - 最低</option>
          </select>
        </div>
        <button className="btn btn-primary" onClick={loadSlaPrediction}>
          🔄 重新计算
        </button>
        <button className="btn btn-info" onClick={() => triggerSlaPredictionAll()}>
          🚀 批量预测所有任务
        </button>
      </div>

      <div className="sla-status-banner">
        <div className={`sla-status ${getStatusClass(slaData.slaStatus)}`}>
          <span className="status-icon">{getStatusIcon(slaData.slaStatus)}</span>
          <span className="status-text">{getStatusLabel(slaData.slaStatus)}</span>
        </div>
        <div className="sla-score-display">
          <div className="score-block">
            <div className="score-label">月度目标</div>
            <div className="score-value target">{slaData.slaTargetScore}</div>
          </div>
          <div className="score-block">
            <div className="score-label">当前月均</div>
            <div className={`score-value ${slaData.currentMonthlyAvg >= slaData.slaTargetScore ? 'success' : 'warning'}`}>
              {slaData.currentMonthlyAvg?.toFixed(1)}
            </div>
          </div>
          <div className="score-block">
            <div className="score-label">月末预测</div>
            <div className={`score-value ${slaData.predictedMonthlyScore >= slaData.slaTargetScore ? 'success' : 'danger'}`}>
              {slaData.predictedMonthlyScore?.toFixed(1)}
            </div>
          </div>
          <div className="score-block">
            <div className="score-label">达成概率</div>
            <div className="score-value probability" style={{ color: getProbabilityColor(slaData.achievementProbability) }}>
              {Math.round(slaData.achievementProbability * 100)}%
            </div>
          </div>
        </div>
      </div>

      <div className="sla-metrics-grid">
        <div className="metric-card">
          <div className="metric-label">本月已分析天数</div>
          <div className="metric-value">{slaData.daysAnalyzed} 天</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">本月剩余天数</div>
          <div className="metric-value">{slaData.daysRemainingInMonth} 天</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">当前成功率</div>
          <div className={`metric-value ${slaData.currentSuccessRate >= 95 ? 'success' : slaData.currentSuccessRate >= 85 ? 'warning' : 'danger'}`}>
            {slaData.currentSuccessRate?.toFixed(1)}%
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">所需成功率</div>
          <div className="metric-value">{slaData.requiredSuccessRate?.toFixed(1)}%</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">预计剩余失败次数</div>
          <div className={`metric-value ${slaData.predictedFailuresRemaining > 5 ? 'danger' : 'warning'}`}>
            {slaData.predictedFailuresRemaining} 次
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">达成可能性</div>
          <div className="metric-value" style={{ color: getProbabilityColor(slaData.achievementProbability) }}>
            {getProbabilityLabel(slaData.achievementProbability)}
          </div>
        </div>
      </div>

      <div className="sla-score-range">
        <h4>📊 月末分数预测区间</h4>
        <div className="range-display">
          <div className="range-item worst">
            <div className="range-label">最坏情况</div>
            <div className="range-value">{slaData.worstCaseScore?.toFixed(1)}</div>
          </div>
          <div className="range-arrow">→</div>
          <div className="range-item predicted">
            <div className="range-label">预测值</div>
            <div className="range-value">{slaData.predictedMonthlyScore?.toFixed(1)}</div>
          </div>
          <div className="range-arrow">→</div>
          <div className="range-item best">
            <div className="range-label">最好情况</div>
            <div className="range-value">{slaData.bestCaseScore?.toFixed(1)}</div>
          </div>
        </div>
        <div className="range-bar">
          <div
            className="range-fill"
            style={{
              left: `${slaData.worstCaseScore}%`,
              width: `${slaData.bestCaseScore - slaData.worstCaseScore}%`
            }}
          >
            <div
              className="prediction-marker"
              style={{ left: `${slaData.predictedMonthlyScore - slaData.worstCaseScore}%` }}
              title={`预测: ${slaData.predictedMonthlyScore?.toFixed(1)}`}
            />
          </div>
          <div className="target-line" style={{ left: `${slaData.slaTargetScore}%` }} title={`目标: ${slaData.slaTargetScore}`}>
            <span className="target-label">目标</span>
          </div>
        </div>
      </div>

      <div className="sla-charts-row">
        <div className="chart-container half">
          <h4>📈 评分趋势与预测</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={getTrendChartData()}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="label" stroke="#94a3b8" fontSize={11} />
              <YAxis domain={[0, 100]} stroke="#94a3b8" fontSize={11} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Legend />
              <ReferenceLine y={slaData.slaTargetScore} stroke="#ef4444" strokeDasharray="5 5" label={{ value: 'SLA目标', fill: '#ef4444', fontSize: 10 }} />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ fill: '#3b82f6', r: 6 }}
                activeDot={{ r: 8 }}
                name="评分"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container half">
          <h4>📅 本月健康天数分布</h4>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={getDaysBreakdownData()} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis type="number" stroke="#94a3b8" fontSize={11} />
              <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={11} width={60} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                labelStyle={{ color: '#e2e8f0' }}
              />
              <Bar dataKey="value" name="天数" radius={[0, 4, 4, 0]}>
                {getDaysBreakdownData().map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {slaData.trendData && (
        <div className="trend-details">
          <h4>📊 趋势分析</h4>
          <div className="trend-grid">
            <div className="trend-item">
              <span className="trend-label">每日趋势:</span>
              <span className={`trend-value ${slaData.trendData.dailyScoreTrend > 0 ? 'positive' : slaData.trendData.dailyScoreTrend < 0 ? 'negative' : ''}`}>
                {slaData.trendData.dailyScoreTrend > 0 ? '+' : ''}{slaData.trendData.dailyScoreTrend?.toFixed(2)} 分/天
              </span>
            </div>
            <div className="trend-item">
              <span className="trend-label">每周趋势:</span>
              <span className={`trend-value ${slaData.trendData.weeklyScoreTrend > 0 ? 'positive' : slaData.trendData.weeklyScoreTrend < 0 ? 'negative' : ''}`}>
                {slaData.trendData.weeklyScoreTrend > 0 ? '+' : ''}{slaData.trendData.weeklyScoreTrend?.toFixed(2)} 分/周
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="sla-recommendations">
        <h4>💡 达成建议</h4>
        <p>{slaData.recommendations}</p>
      </div>

      <div className="sla-meta">
        <small>预测时间: {formatTime(slaData.predictionTime)}</small>
        <small>统计周期: {formatTime(slaData.monthStart)} ~ {formatTime(slaData.monthEnd)}</small>
      </div>
    </div>
  );
}

export default SlaPredictionPanel;
