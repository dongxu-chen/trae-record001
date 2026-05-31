import React, { useState, useEffect } from 'react';
import {
  generatePolicies,
  optimizePolicies,
  generateIstioYAML,
  getCallRelations,
  loadSampleData,
} from '../services/api';

function Policies() {
  const [policies, setPolicies] = useState([]);
  const [callRelations, setCallRelations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [istioYAML, setIstioYAML] = useState('');
  const [showYAMLModal, setShowYAMLModal] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchCallRelations();
  }, []);

  const fetchCallRelations = async () => {
    try {
      const res = await getCallRelations();
      setCallRelations(res.data);
    } catch (error) {
      console.error('Error fetching call relations:', error);
    }
  };

  const handleGeneratePolicies = async () => {
    setLoading(true);
    try {
      const res = await generatePolicies(callRelations);
      setPolicies(res.data);
      setMessage(`Generated ${res.data.length} policies successfully`);
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error generating policies:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOptimizePolicies = async () => {
    setLoading(true);
    try {
      const res = await optimizePolicies(policies);
      setPolicies(res.data);
      setMessage('Policies optimized successfully');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error optimizing policies:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewYAML = async (policy) => {
    try {
      const res = await generateIstioYAML(policy);
      setIstioYAML(res.data.yaml);
      setSelectedPolicy(policy);
      setShowYAMLModal(true);
    } catch (error) {
      console.error('Error generating YAML:', error);
    }
  };

  const handleLoadSampleData = async () => {
    setLoading(true);
    try {
      await loadSampleData();
      await fetchCallRelations();
      setMessage('Sample data loaded successfully');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error loading sample data:', error);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setMessage('Copied to clipboard!');
    setTimeout(() => setMessage(''), 2000);
  };

  return (
    <div>
      <div className="page-header">
        <h2>Authorization Policies</h2>
        <p>Generate and manage Istio authorization policies based on observed traffic</p>
      </div>

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Actions</h3>
        </div>
        <div className="flex gap-4">
          <button
            className="btn btn-primary"
            onClick={handleLoadSampleData}
            disabled={loading}
          >
            📊 Load Sample Data
          </button>
          <button
            className="btn btn-success"
            onClick={handleGeneratePolicies}
            disabled={loading || callRelations.length === 0}
          >
            🎯 Generate Policies
          </button>
          {policies.length > 0 && (
            <button
              className="btn btn-warning"
              onClick={handleOptimizePolicies}
              disabled={loading}
            >
              ⚡ Optimize Policies
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner"></div>
          Processing...
        </div>
      ) : policies.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📜</div>
            <div className="empty-state-text">No policies yet</div>
            <div className="empty-state-hint">
              Load sample data and click "Generate Policies" to create authorization policies
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{policies.length}</div>
              <div className="stat-label">Total Policies</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">
                {policies.filter((p) => p.action === 'ALLOW').length}
              </div>
              <div className="stat-label">ALLOW Policies</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">
                {policies.filter((p) => p.action === 'DENY').length}
              </div>
              <div className="stat-label">DENY Policies</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">
                {policies.reduce((sum, p) => sum + p.rules.length, 0)}
              </div>
              <div className="stat-label">Total Rules</div>
            </div>
          </div>

          {policies.map((policy, idx) => (
            <div className="policy-card" key={idx}>
              <div className="policy-header">
                <div className="flex items-center gap-2">
                  <h3 className="policy-name">{policy.name}</h3>
                  <span className={`badge ${policy.action === 'ALLOW' ? 'badge-allow' : 'badge-deny'}`}>
                    {policy.action}
                  </span>
                </div>
                <div className="policy-actions">
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleViewYAML(policy)}
                  >
                    View YAML
                  </button>
                </div>
              </div>
              <div className="policy-rules">
                {policy.rules.map((rule, ridx) => (
                  <div className="policy-rule" key={ridx}>
                    <div>
                      <span className="policy-rule-from">{rule.from}</span>
                      {' → '}
                      <span className="policy-rule-to">{rule.to}</span>
                    </div>
                    <div style={{ marginTop: '8px', color: '#94a3b8', fontSize: '12px' }}>
                      <div>
                        <strong>Methods:</strong>{' '}
                        {rule.methods.map((m) => (
                          <span
                            key={m}
                            className="badge badge-low"
                            style={{ marginRight: '4px' }}
                          >
                            {m}
                          </span>
                        ))}
                      </div>
                      {rule.paths && rule.paths.length > 0 && (
                        <div style={{ marginTop: '4px' }}>
                          <strong>Paths:</strong>{' '}
                          {rule.paths.join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {policy.selector && Object.keys(policy.selector).length > 0 && (
                <div style={{ fontSize: '12px', color: '#64748b' }}>
                  <strong>Selector:</strong>{' '}
                  {Object.entries(policy.selector)
                    .map(([k, v]) => `${k}=${v}`)
                    .join(', ')}
                </div>
              )}
            </div>
          ))}
        </>
      )}

      {showYAMLModal && (
        <div className="modal-backdrop" onClick={() => setShowYAMLModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Istio YAML - {selectedPolicy?.name}</h3>
              <button className="close-btn" onClick={() => setShowYAMLModal(false)}>
                ×
              </button>
            </div>
            <div className="code-block" style={{ marginBottom: '16px' }}>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{istioYAML}</pre>
            </div>
            <div className="flex justify-between">
              <button
                className="btn btn-primary"
                onClick={() => copyToClipboard(istioYAML)}
              >
                📋 Copy to Clipboard
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setShowYAMLModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Policies;
