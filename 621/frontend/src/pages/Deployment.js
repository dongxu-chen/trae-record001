import React, { useState, useEffect } from 'react';
import {
  generatePolicies,
  getCallRelations,
  deployPolicies,
  quickDeployPolicies,
  generateYAML,
  listDeployments,
  rollbackDeployment,
  loadSampleData,
} from '../services/api';

function Deployment() {
  const [policies, setPolicies] = useState([]);
  const [deployments, setDeployments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [activeTab, setActiveTab] = useState('deploy');

  const [targetNamespace, setTargetNamespace] = useState('default');
  const [dryRun, setDryRun] = useState(true);
  const [deploymentResult, setDeploymentResult] = useState(null);
  const [generatedYAML, setGeneratedYAML] = useState('');
  const [showYAML, setShowYAML] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [callsRes, deploymentsRes] = await Promise.all([
        getCallRelations(),
        listDeployments(),
      ]);
      const policiesRes = await generatePolicies(callsRes.data);
      setPolicies(policiesRes.data);
      setDeployments(deploymentsRes.data.deployments || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const handleQuickDeploy = async () => {
    if (policies.length === 0) {
      setMessage('Please generate policies first');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const res = await quickDeployPolicies(targetNamespace, true, dryRun);
      setDeploymentResult(res.data);
      setGeneratedYAML(res.data.yaml);
      setMessage(`Deployment ${res.data.success ? 'successful' : 'failed'}`);
      setTimeout(() => setMessage(''), 5000);
      await fetchData();
    } catch (error) {
      console.error('Error deploying:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateYAML = async () => {
    if (policies.length === 0) {
      setMessage('Please generate policies first');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const res = await generateYAML(policies);
      setGeneratedYAML(res.data.yaml);
      setShowYAML(true);
    } catch (error) {
      console.error('Error generating YAML:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async (deploymentId) => {
    setLoading(true);
    try {
      await rollbackDeployment(deploymentId);
      setMessage('Rollback successful');
      setTimeout(() => setMessage(''), 3000);
      await fetchData();
    } catch (error) {
      console.error('Error rolling back:', error);
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

  const getStatusBadge = (status) => {
    const badgeClass = {
      PENDING: 'badge-medium',
      DEPLOYING: 'badge-medium',
      SUCCESS: 'badge-success',
      FAILED: 'badge-fail',
      ROLLING_BACK: 'badge-medium',
      ROLLED_BACK: 'badge-deny',
    };
    return <span className={`badge ${badgeClass[status] || 'badge-low'}`}>{status}</span>;
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setMessage('YAML copied to clipboard');
    setTimeout(() => setMessage(''), 2000);
  };

  return (
    <div>
      <div className="page-header">
        <h2>Policy Deployment</h2>
        <p>Deploy authorization policies to Istio with one click</p>
      </div>

      {message && (
        <div className="alert alert-info">{message}</div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Deployment Controls</h3>
        </div>
        <div className="flex gap-4 flex-wrap">
          <button
            className="btn btn-primary"
            onClick={handleLoadSampleData}
            disabled={loading}
          >
            📊 Load Sample Data
          </button>
          <div style={{ color: '#94a3b8', alignSelf: 'center' }}>
            {policies.length} policies ready | {deployments.length} deployments history
          </div>
        </div>
      </div>

      <div className="card">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'deploy' ? 'active' : ''}`}
            onClick={() => setActiveTab('deploy')}
          >
            Quick Deploy
          </button>
          <button
            className={`tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            Deployment History
          </button>
        </div>

        {activeTab === 'deploy' && (
          <div>
            <div className="alert alert-info">
              <strong>Quick Deploy:</strong> Generate and deploy authorization policies based on observed service communication patterns.
            </div>

            <div className="row mt-4">
              <div className="col">
                <div className="form-group">
                  <label>Target Namespace</label>
                  <input
                    type="text"
                    className="form-control"
                    value={targetNamespace}
                    onChange={(e) => setTargetNamespace(e.target.value)}
                    placeholder="default"
                  />
                </div>
              </div>
              <div className="col">
                <div className="form-group">
                  <label>Deployment Mode</label>
                  <select
                    className="form-control"
                    value={dryRun ? 'dryrun' : 'apply'}
                    onChange={(e) => setDryRun(e.target.value === 'dryrun')}
                  >
                    <option value="dryrun">Dry Run (Preview only)</option>
                    <option value="apply">Apply (Deploy to cluster)</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex gap-2 mb-4">
              <button
                className="btn btn-primary"
                onClick={handleQuickDeploy}
                disabled={loading || policies.length === 0}
              >
                {loading ? 'Deploying...' : '🚀 Quick Deploy'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={handleGenerateYAML}
                disabled={loading || policies.length === 0}
              >
                📄 Generate YAML
              </button>
            </div>

            {showYAML && generatedYAML && (
              <div className="card" style={{ backgroundColor: '#0f172a' }}>
                <div className="card-header flex justify-between items-center">
                  <h4>Generated Istio YAML</h4>
                  <div className="flex gap-2">
                    <button
                      className="btn btn-sm btn-primary"
                      onClick={() => copyToClipboard(generatedYAML)}
                    >
                      📋 Copy
                    </button>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => setShowYAML(false)}
                    >
                      ✕ Close
                    </button>
                  </div>
                </div>
                <pre
                  style={{
                    padding: '16px',
                    overflowX: 'auto',
                    fontSize: '12px',
                    color: '#e2e8f0',
                    backgroundColor: '#1e293b',
                    borderRadius: '4px',
                    maxHeight: '400px',
                    overflowY: 'auto',
                  }}
                >
                  {generatedYAML}
                </pre>
              </div>
            )}

            {deploymentResult && (
              <div className={`card ${deploymentResult.success ? 'alert-success' : 'alert-error'}`} style={{ marginTop: '16px' }}>
                <div className="card-header">
                  <h4>Deployment Result</h4>
                </div>
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: deploymentResult.success ? '#10b981' : '#ef4444' }}>
                      {deploymentResult.applied}
                    </div>
                    <div className="stat-label">Applied</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: '#ef4444' }}>
                      {deploymentResult.failed}
                    </div>
                    <div className="stat-label">Failed</div>
                  </div>
                </div>
                <p style={{ marginTop: '16px' }}>{deploymentResult.message}</p>
              </div>
            )}

            {policies.length > 0 && (
              <div className="card" style={{ marginTop: '16px' }}>
                <div className="card-header">
                  <h4>Policies to Deploy ({policies.length})</h4>
                </div>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Policy Name</th>
                      <th>Action</th>
                      <th>Rules</th>
                    </tr>
                  </thead>
                  <tbody>
                    {policies.map((policy, idx) => (
                      <tr key={idx}>
                        <td style={{ fontFamily: 'monospace' }}>{policy.name}</td>
                        <td>
                          <span className={`badge ${policy.action === 'ALLOW' ? 'badge-allow' : 'badge-deny'}`}>
                            {policy.action}
                          </span>
                        </td>
                        <td>{policy.rules?.length || 0} rules</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div>
            {deployments.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">📜</div>
                <div className="empty-state-text">No deployment history</div>
                <div className="empty-state-hint">
                  Run a deployment to see the history here
                </div>
              </div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Target</th>
                    <th>Policies</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {deployments.map((deployment, idx) => (
                    <tr key={idx}>
                      <td style={{ fontFamily: 'monospace' }}>{deployment.name}</td>
                      <td>{getStatusBadge(deployment.status)}</td>
                      <td>{deployment.target?.namespace || '-'}</td>
                      <td>{deployment.policies?.length || 0}</td>
                      <td style={{ fontSize: '12px' }}>
                        {new Date(deployment.createdAt).toLocaleString()}
                      </td>
                      <td>
                        {deployment.rollbackEnabled && deployment.status === 'SUCCESS' && (
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => handleRollback(deployment.id)}
                            disabled={loading}
                          >
                            ↩️ Rollback
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Deployment;
