import React, { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { scanAPI } from '../services/api';

function ResultsPage({ result }) {
  const [activeTab, setActiveTab] = useState('overview');

  if (!result) {
    return (
      <div className="card">
        <h2 className="card-title">📊 扫描结果</h2>
        <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
          <p style={{ fontSize: '1.25rem' }}>暂无扫描结果</p>
          <p>请先进行扫描</p>
        </div>
      </div>
    );
  }

  const vulnerabilities = result.vulnerabilities || [];
  
  const stats = {
    critical: vulnerabilities.filter(v => v.severity === 'critical').length,
    high: vulnerabilities.filter(v => v.severity === 'high').length,
    medium: vulnerabilities.filter(v => v.severity === 'medium').length,
    low: vulnerabilities.filter(v => v.severity === 'low').length,
  };

  const chartData = [
    { name: '严重', value: stats.critical, color: '#dc3545' },
    { name: '高危', value: stats.high, color: '#fd7e14' },
    { name: '中危', value: stats.medium, color: '#ffc107' },
    { name: '低危', value: stats.low, color: '#28a745' },
  ].filter(item => item.value > 0);

  const exportHTML = async () => {
    try {
      const html = await scanAPI.generateHTMLReport(result);
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `scan-report-${new Date().toISOString().slice(0, 10)}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const exportMarkdown = async () => {
    try {
      const { markdown } = await scanAPI.generateMarkdownReport(result);
      const blob = new Blob([markdown], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `scan-report-${new Date().toISOString().slice(0, 10)}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 className="card-title" style={{ margin: 0 }}>📊 扫描结果</h2>
          <div className="btn-group">
            <button onClick={exportHTML} className="btn btn-success">
              📄 导出HTML报告
            </button>
            <button onClick={exportMarkdown} className="btn btn-primary">
              📝 导出Markdown报告
            </button>
          </div>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{vulnerabilities.length}</div>
          <div className="stat-label">发现漏洞数</div>
        </div>
        <div className="stat-card">
          <div className="stat-number stat-critical">{stats.critical}</div>
          <div className="stat-label">严重</div>
        </div>
        <div className="stat-card">
          <div className="stat-number stat-high">{stats.high}</div>
          <div className="stat-label">高危</div>
        </div>
        <div className="stat-card">
          <div className="stat-number stat-medium">{stats.medium}</div>
          <div className="stat-label">中危</div>
        </div>
        <div className="stat-card">
          <div className="stat-number stat-low">{stats.low}</div>
          <div className="stat-label">低危</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{result.total_requests || 0}</div>
          <div className="stat-label">总请求数</div>
        </div>
      </div>

      <div className="card">
        <div className="tabs">
          <div 
            className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            总览
          </div>
          <div 
            className={`tab ${activeTab === 'details' ? 'active' : ''}`}
            onClick={() => setActiveTab('details')}
          >
            漏洞详情
          </div>
        </div>

        <div className={`tab-content ${activeTab === 'overview' ? 'active' : ''}`}>
          {chartData.length > 0 ? (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="no-vulnerabilities">
              <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🎉</div>
              <p>未发现漏洞！</p>
            </div>
          )}
        </div>

        <div className={`tab-content ${activeTab === 'details' ? 'active' : ''}`}>
          {vulnerabilities.length > 0 ? (
            vulnerabilities.map((vuln, index) => (
              <div key={index} className="vulnerability-item">
                <div className="vulnerability-header">
                  <span className="vulnerability-type">{vuln.type}</span>
                  <span className={`severity-badge severity-${vuln.severity}`}>
                    {vuln.severity.toUpperCase()}
                  </span>
                </div>
                
                <div className="vulnerability-details">
                  <div className="detail-box">
                    <div className="detail-label">端点</div>
                    <div className="detail-value">{vuln.endpoint}</div>
                  </div>
                  <div className="detail-box">
                    <div className="detail-label">方法</div>
                    <div className="detail-value">{vuln.method}</div>
                  </div>
                  <div className="detail-box">
                    <div className="detail-label">验证状态</div>
                    <div className="detail-value">
                      {vuln.verified ? '✅ 已验证' : '⏳ 待验证'}
                    </div>
                  </div>
                </div>

                <div className="evidence-box">
                  <strong>证据:</strong> {vuln.evidence}
                  <br />
                  <strong>Payload:</strong> {vuln.payload?.substring(0, 200)}
                </div>

                <div className="recommendation-box">
                  <strong>💡 修复建议:</strong> {vuln.recommendation}
                </div>
              </div>
            ))
          ) : (
            <div className="no-vulnerabilities">
              <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🎉</div>
              <p>未发现漏洞！</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ResultsPage;
