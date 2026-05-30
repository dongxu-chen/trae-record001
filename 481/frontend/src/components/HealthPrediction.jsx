import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { fetchHealthPrediction } from '../api';

function HealthPrediction({ taskName, onClose }) {
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [horizon, setHorizon] = useState(72);

  useEffect(() => {
    if (taskName) {
      loadPrediction();
    }
  }, [taskName, horizon]);

  const loadPrediction = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchHealthPrediction(taskName, horizon);
      setPrediction(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getTrendIcon = (direction) => {
    switch (direction) {
      case 'IMPROVING': return '📈';
      case 'DECLINING': return '📉';
      default: return '➡️';
    }
  };

  const getTrendClass = (direction) => {
    switch (direction) {
      case 'IMPROVING': return 'trend-improving';
      case 'DECLINING': return 'trend-declining';
      default: return 'trend-stable';
    }
  };

  const getChartData = () => {
    if (!prediction?.predictedScores) return [];
    return prediction.predictedScores.map(p => ({
      time: new Date(p.time).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit' }),
      predicted: p.predictedScore,
      lower: p.lowerBound,
      upper: p.upperBound,
      confidence: Math.round(p.confidence * 100)
    }));
  };

  const formatTime = (timeStr) => {
    return new Date(timeStr).toLocaleString('zh-CN');
  };

  if (loading) return <div className="loading">加载预测数据中...</div>;
  if (error) return <div className="error">加载失败: {error}</div>;
  if (!prediction) return null;

  return (
    <div className="prediction-panel">
      <div className="panel-header">
        <h3>🔮 健康度预测分析</h3>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="prediction-summary">
        <div className="pred-summary-card">
          <div className="pred-label">当前评分</div>
          <div className="pred-value current-score">{prediction.currentScore ?? 'N/A'}</div>
        </div>
        <div className="pred-summary-card">
          <div className="pred-label">趋势方向</div>
          <div className={`pred-value ${getTrendClass(prediction.trendDirection)}`}>
            {getTrendIcon(prediction.trendDirection)} {prediction.trendDirection === 'IMPROVING' ? '改善中' :
              prediction.trendDirection === 'DECLINING' ? '下降中' : '稳定'}
          </div>
        </div>
        <div className="pred-summary-card">
          <div className="pred-label">趋势斜率</div>
          <div className="pred-value">{prediction.trendSlope?.toFixed(2) ?? 'N/A'}</div>
        </div>
        <div className="pred-summary-card">
          <div className="pred-label">预测置信度</div>
          <div className="pred-value confidence">{Math.round((prediction.confidence ?? 0) * 100)}%</div>
        </div>
      </div>

      <div className="prediction-controls">
        <label>预测时间范围: </label>
        <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
          <option value={24}>24小时</option>
          <option value={48}>48小时</option>
          <option value={72}>72小时</option>
          <option value={168}>7天</option>
        </select>
        <span className="algorithm-badge">算法: {prediction.algorithmUsed}</span>
      </div>

      <div className="chart-container">
        <h4>📊 评分预测趋势图</h4>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={getChartData()}>
            <defs>
              <linearGradient id="colorPred" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorRange" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#94a3b8" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="time" stroke="#94a3b8" fontSize={11} />
            <YAxis domain={[0, 100]} stroke="#94a3b8" fontSize={11} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Legend />
            <Area type="monotone" dataKey="upper" stroke="none" fill="url(#colorRange)" />
            <Area type="monotone" dataKey="lower" stroke="none" fill="#0f172a" />
            <Line type="monotone" dataKey="predicted" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6' }} name="预测评分" />
            <Line type="monotone" dataKey="upper" stroke="#94a3b8" strokeWidth={1} strokeDasharray="5 5" dot={false} name="上限" />
            <Line type="monotone" dataKey="lower" stroke="#94a3b8" strokeWidth={1} strokeDasharray="5 5" dot={false} name="下限" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="forecast-summary">
        <h4>💡 预测分析摘要</h4>
        <p>{prediction.forecastSummary}</p>
      </div>

      <div className="prediction-details">
        <h4>📋 详细预测数据</h4>
        <div className="prediction-table">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>预测评分</th>
                <th>置信区间</th>
                <th>置信度</th>
              </tr>
            </thead>
            <tbody>
              {prediction.predictedScores?.slice(0, 6).map((p, idx) => (
                <tr key={idx}>
                  <td>{formatTime(p.time)}</td>
                  <td className={`score-cell ${p.predictedScore >= 80 ? 'score-good' : p.predictedScore >= 60 ? 'score-warning' : 'score-critical'}`}>
                    {p.predictedScore}
                  </td>
                  <td>{p.lowerBound} ~ {p.upperBound}</td>
                  <td>{Math.round(p.confidence * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="prediction-meta">
        <small>预测时间: {formatTime(prediction.predictionTime)}</small>
        <small>预测范围: {prediction.predictionHorizonHours}小时</small>
      </div>
    </div>
  );
}

export default HealthPrediction;
