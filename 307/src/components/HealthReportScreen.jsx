import React, { useState, useEffect, useRef } from 'react';
import { HealthReportService } from '../utils/healthReport.js';

export default function HealthReportScreen({ showNotification }) {
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState(null);
  const [history, setHistory] = useState([]);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const chartRef = useRef(null);

  useEffect(() => {
    loadReport();
  }, []);

  const loadReport = async () => {
    try {
      setLoading(true);
      const [reportData, historyData] = await Promise.all([
        HealthReportService.generateReport(),
        HealthReportService.getHealthHistory()
      ]);
      setReport(reportData);
      setHistory(historyData);
    } catch (error) {
      console.error('加载报告失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSnapshot = async () => {
    try {
      await HealthReportService.saveHealthSnapshot();
      await loadReport();
      showNotification('健康快照已保存', 'success');
    } catch (error) {
      showNotification('保存失败: ' + error.message, 'error');
    }
  };

  const handleExport = async (format) => {
    try {
      const data = await HealthReportService.exportReport(format);
      const blob = new Blob([data], { 
        type: format === 'json' ? 'application/json' : 'text/csv' 
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `password-health-report.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      setShowExportMenu(false);
      showNotification(`报告已导出为 ${format.toUpperCase()} 格式`, 'success');
    } catch (error) {
      showNotification('导出失败: ' + error.message, 'error');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return '#22c55e';
    if (score >= 75) return '#3b82f6';
    if (score >= 50) return '#f59e0b';
    return '#ef4444';
  };

  const getTrendIcon = (trend) => {
    switch (trend) {
      case 'improving': return '📈 正在改善';
      case 'declining': return '📉 正在下降';
      default: return '➡️ 保持稳定';
    }
  };

  const renderStrengthChart = (byStrength) => {
    const total = byStrength.weak + byStrength.fair + byStrength.good + byStrength.strong;
    if (total === 0) return null;

    const segments = [
      { label: '弱', value: byStrength.weak, color: '#ef4444' },
      { label: '一般', value: byStrength.fair, color: '#f59e0b' },
      { label: '良好', value: byStrength.good, color: '#3b82f6' },
      { label: '优秀', value: byStrength.strong, color: '#22c55e' }
    ];

    let cumulative = 0;

    return (
      <div>
        <div style={{ 
          height: '24px', 
          borderRadius: '12px', 
          overflow: 'hidden',
          display: 'flex',
          marginBottom: '12px'
        }}>
          {segments.map((seg, i) => {
            if (seg.value === 0) return null;
            const width = (seg.value / total) * 100;
            return (
              <div
                key={i}
                style={{
                  width: `${width}%`,
                  background: seg.color,
                  transition: 'width 0.5s ease'
                }}
                title={`${seg.label}: ${seg.value}个 (${width.toFixed(1)}%)`}
              />
            );
          })}
        </div>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          {segments.map((seg, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: seg.color }}></div>
              <span>{seg.label}: {seg.value}个</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderAgeChart = (byAge) => {
    const data = [
      { label: '>90天', value: byAge.threeMonths, color: '#fef3c7' },
      { label: '>180天', value: byAge.sixMonths, color: '#fcd34d' },
      { label: '>1年', value: byAge.oneYear, color: '#f59e0b' }
    ];

    return (
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', height: '120px' }}>
        {data.map((item, i) => {
          const maxValue = Math.max(...data.map(d => d.value), 1);
          const height = (item.value / maxValue) * 100;
          return (
            <div key={i} style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ 
                height: `${height}%`, 
                background: item.color, 
                borderRadius: '4px 4px 0 0',
                minHeight: item.value > 0 ? '20px' : '0',
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'center',
                paddingTop: '4px'
              }}>
                {item.value > 0 && (
                  <span style={{ fontSize: '11px', color: '#92400e', fontWeight: 'bold' }}>
                    {item.value}
                  </span>
                )}
              </div>
              <div style={{ fontSize: '12px', marginTop: '6px', color: 'var(--text-secondary)' }}>
                {item.label}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderTrendChart = () => {
    if (history.length < 2) return null;

    const data = history.slice(-12);
    const maxScore = 100;
    const minScore = 0;

    return (
      <div ref={chartRef} style={{ height: '150px', position: 'relative', marginTop: '16px' }}>
        <svg width="100%" height="100%" style={{ position: 'absolute', top: 0, left: 0 }}>
          {[0, 25, 50, 75, 100].map((val, i) => (
            <line
              key={i}
              x1="0"
              y1={`${100 - val}%`}
              x2="100%"
              y2={`${100 - val}%`}
              stroke="var(--border)"
              strokeWidth="1"
              strokeDasharray="4,4"
            />
          ))}
          
          {data.length > 1 && (
            <polyline
              fill="none"
              stroke="var(--primary)"
              strokeWidth="2"
              points={data.map((d, i) => {
                const x = (i / (data.length - 1)) * 100;
                const y = 100 - ((d.score - minScore) / (maxScore - minScore)) * 100;
                return `${x}%,${y}%`;
              }).join(' ')}
            />
          )}
          
          {data.map((d, i) => {
            const x = data.length > 1 ? (i / (data.length - 1)) * 100 : 50;
            const y = 100 - ((d.score - minScore) / (maxScore - minScore)) * 100;
            return (
              <circle
                key={i}
                cx={`${x}%`}
                cy={`${y}%`}
                r="4"
                fill="var(--primary)"
              />
            );
          })}
        </svg>
        
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          position: 'absolute', 
          bottom: '-20px', 
          left: 0, 
          right: 0,
          fontSize: '11px',
          color: 'var(--text-secondary)'
        }}>
          <span>{data.length > 0 ? new Date(data[0].timestamp).toLocaleDateString('zh-CN') : ''}</span>
          <span>{data.length > 0 ? new Date(data[data.length - 1].timestamp).toLocaleDateString('zh-CN') : ''}</span>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
        <div className="loading"></div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📊</div>
        <h3>无法加载健康报告</h3>
        <button className="btn btn-primary" onClick={loadReport}>重新加载</button>
      </div>
    );
  }

  const scoreInfo = HealthReportService.getScoreLabel(report.score);

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ marginBottom: '4px' }}>📊 密码健康报告</h2>
          <p style={{ color: 'var(--text-secondary)' }}>
            上次生成：{formatDate(report.generatedAt)}
            {report.trends.lastUpdated && (
              <span style={{ marginLeft: '16px' }}>
                上次快照：{formatDate(report.trends.lastUpdated)}
              </span>
            )}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ position: 'relative' }}>
            <button className="btn btn-secondary" onClick={() => setShowExportMenu(!showExportMenu)}>
              📥 导出报告
            </button>
            {showExportMenu && (
              <div className="pm-context-menu" style={{ right: 0, top: '100%', marginTop: '8px' }}>
                <div 
                  className="pm-context-menu-item"
                  onClick={() => handleExport('json')}
                >
                  JSON 格式
                </div>
                <div 
                  className="pm-context-menu-item"
                  onClick={() => handleExport('csv')}
                >
                  CSV 格式
                </div>
              </div>
            )}
          </div>
          <button className="btn btn-primary" onClick={handleSaveSnapshot}>
            💾 保存快照
          </button>
          <button className="btn btn-secondary" onClick={loadReport}>
            🔄 刷新
          </button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px', background: `linear-gradient(135deg, ${getScoreColor(report.score)}22, var(--bg-primary))` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: '120px',
              height: '120px',
              borderRadius: '50%',
              border: `8px solid ${getScoreColor(report.score)}`,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              background: 'var(--bg-primary)'
            }}>
              <div style={{ fontSize: '36px', fontWeight: 'bold', color: getScoreColor(report.score) }}>
                {report.score}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>分</div>
            </div>
          </div>
          <div style={{ flex: 1 }}>
            <h2 style={{ marginBottom: '8px', color: getScoreColor(report.score) }}>
              {scoreInfo.label}
            </h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '12px' }}>
              您的密码安全综合评分。{getTrendIcon(report.trends.overall)}
            </p>
            <div style={{ display: 'flex', gap: '32px' }}>
              <div>
                <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{report.totalPasswords}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>总密码数</div>
              </div>
              <div>
                <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{report.stats.entropy.average}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>平均熵值 (bits)</div>
              </div>
              <div>
                <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{history.length}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>历史快照</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2" style={{ marginBottom: '24px', gap: '24px' }}>
        <div className="card">
          <h3 style={{ marginBottom: '16px' }}>💪 密码强度分布</h3>
          {renderStrengthChart(report.stats.byStrength)}
        </div>

        <div className="card">
          <h3 style={{ marginBottom: '16px' }}>📅 密码更新周期</h3>
          {renderAgeChart(report.stats.byAge)}
        </div>
      </div>

      {history.length >= 2 && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <h3 style={{ marginBottom: '16px' }}>📈 健康趋势</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '32px' }}>
            最近 {Math.min(history.length, 12)} 次健康评分记录
          </p>
          {renderTrendChart()}
        </div>
      )}

      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ marginBottom: '16px' }}>⚠️ 问题统计</h3>
        <div className="grid grid-cols-4" style={{ gap: '16px' }}>
          <div className="card" style={{ background: report.stats.byStrength.weak > 0 ? 'var(--danger-bg)' : 'var(--bg-tertiary)', textAlign: 'center' }}>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: report.stats.byStrength.weak > 0 ? 'var(--danger)' : 'var(--text)' }}>
              {report.stats.byStrength.weak}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>弱密码</div>
          </div>
          <div className="card" style={{ background: report.stats.duplicates.count > 0 ? 'var(--danger-bg)' : 'var(--bg-tertiary)', textAlign: 'center' }}>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: report.stats.duplicates.count > 0 ? 'var(--danger)' : 'var(--text)' }}>
              {report.stats.duplicates.count}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>重复密码组</div>
          </div>
          <div className="card" style={{ background: report.stats.byAge.oneYear > 0 ? 'var(--warning-bg)' : 'var(--bg-tertiary)', textAlign: 'center' }}>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: report.stats.byAge.oneYear > 0 ? 'var(--warning)' : 'var(--text)' }}>
              {report.stats.byAge.oneYear}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>超过1年未更新</div>
          </div>
          <div className="card" style={{ background: report.stats.byStrength.fair > 0 ? 'var(--warning-bg)' : 'var(--bg-tertiary)', textAlign: 'center' }}>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: report.stats.byStrength.fair > 0 ? 'var(--warning)' : 'var(--text)' }}>
              {report.stats.byStrength.fair}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>一般强度</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: '16px' }}>💡 改进建议</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {report.recommendations.map((rec, i) => (
            <div 
              key={i} 
              className={`card ${rec.priority === 'high' ? 'bg-red-50' : rec.priority === 'medium' ? 'bg-yellow-50' : 'bg-green-50'}`}
              style={{ 
                padding: '16px',
                background: rec.priority === 'high' ? 'var(--danger-bg)' : 
                           rec.priority === 'medium' ? 'var(--warning-bg)' : 
                           'var(--success-bg)',
                border: `1px solid ${rec.priority === 'high' ? 'var(--danger)' : 
                                      rec.priority === 'medium' ? 'var(--warning)' : 
                                      'var(--success)'}`
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontSize: '20px' }}>
                      {rec.priority === 'high' ? '🔴' : rec.priority === 'medium' ? '🟡' : '🟢'}
                    </span>
                    <h4 style={{ margin: 0 }}>{rec.title}</h4>
                    {rec.count !== null && (
                      <span className="badge" style={{ marginLeft: '8px' }}>{rec.count}项</span>
                    )}
                  </div>
                  <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '14px' }}>
                    {rec.description}
                  </p>
                </div>
                {rec.action && (
                  <button 
                    className="btn btn-secondary btn-small"
                    style={{ marginLeft: '16px' }}
                  >
                    {rec.action}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {report.stats.duplicates.count > 0 && (
        <div className="card" style={{ marginTop: '24px' }}>
          <h3 style={{ marginBottom: '16px' }}>🔍 重复密码详情</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {report.stats.duplicates.groups.map((group, i) => (
              <div key={i} className="card" style={{ background: 'var(--bg-tertiary)', padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <div>
                    <span style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                      {group.password}
                    </span>
                    <span className="badge" style={{ marginLeft: '12px' }}>
                      被 {group.count} 个账户使用
                    </span>
                  </div>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {group.entries.map((entry, j) => (
                    <div 
                      key={j} 
                      className="card"
                      style={{ 
                        background: 'var(--bg-primary)', 
                        padding: '8px 12px',
                        fontSize: '13px'
                      }}
                    >
                      <div style={{ fontWeight: '500' }}>{entry.title}</div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                        {entry.username}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function formatDate(timestamp) {
  return new Date(timestamp).toLocaleString('zh-CN');
}
