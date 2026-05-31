import React, { useState, useEffect } from 'react';
import {
  simulate,
  simulateBatch,
  getCoverageReport,
  generatePolicies,
  getCallRelations,
  loadSampleData,
  detectPolicyChanges,
  simulateIncremental,
  setSimulationBaseline,
} from '../services/api';

function Simulator() {
  const [policies, setPolicies] = useState([]);
  const [callRelations, setCallRelations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [activeTab, setActiveTab] = useState('single');

  const [singleRequest, setSingleRequest] = useState({
    source: '',
    dest: '',
    method: 'GET',
    path: '/',
  });
  const [singleResult, setSingleResult] = useState(null);

  const [batchResult, setBatchResult] = useState(null);
  const [coverageReport, setCoverageReport] = useState(null);
  const [incrementalResult, setIncrementalResult] = useState(null);
  const [policyChanges, setPolicyChanges] = useState(null);
  const [baselineBuilt, setBaselineBuilt] = useState(false);

  const methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [policiesRes, callsRes] = await Promise.all([
        generatePolicies([]),
        getCallRelations(),
      ]);
      setPolicies(policiesRes.data);
      setCallRelations(callsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
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

  const handleSimulateSingle = async () => {
    if (!singleRequest.source || !singleRequest.dest) {
      setMessage('Please fill in source and destination');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const res = await simulate({
        policies,
        ...singleRequest,
      });
      setSingleResult(res.data);
    } catch (error) {
      console.error('Error simulating:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateBatch = async () => {
    if (callRelations.length === 0) {
      setMessage('No call relations to simulate. Load sample data first.');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const res = await simulateBatch({
        policies,
        calls: callRelations,
      });
      setBatchResult(res.data);
      setMessage(`Simulation complete: ${res.data.allowed} allowed, ${res.data.denied} denied`);
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error simulating batch:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGetCoverage = async () => {
    if (policies.length === 0 || callRelations.length === 0) {
      setMessage('Need both policies and call relations for coverage report');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const res = await getCoverageReport(policies, callRelations);
      setCoverageReport(res.data);
    } catch (error) {
      console.error('Error getting coverage:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBuildBaseline = async () => {
    if (policies.length === 0 || callRelations.length === 0) {
      setMessage('Need both policies and call relations to build baseline');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const requests = callRelations.map((call) => ({
        source: call.source.name,
        dest: call.destination.name,
        method: call.method,
        path: call.path,
      }));

      await setSimulationBaseline({
        policies,
        requests,
        clearFirst: true,
      });

      setBaselineBuilt(true);
      setMessage('Baseline built successfully');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error building baseline:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDetectChanges = async () => {
    if (policies.length === 0) {
      setMessage('Need policies to detect changes');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const modifiedPolicies = JSON.parse(JSON.stringify(policies));
      if (modifiedPolicies.length > 0 && modifiedPolicies[0].rules) {
        modifiedPolicies[0].rules[0].to.operations.methods = ['GET', 'POST'];
      }

      const res = await detectPolicyChanges(policies, modifiedPolicies);
      setPolicyChanges(res.data);
      setMessage(`Detected ${res.data.count} policy changes`);
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error detecting changes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleIncrementalSimulate = async () => {
    if (!baselineBuilt) {
      setMessage('Please build baseline first');
      setTimeout(() => setMessage(''), 3000);
      return;
    }

    setLoading(true);
    try {
      const modifiedPolicies = JSON.parse(JSON.stringify(policies));
      if (modifiedPolicies.length > 0 && modifiedPolicies[0].rules) {
        modifiedPolicies[0].rules[0].to.operations.methods = ['GET', 'POST'];
      }

      const requests = callRelations.map((call) => ({
        source: call.source.name,
        dest: call.destination.name,
        method: call.method,
        path: call.path,
      }));

      const res = await simulateIncremental({
        basePolicies: policies,
        policyChanges: [
          {
            type: 'MODIFY',
            policy: modifiedPolicies[0],
          },
        ],
        testRequests: requests,
      });

      setIncrementalResult(res.data);
      setMessage(`Incremental simulation: ${res.data.skippedCount} skipped, ${res.data.affectedCount} affected`);
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error in incremental simulation:', error);
    } finally {
      setLoading(false);
    }
  };

  const services = Array.from(
    new Set([
      ...callRelations.map((c) => c.source.name),
      ...callRelations.map((c) => c.destination.name),
    ])
  ).sort();

  return (
    <div>
      <div className="page-header">
        <h2>Policy Simulator</h2>
        <p>Test your authorization policies before deploying them</p>
      </div>

      {message && (
        <div className="alert alert-info">{message}</div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Simulation Controls</h3>
        </div>
        <div className="flex gap-4">
          <button
            className="btn btn-primary"
            onClick={handleLoadSampleData}
            disabled={loading}
          >
            📊 Load Sample Data
          </button>
          <div style={{ color: '#94a3b8', alignSelf: 'center' }}>
            {policies.length} policies loaded | {callRelations.length} call patterns
          </div>
        </div>
      </div>

      <div className="card">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'single' ? 'active' : ''}`}
            onClick={() => setActiveTab('single')}
          >
            Single Request
          </button>
          <button
            className={`tab ${activeTab === 'batch' ? 'active' : ''}`}
            onClick={() => setActiveTab('batch')}
          >
            Batch Simulation
          </button>
          <button
            className={`tab ${activeTab === 'coverage' ? 'active' : ''}`}
            onClick={() => setActiveTab('coverage')}
          >
            Coverage Report
          </button>
          <button
            className={`tab ${activeTab === 'incremental' ? 'active' : ''}`}
            onClick={() => setActiveTab('incremental')}
          >
            Incremental Simulation
          </button>
        </div>

        {activeTab === 'single' && (
          <div>
            <div className="row">
              <div className="col">
                <div className="form-group">
                  <label>Source Service</label>
                  <select
                    className="form-control"
                    value={singleRequest.source}
                    onChange={(e) => setSingleRequest({ ...singleRequest, source: e.target.value })}
                  >
                    <option value="">Select source...</option>
                    {services.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="col">
                <div className="form-group">
                  <label>Destination Service</label>
                  <select
                    className="form-control"
                    value={singleRequest.dest}
                    onChange={(e) => setSingleRequest({ ...singleRequest, dest: e.target.value })}
                  >
                    <option value="">Select destination...</option>
                    {services.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
            <div className="row">
              <div className="col">
                <div className="form-group">
                  <label>HTTP Method</label>
                  <select
                    className="form-control"
                    value={singleRequest.method}
                    onChange={(e) => setSingleRequest({ ...singleRequest, method: e.target.value })}
                  >
                    {methods.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="col">
                <div className="form-group">
                  <label>Path</label>
                  <input
                    type="text"
                    className="form-control"
                    value={singleRequest.path}
                    onChange={(e) => setSingleRequest({ ...singleRequest, path: e.target.value })}
                    placeholder="/api/resource"
                  />
                </div>
              </div>
            </div>
            <button
              className="btn btn-primary"
              onClick={handleSimulateSingle}
              disabled={loading}
            >
              {loading ? 'Simulating...' : '🔬 Run Simulation'}
            </button>

            {singleResult && (
              <div
                className={`simulation-result ${
                  singleResult.allowed ? 'simulation-allowed' : 'simulation-denied'
                }`}
              >
                <div className="simulation-status">
                  {singleResult.allowed ? '✅ ALLOWED' : '❌ DENIED'}
                </div>
                <div className="simulation-reason">
                  {singleResult.reason}
                  {singleResult.matchedPolicy && (
                    <div style={{ marginTop: '8px' }}>
                      Matched policy: <code>{singleResult.matchedPolicy}</code>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'batch' && (
          <div>
            <div className="alert alert-info">
              Run simulation against all observed call patterns to verify policy coverage.
            </div>
            <button
              className="btn btn-primary mb-4"
              onClick={handleSimulateBatch}
              disabled={loading || callRelations.length === 0}
            >
              {loading ? 'Simulating...' : '▶️ Run Batch Simulation'}
            </button>

            {batchResult && (
              <>
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-value">{batchResult.total}</div>
                    <div className="stat-label">Total Tests</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: '#10b981' }}>
                      {batchResult.allowed}
                    </div>
                    <div className="stat-label">Allowed</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: '#ef4444' }}>
                      {batchResult.denied}
                    </div>
                    <div className="stat-label">Denied</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">
                      {batchResult.total > 0
                        ? ((batchResult.allowed / batchResult.total) * 100).toFixed(0)
                        : 0}%
                    </div>
                    <div className="stat-label">Coverage</div>
                  </div>
                </div>

                <table className="table">
                  <thead>
                    <tr>
                      <th>Source</th>
                      <th>Destination</th>
                      <th>Method</th>
                      <th>Path</th>
                      <th>Result</th>
                      <th>Matched Policy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {batchResult.results.map((r, idx) => (
                      <tr key={idx}>
                        <td>{r.call.source.name}</td>
                        <td>{r.call.destination.name}</td>
                        <td>
                          <span className={`badge ${r.call.method === 'GET' ? 'badge-low' : 'badge-medium'}`}>
                            {r.call.method}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                          {r.call.path}
                        </td>
                        <td>
                          <span className={`badge ${r.result.allowed ? 'badge-allow' : 'badge-deny'}`}>
                            {r.result.allowed ? 'ALLOW' : 'DENY'}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                          {r.result.matchedPolicy || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>
        )}

        {activeTab === 'coverage' && (
          <div>
            <div className="alert alert-info">
              Generate a coverage report showing which call patterns are covered by your policies.
            </div>
            <button
              className="btn btn-primary mb-4"
              onClick={handleGetCoverage}
              disabled={loading || policies.length === 0 || callRelations.length === 0}
            >
              {loading ? 'Generating...' : '📊 Generate Coverage Report'}
            </button>

            {coverageReport && (
              <>
                <div className="stats-grid">
                  <div className="stat-card">
                    <div
                      className="stat-value"
                      style={{
                        color:
                          coverageReport.coveragePercent >= 80
                            ? '#10b981'
                            : coverageReport.coveragePercent >= 50
                            ? '#f59e0b'
                            : '#ef4444',
                      }}
                    >
                      {coverageReport.coveragePercent}%
                    </div>
                    <div className="stat-label">Coverage</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value">{coverageReport.totalCalls}</div>
                    <div className="stat-label">Total Calls</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: '#10b981' }}>
                      {coverageReport.coveredCalls}
                    </div>
                    <div className="stat-label">Covered</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: '#ef4444' }}>
                      {coverageReport.uncoveredCalls?.length || 0}
                    </div>
                    <div className="stat-label">Uncovered</div>
                  </div>
                </div>

                {coverageReport.uncoveredCalls?.length > 0 && (
                  <div className="card">
                    <div className="card-header">
                      <h3>⚠️ Uncovered Call Patterns</h3>
                    </div>
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Source</th>
                          <th>Destination</th>
                          <th>Method</th>
                          <th>Path</th>
                        </tr>
                      </thead>
                      <tbody>
                        {coverageReport.uncoveredCalls.map((call, idx) => (
                          <tr key={idx}>
                            <td>{call.source?.name || call.source}</td>
                            <td>{call.destination?.name || call.destination}</td>
                            <td>{call.method}</td>
                            <td style={{ fontFamily: 'monospace' }}>{call.path}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'incremental' && (
          <div>
            <div className="alert alert-info">
              <strong>Incremental Simulation:</strong> Only re-simulate requests affected by policy changes for faster iteration.
              <ol style={{ marginTop: '8px', marginLeft: '20px' }}>
                <li>Build baseline with current policies</li>
                <li>Detect policy changes</li>
                <li>Run incremental simulation</li>
              </ol>
            </div>

            <div className="flex gap-2 mb-4 flex-wrap">
              <button
                className="btn btn-primary"
                onClick={handleBuildBaseline}
                disabled={loading || policies.length === 0 || callRelations.length === 0}
              >
                {loading ? 'Building...' : '🏗️ Build Baseline'}
              </button>
              <button
                className="btn btn-secondary"
                onClick={handleDetectChanges}
                disabled={loading || policies.length === 0}
              >
                {loading ? 'Detecting...' : '🔍 Detect Changes'}
              </button>
              <button
                className="btn btn-success"
                onClick={handleIncrementalSimulate}
                disabled={loading || !baselineBuilt}
              >
                {loading ? 'Simulating...' : '⚡ Run Incremental Simulation'}
              </button>
            </div>

            {baselineBuilt && (
              <div className="alert alert-success mb-4">
                ✅ Baseline built successfully with {callRelations.length} test requests
              </div>
            )}

            {policyChanges && policyChanges.changes?.length > 0 && (
              <div className="card mb-4">
                <div className="card-header">
                  <h3>📋 Detected Policy Changes ({policyChanges.count})</h3>
                </div>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Policy Name</th>
                      <th>Affected Services</th>
                    </tr>
                  </thead>
                  <tbody>
                    {policyChanges.changes.map((change, idx) => (
                      <tr key={idx}>
                        <td>
                          <span className={`badge ${
                            change.type === 'ADD' ? 'badge-allow' :
                            change.type === 'REMOVE' ? 'badge-deny' : 'badge-medium'
                          }`}>
                            {change.type}
                          </span>
                        </td>
                        <td>{change.policyName}</td>
                        <td>{change.affectedServices?.join(', ') || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {incrementalResult && (
              <>
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-value">{incrementalResult.totalCount}</div>
                    <div className="stat-label">Total Requests</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: '#64748b' }}>
                      {incrementalResult.skippedCount}
                    </div>
                    <div className="stat-label">Skipped (Cached)</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: '#f59e0b' }}>
                      {incrementalResult.affectedCount}
                    </div>
                    <div className="stat-label">Re-simulated</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-value" style={{ color: '#10b981' }}>
                      {incrementalResult.changesDetected}
                    </div>
                    <div className="stat-label">Result Changes</div>
                  </div>
                </div>

                {incrementalResult.summary?.changedResults?.length > 0 && (
                  <div className="card">
                    <div className="card-header">
                      <h3>🔄 Changed Results</h3>
                    </div>
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Source</th>
                          <th>Destination</th>
                          <th>Method</th>
                          <th>Before</th>
                          <th>After</th>
                        </tr>
                      </thead>
                      <tbody>
                        {incrementalResult.summary.changedResults.map((r, idx) => (
                          <tr key={idx}>
                            <td>{r.request?.source}</td>
                            <td>{r.request?.dest}</td>
                            <td>{r.request?.method}</td>
                            <td>
                              <span className={`badge ${r.baselineResult?.allowed ? 'badge-allow' : 'badge-deny'}`}>
                                {r.baselineResult?.allowed ? 'ALLOW' : 'DENY'}
                              </span>
                            </td>
                            <td>
                              <span className={`badge ${r.newResult?.allowed ? 'badge-allow' : 'badge-deny'}`}>
                                {r.newResult?.allowed ? 'ALLOW' : 'DENY'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Simulator;
