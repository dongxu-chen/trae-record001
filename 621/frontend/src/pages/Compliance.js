import React, { useState, useEffect } from 'react';
import {
  checkCompliance,
  getComplianceRules,
  generatePolicies,
  getCallRelations,
  loadSampleData,
  getComplianceScenarios,
  checkSemanticCompliance,
} from '../services/api';

function Compliance() {
  const [report, setReport] = useState(null);
  const [rules, setRules] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [activeTab, setActiveTab] = useState('syntax');
  const [scenarios, setScenarios] = useState([]);
  const [semanticReport, setSemanticReport] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedScenarios, setSelectedScenarios] = useState([]);

  useEffect(() => {
    fetchScenarios();
  }, []);

  const fetchScenarios = async () => {
    try {
      const res = await getComplianceScenarios(selectedCategory);
      setScenarios(res.data.scenarios || []);
    } catch (error) {
      console.error('Error fetching scenarios:', error);
    }
  };

  const loadAndCheck = async () => {
    setLoading(true);
    try {
      await loadSampleData();
      const callsRes = await getCallRelations();
      const policiesRes = await generatePolicies(callsRes.data);
      setPolicies(policiesRes.data);

      const rulesRes = await getComplianceRules();
      setRules(rulesRes.data);

      const reportRes = await checkCompliance(policiesRes.data, null);
      setReport(reportRes.data);

      setMessage(`Compliance score: ${reportRes.data.overallScore}%`);
      setTimeout(() => setMessage(''), 5000);
    } catch (error) {
      console.error('Error checking compliance:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckCompliance = async () => {
    if (policies.length === 0) {
      setMessage('Please load or generate policies first');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const res = await checkCompliance(policies, null);
      setReport(res.data);
      setMessage(`Compliance score: ${res.data.overallScore}%`);
      setTimeout(() => setMessage(''), 5000);
    } catch (error) {
      console.error('Error checking compliance:', error);
    } finally {
      setLoading(false);
    }
  };

  const getScoreClass = (score) => {
    if (score >= 80) return 'score-good';
    if (score >= 50) return 'score-medium';
    return 'score-poor';
  };

  const getSeverityBadge = (severity) => {
    const map = {
      CRITICAL: 'badge-critical',
      HIGH: 'badge-high',
      MEDIUM: 'badge-medium',
      LOW: 'badge-low',
    };
    return <span className={`badge ${map[severity] || 'badge-low'}`}>{severity}</span>;
  };

  const handleCheckSemanticCompliance = async () => {
    if (policies.length === 0) {
      setMessage('Please load or generate policies first');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const res = await checkSemanticCompliance(
        policies,
        null,
        selectedScenarios.length > 0 ? selectedScenarios : undefined
      );
      setSemanticReport(res.data);
      setMessage(`Semantic compliance score: ${res.data.overallScore}%`);
      setTimeout(() => setMessage(''), 5000);
    } catch (error) {
      console.error('Error checking semantic compliance:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleScenario = (scenarioId) => {
    setSelectedScenarios((prev) =>
      prev.includes(scenarioId)
        ? prev.filter((id) => id !== scenarioId)
        : [...prev, scenarioId]
    );
  };

  const handleCategoryChange = async (category) => {
    setSelectedCategory(category);
    try {
      const res = await getComplianceScenarios(category);
      setScenarios(res.data.scenarios || []);
    } catch (error) {
      console.error('Error fetching scenarios:', error);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>Compliance Check</h2>
        <p>Verify your authorization policies against security best practices and semantic scenarios</p>
      </div>

      {message && (
        <div className="alert alert-info">{message}</div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Compliance Controls</h3>
        </div>
        <div className="flex gap-4 flex-wrap">
          <button
            className="btn btn-primary"
            onClick={loadAndCheck}
            disabled={loading}
          >
            📊 Load Sample & Check
          </button>
        </div>
        {policies.length > 0 && (
          <div className="mt-4">
            <div className="alert alert-info">
              <strong>Ready:</strong> {policies.length} policies loaded for compliance check
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'syntax' ? 'active' : ''}`}
            onClick={() => setActiveTab('syntax')}
          >
            Syntax Rules
          </button>
          <button
            className={`tab ${activeTab === 'semantic' ? 'active' : ''}`}
            onClick={() => setActiveTab('semantic')}
          >
            Semantic Scenarios
          </button>
        </div>

        {activeTab === 'syntax' && (
          <div>
            <div className="mt-4">
              <button
                className="btn btn-success"
                onClick={handleCheckCompliance}
                disabled={loading || policies.length === 0}
              >
                ✅ Run Syntax Compliance Check
              </button>
            </div>

            {loading ? (
              <div className="loading">
                <div className="spinner"></div>
                Checking compliance...
              </div>
            ) : report ? (
              <>
                <div className="compliance-score">
                  <div
                    className={`score-circle ${getScoreClass(report.overallScore)}`}
                    style={{ '--score': `${report.overallScore}%` }}
                  >
                    {report.overallScore}%
                  </div>
                  <div className="score-label">Overall Compliance Score</div>
                  <div style={{ marginTop: '16px', color: '#94a3b8', fontSize: '14px' }}>
                    {report.overallScore >= 80
                      ? '🎉 Excellent! Your policies are well-configured.'
                      : report.overallScore >= 50
                      ? '⚠️ Some improvements needed. Review the failed checks below.'
                      : '❌ Critical issues found. Please address the high-severity items.'}
                  </div>
                </div>

                <div className="stats-grid" style={{ marginTop: '16px' }}>
                  {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => {
                    const passed = report.results.filter(
                      (r) => r.rule.severity === sev && r.passed
                    ).length;
                    const failed = report.results.filter(
                      (r) => r.rule.severity === sev && !r.passed
                    ).length;
                    return (
                      <div className="stat-card" key={sev}>
                        <div className="flex justify-between">
                          <div>
                            <div className="stat-value" style={{ fontSize: '24px', color: '#10b981' }}>
                              {passed}
                            </div>
                            <div className="stat-label">Passed</div>
                          </div>
                          <div>
                            <div className="stat-value" style={{ fontSize: '24px', color: '#ef4444' }}>
                              {failed}
                            </div>
                            <div className="stat-label">Failed</div>
                          </div>
                        </div>
                        <div className="mt-4" style={{ textAlign: 'center' }}>
                          {getSeverityBadge(sev)}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="card" style={{ marginTop: '16px' }}>
                  <div className="card-header">
                    <h3>Check Results</h3>
                  </div>
                  {report.results.map((result, idx) => (
                    <div className="compliance-item" key={idx}>
                      <div className={`compliance-status ${result.passed ? 'compliance-passed' : 'compliance-failed'}`}>
                        {result.passed ? '✓' : '✗'}
                      </div>
                      <div className="compliance-content">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="compliance-rule-name">
                              {result.rule.name}
                            </div>
                            <div className="compliance-rule-id">
                              {result.rule.id} | {getSeverityBadge(result.rule.severity)}
                            </div>
                          </div>
                          <span className={`badge ${result.passed ? 'badge-success' : 'badge-fail'}`}>
                            {result.passed ? 'PASSED' : 'FAILED'}
                          </span>
                        </div>
                        <div className="compliance-details">
                          {result.rule.description}
                        </div>
                        <div className="compliance-details" style={{ marginTop: '8px', fontStyle: 'italic' }}>
                          {result.details}
                        </div>
                        {result.violations && result.violations.length > 0 && (
                          <ul className="compliance-violations">
                            {result.violations.map((v, vidx) => (
                              <li key={vidx}>{v}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="card" style={{ marginTop: '16px' }}>
                  <div className="card-header">
                    <h3>Compliance Framework Reference</h3>
                  </div>
                  <div className="alert alert-info">
                    <strong>About these checks:</strong> These rules are based on CIS Kubernetes
                    Benchmark, Istio security best practices, and the principle of least privilege.
                  </div>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Rule ID</th>
                        <th>Name</th>
                        <th>Description</th>
                        <th>Severity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rules.length > 0
                        ? rules.map((rule) => (
                            <tr key={rule.id}>
                              <td style={{ fontFamily: 'monospace' }}>{rule.id}</td>
                              <td>{rule.name}</td>
                              <td style={{ color: '#94a3b8' }}>{rule.description}</td>
                              <td>{getSeverityBadge(rule.severity)}</td>
                            </tr>
                          ))
                        : [
                            { id: 'CIS-001', name: 'Deny-All Default Policy', desc: 'Ensure a default deny-all policy exists', severity: 'HIGH' },
                            { id: 'CIS-002', name: 'No Wildcard Sources', desc: 'Avoid wildcard (*) in source principals', severity: 'HIGH' },
                            { id: 'CIS-003', name: 'Least Privilege Methods', desc: 'Avoid wildcard (*) for HTTP methods', severity: 'MEDIUM' },
                            { id: 'CIS-004', name: 'Path Restrictions', desc: 'Policies should specify paths', severity: 'MEDIUM' },
                            { id: 'CIS-005', name: 'No Empty Selector', desc: 'Policies should target specific workloads', severity: 'MEDIUM' },
                            { id: 'CIS-006', name: 'Avoid Namespace-Wide', desc: 'Avoid policies applying to all services', severity: 'LOW' },
                            { id: 'CIS-007', name: 'Least Privilege', desc: 'Minimal necessary permissions', severity: 'HIGH' },
                            { id: 'CIS-008', name: 'Mutual TLS Enabled', desc: 'Use service account identities', severity: 'HIGH' },
                          ].map((rule) => (
                            <tr key={rule.id}>
                              <td style={{ fontFamily: 'monospace' }}>{rule.id}</td>
                              <td>{rule.name}</td>
                              <td style={{ color: '#94a3b8' }}>{rule.desc}</td>
                              <td>{getSeverityBadge(rule.severity)}</td>
                            </tr>
                          ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">✅</div>
                <div className="empty-state-text">No compliance check run yet</div>
                <div className="empty-state-hint">
                  Click "Load Sample & Check" to evaluate your policies against security best practices
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'semantic' && (
          <div>
            <div className="mt-4">
              <div className="alert alert-info">
                <strong>Semantic Compliance:</strong> Check policies against common security scenarios
                based on service topology and business logic.
              </div>
            </div>

            <div className="row mt-4">
              <div className="col">
                <div className="form-group">
                  <label>Filter by Category</label>
                  <select
                    className="form-control"
                    value={selectedCategory}
                    onChange={(e) => handleCategoryChange(e.target.value)}
                  >
                    <option value="">All Categories</option>
                    <option value="DATABASE_ACCESS">Database Access</option>
                    <option value="PAYMENT_SERVICE">Payment Service</option>
                    <option value="ADMIN_INTERFACE">Admin Interface</option>
                    <option value="EXTERNAL_API">External API</option>
                    <option value="PUBLIC_API">Public API</option>
                    <option value="USER_DATA">User Data</option>
                    <option value="MESSAGE_QUEUE">Message Queue</option>
                    <option value="CACHE_SERVICE">Cache Service</option>
                    <option value="CIRCULAR_DEPENDENCY">Circular Dependency</option>
                    <option value="SENSITIVE_PATH">Sensitive Path</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="card" style={{ margin: '16px 0', backgroundColor: '#0f172a' }}>
              <div className="card-header">
                <h4>Select Scenarios to Check</h4>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => setSelectedScenarios(scenarios.map(s => s.id))}
                >
                  Select All
                </button>
              </div>
              <div style={{ maxHeight: '300px', overflowY: 'auto', padding: '16px' }}>
                {scenarios.map((scenario) => (
                  <div key={scenario.id} className="flex items-start gap-3 mb-3">
                    <input
                      type="checkbox"
                      id={scenario.id}
                      checked={selectedScenarios.includes(scenario.id)}
                      onChange={() => toggleScenario(scenario.id)}
                      style={{ marginTop: '4px' }}
                    />
                    <label htmlFor={scenario.id} style={{ cursor: 'pointer', flex: 1 }}>
                      <div className="flex justify-between items-start">
                        <div>
                          <strong>{scenario.id}: {scenario.name}</strong>
                          {getSeverityBadge(scenario.severity)}
                        </div>
                        <span className="badge badge-medium">{scenario.category}</span>
                      </div>
                      <div style={{ color: '#94a3b8', fontSize: '13px', marginTop: '4px' }}>
                        {scenario.description}
                      </div>
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <button
              className="btn btn-success"
              onClick={handleCheckSemanticCompliance}
              disabled={loading || policies.length === 0}
            >
              {loading ? 'Checking...' : '🔍 Run Semantic Compliance Check'}
            </button>

            {semanticReport && (
              <>
                <div className="compliance-score" style={{ marginTop: '16px' }}>
                  <div
                    className={`score-circle ${getScoreClass(semanticReport.overallScore)}`}
                    style={{ '--score': `${semanticReport.overallScore}%` }}
                  >
                    {semanticReport.overallScore}%
                  </div>
                  <div className="score-label">Semantic Compliance Score</div>
                  <div style={{ marginTop: '16px', color: '#94a3b8', fontSize: '14px' }}>
                    {semanticReport.overallScore >= 80
                      ? '🎉 Excellent! Your policies follow security best practices.'
                      : semanticReport.overallScore >= 50
                      ? '⚠️ Some scenario violations detected.'
                      : '❌ Critical security scenarios violated.'}
                  </div>
                </div>

                <div className="stats-grid" style={{ marginTop: '16px' }}>
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: '#10b981' }}>
                      {semanticReport.passedScenarios}
                    </div>
                    <div className="stat-label">Passed</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: '#ef4444' }}>
                      {semanticReport.failedScenarios}
                    </div>
                    <div className="stat-label">Failed</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{semanticReport.totalScenarios}</div>
                    <div className="stat-label">Total Checked</div>
                  </div>
                </div>

                <div className="card" style={{ marginTop: '16px' }}>
                  <div className="card-header">
                    <h3>Scenario Check Results</h3>
                  </div>
                  {semanticReport.results?.map((result, idx) => (
                    <div className="compliance-item" key={idx}>
                      <div className={`compliance-status ${result.passed ? 'compliance-passed' : 'compliance-failed'}`}>
                        {result.passed ? '✓' : '✗'}
                      </div>
                      <div className="compliance-content">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="compliance-rule-name">
                              {result.scenario.name}
                            </div>
                            <div className="compliance-rule-id">
                              {result.scenario.id} | {getSeverityBadge(result.scenario.severity)}
                            </div>
                          </div>
                          <span className={`badge ${result.passed ? 'badge-success' : 'badge-fail'}`}>
                            {result.passed ? 'PASSED' : 'FAILED'}
                          </span>
                        </div>
                        <div className="compliance-details">
                          {result.scenario.description}
                        </div>
                        {result.violations && result.violations.length > 0 && (
                          <ul className="compliance-violations">
                            {result.violations.map((v, vidx) => (
                              <li key={vidx}>{v}</li>
                            ))}
                          </ul>
                        )}
                        {result.recommendations && result.recommendations.length > 0 && (
                          <div className="alert alert-info" style={{ marginTop: '8px' }}>
                            <strong>💡 Recommendations:</strong>
                            <ul style={{ margin: '8px 0 0 16px' }}>
                              {result.recommendations.map((r, ridx) => (
                                <li key={ridx}>{r}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Compliance;
