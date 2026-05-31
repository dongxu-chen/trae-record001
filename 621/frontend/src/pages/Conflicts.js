import React, { useState } from 'react';
import { detectConflicts, generatePolicies, getCallRelations, loadSampleData } from '../services/api';

function Conflicts() {
  const [conflicts, setConflicts] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [activeTab, setActiveTab] = useState('detect');

  const loadDataAndDetect = async () => {
    setLoading(true);
    try {
      await loadSampleData();
      const callsRes = await getCallRelations();
      const policiesRes = await generatePolicies(callsRes.data);
      setPolicies(policiesRes.data);

      const conflictsRes = await detectConflicts(policiesRes.data);
      setConflicts(conflictsRes.data);

      if (conflictsRes.data.length === 0) {
        setMessage('No conflicts detected! Your policies are clean.');
      } else {
        setMessage(`Detected ${conflictsRes.data.length} potential conflicts`);
      }
      setTimeout(() => setMessage(''), 5000);
    } catch (error) {
      console.error('Error detecting conflicts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDetectConflicts = async () => {
    if (policies.length === 0) {
      setMessage('Please generate or load policies first');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const res = await detectConflicts(policies);
      setConflicts(res.data);

      if (res.data.length === 0) {
        setMessage('No conflicts detected! Your policies are clean.');
      } else {
        setMessage(`Detected ${res.data.length} potential conflicts`);
      }
      setTimeout(() => setMessage(''), 5000);
    } catch (error) {
      console.error('Error detecting conflicts:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityBadge = (severity) => {
    const severityMap = {
      CRITICAL: 'badge-critical',
      HIGH: 'badge-high',
      MEDIUM: 'badge-medium',
      LOW: 'badge-low',
    };
    return (
      <span className={`badge ${severityMap[severity] || 'badge-low'}`}>
        {severity}
      </span>
    );
  };

  const getConflictTypeIcon = (type) => {
    const icons = {
      SHADOWING: '🌑',
      OVERLAP: '🔀',
      CONTRADICTION: '⚠️',
      OVERLY_BROAD: '🔓',
      WILDCARD_METHOD: '❓',
    };
    return icons[type] || '⚠️';
  };

  const conflictTypes = [
    { id: 'SHADOWING', name: 'Shadowing', desc: 'One policy hides another' },
    { id: 'OVERLAP', name: 'Overlap', desc: 'Policies cover same traffic' },
    { id: 'CONTRADICTION', name: 'Contradiction', desc: 'ALLOW and DENY conflict' },
    { id: 'OVERLY_BROAD', name: 'Overly Broad', desc: 'Wildcard sources in ALLOW' },
    { id: 'WILDCARD_METHOD', name: 'Wildcard Method', desc: 'Wildcard HTTP methods' },
  ];

  const filteredConflicts = activeTab === 'detect'
    ? conflicts
    : conflicts.filter((c) => c.type === activeTab);

  return (
    <div>
      <div className="page-header">
        <h2>Policy Conflicts</h2>
        <p>Detect and analyze conflicts in your authorization policies</p>
      </div>

      {message && (
        <div className={`alert ${conflicts.length === 0 ? 'alert-success' : 'alert-warning'}`}>
          {message}
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Conflict Detection</h3>
        </div>
        <div className="flex gap-4">
          <button
            className="btn btn-primary"
            onClick={loadDataAndDetect}
            disabled={loading}
          >
            📊 Load Sample & Detect
          </button>
          <button
            className="btn btn-warning"
            onClick={handleDetectConflicts}
            disabled={loading || policies.length === 0}
          >
            🔍 Detect Conflicts
          </button>
        </div>

        {policies.length > 0 && (
          <div className="mt-4">
            <div className="alert alert-info">
              <strong>Loaded:</strong> {policies.length} policies ready for analysis
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner"></div>
          Analyzing policies...
        </div>
      ) : conflicts.length > 0 ? (
        <>
          <div className="stats-grid">
            {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => {
              const count = conflicts.filter((c) => c.severity === sev).length;
              return (
                <div className="stat-card" key={sev}>
                  <div className="stat-value">{count}</div>
                  <div className="stat-label">{sev} Severity</div>
                </div>
              );
            })}
          </div>

          <div className="card">
            <div className="card-header">
              <h3>Conflict Types</h3>
            </div>
            <div className="tabs">
              <button
                className={`tab ${activeTab === 'detect' ? 'active' : ''}`}
                onClick={() => setActiveTab('detect')}
              >
                All ({conflicts.length})
              </button>
              {conflictTypes.map((type) => {
                const count = conflicts.filter((c) => c.type === type.id).length;
                return (
                  <button
                    key={type.id}
                    className={`tab ${activeTab === type.id ? 'active' : ''}`}
                    onClick={() => setActiveTab(type.id)}
                    disabled={count === 0}
                  >
                    {type.name} ({count})
                  </button>
                );
              })}
            </div>

            {filteredConflicts.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">✅</div>
                <div className="empty-state-text">No conflicts of this type</div>
              </div>
            ) : (
              filteredConflicts.map((conflict, idx) => (
                <div className="conflict-item" key={idx}>
                  <div className="conflict-header">
                    <div className="flex items-center gap-2">
                      <span style={{ fontSize: '20px' }}>
                        {getConflictTypeIcon(conflict.type)}
                      </span>
                      <span className="conflict-type">{conflict.type}</span>
                      {getSeverityBadge(conflict.severity)}
                    </div>
                  </div>
                  <div className="conflict-description">
                    {conflict.description}
                  </div>
                  <div className="conflict-policies">
                    <span className="badge badge-medium">
                      📜 {conflict.policyA}
                    </span>
                    {conflict.policyB && (
                      <span className="badge badge-medium">
                        📜 {conflict.policyB}
                      </span>
                    )}
                  </div>
                  <div style={{ marginTop: '8px', fontSize: '12px', color: '#64748b' }}>
                    <strong>Affected services:</strong>{' '}
                    {conflict.affectedServices.join(', ')}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <h3>Conflict Type Reference</h3>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Severity</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>🌑 SHADOWING</td>
                  <td>A higher priority policy prevents a lower priority policy from ever being evaluated</td>
                  <td><span className="badge badge-high">HIGH</span></td>
                </tr>
                <tr>
                  <td>🔀 OVERLAP</td>
                  <td>Multiple policies match the same traffic pattern, potentially causing confusion</td>
                  <td><span className="badge badge-medium">MEDIUM</span></td>
                </tr>
                <tr>
                  <td>⚠️ CONTRADICTION</td>
                  <td>Both ALLOW and DENY policies match the same traffic, leading to unpredictable behavior</td>
                  <td><span className="badge badge-critical">CRITICAL</span></td>
                </tr>
                <tr>
                  <td>🔓 OVERLY_BROAD</td>
                  <td>ALLOW policy uses wildcard (*) source, violating least privilege</td>
                  <td><span className="badge badge-medium">MEDIUM</span></td>
                </tr>
                <tr>
                  <td>❓ WILDCARD_METHOD</td>
                  <td>ALLOW policy uses wildcard (*) HTTP method, granting more access than needed</td>
                  <td><span className="badge badge-low">LOW</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-text">No conflicts analyzed yet</div>
            <div className="empty-state-hint">
              Click "Load Sample & Detect" to analyze policies for conflicts
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Conflicts;
