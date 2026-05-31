import React, { useState, useEffect } from 'react';
import {
  generatePolicies,
  getCallRelations,
  evaluateEffectiveness,
  compareSuccessRates,
  loadSampleData,
} from '../services/api';

function Effectiveness() {
  const [beforePolicies, setBeforePolicies] = useState([]);
  const [afterPolicies, setAfterPolicies] = useState([]);
  const [testRequests, setTestRequests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [effectivenessReport, setEffectivenessReport] = useState(null);
  const [successRateMetrics, setSuccessRateMetrics] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const callsRes = await getCallRelations();
      const calls = callsRes.data;

      const requests = calls.map(call => ({
        source: call.source.name,
        dest: call.destination.name,
        method: call.method,
        path: call.path,
      }));
      setTestRequests(requests);

      const policiesRes = await generatePolicies(calls);
      setAfterPolicies(policiesRes.data);

      const restrictedPolicies = policiesRes.data.slice(0, Math.max(1, Math.floor(policiesRes.data.length / 2)));
      setBeforePolicies(restrictedPolicies);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const handleEvaluate = async () => {
    if (beforePolicies.length === 0 || afterPolicies.length === 0 || testRequests.length === 0) {
      setMessage('Please ensure you have policies and test requests');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const [evalRes, ratesRes] = await Promise.all([
        evaluateEffectiveness({
          deploymentId: 'eval-' + Date.now(),
          beforeWindow: 'before',
          afterWindow: 'after',
          testRequests,
          beforePolicies,
          afterPolicies,
        }),
        compareSuccessRates(beforePolicies, afterPolicies, testRequests),
      ]);

      setEffectivenessReport(evalRes.data);
      setSuccessRateMetrics(ratesRes.data.metrics || []);
      setMessage(`Evaluation complete, overall score: ${evalRes.data.overallScore.toFixed(1)}%`);
      setTimeout(() => setMessage(''), 5000);
    } catch (error) {
      console.error('Error evaluating:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSampleData = async () => {
    setLoading(true);
    try {
      await loadSampleData();
      await fetchData();
      setMessage('Sample data loaded successfully');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error loading sample data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreClass = (score) => {
    if (score >= 80) return 'score-good';
    if (score >= 50) return 'score-medium';
    return 'score-poor';
  };

  return (
    <div>
      <div className="page-header">
        <h2>Policy Effectiveness</h2>
        <p>Evaluate policy impact with before/after comparison</p>
      </div>

      {message && (
        <div className="alert alert-info">{message}</div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Evaluation Controls</h3>
        </div>
        <div className="flex gap-4 flex-wrap">
          <button
            className="btn btn-primary"
            onClick={handleLoadSampleData}
            disabled={loading}
          >
            📊 Load Sample Data
          </button>
          <button
            className="btn btn-success"
            onClick={handleEvaluate}
            disabled={loading || testRequests.length === 0}
          >
            {loading ? 'Evaluating...' : '📈 Run Evaluation'}
          </button>
          <div style={{ color: '#94a3b8', alignSelf: 'center' }}>
            {testRequests.length} test requests | {beforePolicies.length} before / {afterPolicies.length} after policies
          </div>
        </div>
      </div>

      {effectivenessReport && (
        <>
          <div className="card">
            <div className="compliance-score">
              <div
                className={`score-circle ${getScoreClass(effectivenessReport.overallScore)}`}
                style={{ '--score': `${effectivenessReport.overallScore}%` }}
              >
                {effectivenessReport.overallScore.toFixed(1)}%
              </div>
              <div className="score-label">Overall Effectiveness Score</div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>Metric Comparison</h3>
            </div>
            <div className="stats-grid">
              {effectivenessReport.metrics?.map((metric, idx) => (
                <div className="stat-card" key={idx}>
                  <div className="stat-label">{metric.metricName}</div>
                  <div className="flex justify-between mt-2">
                    <div>
                      <div style={{ fontSize: '14px', color: '#94a3b8' }}>Before</div>
                      <div style={{ fontSize: '20px', fontWeight: 'bold' }}>
                        {metric.beforeValue.toFixed(1)}%
                      </div>
                    </div>
                    <div style={{ alignSelf: 'center' }}>
                      <span className={`badge ${metric.improved ? 'badge-success' : 'badge-fail'}`}>
                        {metric.change >= 0 ? '+' : ''}{metric.changePercent.toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <div style={{ fontSize: '14px', color: '#94a3b8' }}>After</div>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: metric.improved ? '#10b981' : '#ef4444' }}>
                        {metric.afterValue.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>Service-Level Success Rates</h3>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Total Requests</th>
                  <th>Before</th>
                  <th>After</th>
                  <th>Change</th>
                </tr>
              </thead>
              <tbody>
                {successRateMetrics.map((metric, idx) => (
                  <tr key={idx}>
                    <td style={{ fontFamily: 'monospace' }}>{metric.serviceName}</td>
                    <td>{metric.totalRequests}</td>
                    <td>{metric.rateBefore.toFixed(1)}%</td>
                    <td style={{ color: metric.rateChange >= 0 ? '#10b981' : '#ef4444' }}>
                      {metric.rateAfter.toFixed(1)}%
                    </td>
                    <td>
                      <span className={`badge ${metric.rateChange >= 0 ? 'badge-allow' : 'badge-deny'}`}>
                        {metric.rateChange >= 0 ? '+' : ''}{metric.rateChange.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {effectivenessReport.recommendations?.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h3>💡 Recommendations</h3>
              </div>
              <ul style={{ padding: '16px', margin: 0, paddingLeft: '32px' }}>
                {effectivenessReport.recommendations.map((rec, idx) => (
                  <li key={idx} style={{ marginBottom: '8px' }}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Policy Comparison</h3>
        </div>
        <div className="row">
          <div className="col">
            <h4>Before Policies ({beforePolicies.length})</h4>
            <div style={{ maxHeight: '300px', overflowY: 'auto', paddingRight: '8px' }}>
              {beforePolicies.map((policy, idx) => (
                <div key={idx} className="card" style={{ marginBottom: '8px', padding: '12px' }}>
                  <div style={{ fontFamily: 'monospace', fontSize: '13px' }}>{policy.name}</div>
                  <div>
                    <span className={`badge ${policy.action === 'ALLOW' ? 'badge-allow' : 'badge-deny'}`}>
                      {policy.action}
                    </span>
                    <span style={{ color: '#94a3b8', fontSize: '12px', marginLeft: '8px' }}>
                      {policy.rules?.length || 0} rules
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="col">
            <h4>After Policies ({afterPolicies.length})</h4>
            <div style={{ maxHeight: '300px', overflowY: 'auto', paddingRight: '8px' }}>
              {afterPolicies.map((policy, idx) => (
                <div key={idx} className="card" style={{ marginBottom: '8px', padding: '12px' }}>
                  <div style={{ fontFamily: 'monospace', fontSize: '13px' }}>{policy.name}</div>
                  <div>
                    <span className={`badge ${policy.action === 'ALLOW' ? 'badge-allow' : 'badge-deny'}`}>
                      {policy.action}
                    </span>
                    <span style={{ color: '#94a3b8', fontSize: '12px', marginLeft: '8px' }}>
                      {policy.rules?.length || 0} rules
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Effectiveness;
