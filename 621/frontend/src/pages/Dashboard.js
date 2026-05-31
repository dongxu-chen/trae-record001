import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getServiceGraph, getCallRelations, loadSampleData } from '../services/api';

function Dashboard({ setActivePage }) {
  const navigate = useNavigate();
  const [serviceGraph, setServiceGraph] = useState(null);
  const [callRelations, setCallRelations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [graphRes, callsRes] = await Promise.all([
        getServiceGraph(),
        getCallRelations(),
      ]);
      setServiceGraph(graphRes.data);
      setCallRelations(callsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSampleData = async () => {
    setLoading(true);
    try {
      const res = await loadSampleData();
      setMessage(res.data.message);
      await fetchData();
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error loading sample data:', error);
    } finally {
      setLoading(false);
    }
  };

  const uniqueServices = serviceGraph?.services?.length || 0;
  const uniqueEdges = new Set(
    callRelations.map((e) => `${e.source.name}->${e.destination.name}`)
  ).size;

  const getTopServices = () => {
    const callCounts = {};
    callRelations.forEach((edge) => {
      const dest = edge.destination.name;
      callCounts[dest] = (callCounts[dest] || 0) + edge.count;
    });
    return Object.entries(callCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5);
  };

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Overview of your service mesh authorization policies</p>
      </div>

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{uniqueServices}</div>
          <div className="stat-label">Services</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{uniqueEdges}</div>
          <div className="stat-label">Unique Connections</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{callRelations.length}</div>
          <div className="stat-label">API Endpoints</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {callRelations.reduce((sum, e) => sum + e.count, 0)}
          </div>
          <div className="stat-label">Total Calls</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Quick Actions</h3>
        </div>
        <div className="flex gap-4">
          <button
            className="btn btn-primary"
            onClick={handleLoadSampleData}
            disabled={loading}
          >
            {loading ? 'Loading...' : '📊 Load Sample Data'}
          </button>
          <button
            className="btn btn-success"
            onClick={() => {
              setActivePage('policies');
              navigate('/policies');
            }}
          >
            🎯 Generate Policies
          </button>
          <button
            className="btn btn-warning"
            onClick={() => {
              setActivePage('simulator');
              navigate('/simulator');
            }}
          >
            🔬 Run Simulation
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => {
              setActivePage('compliance');
              navigate('/compliance');
            }}
          >
            ✅ Check Compliance
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner"></div>
          Loading data...
        </div>
      ) : callRelations.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <div className="empty-state-text">No data available yet</div>
            <div className="empty-state-hint">
              Click "Load Sample Data" to see a demo, or upload your own trace data
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="card">
            <div className="card-header">
              <h3>Most Called Services</h3>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Call Count</th>
                  <th>Percentage</th>
                </tr>
              </thead>
              <tbody>
                {getTopServices().map(([service, count]) => {
                  const total = callRelations.reduce((sum, e) => sum + e.count, 0);
                  const percent = ((count / total) * 100).toFixed(1);
                  return (
                    <tr key={service}>
                      <td>
                        <span className="badge badge-allow">{service}</span>
                      </td>
                      <td>{count}</td>
                      <td>
                        <div style={{ width: '100%', backgroundColor: '#334155', borderRadius: '4px', height: '8px' }}>
                          <div
                            style={{
                              width: `${percent}%`,
                              backgroundColor: '#38bdf8',
                              height: '100%',
                              borderRadius: '4px',
                            }}
                          ></div>
                        </div>
                        <span style={{ fontSize: '12px', color: '#94a3b8' }}>{percent}%</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="card">
            <div className="card-header">
              <h3>Recent Call Relations</h3>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Destination</th>
                  <th>Method</th>
                  <th>Path</th>
                  <th>Count</th>
                </tr>
              </thead>
              <tbody>
                {callRelations.slice(0, 10).map((edge, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className="policy-rule-from">{edge.source.name}</span>
                    </td>
                    <td>
                      <span className="policy-rule-to">{edge.destination.name}</span>
                    </td>
                    <td>
                      <span className={`badge ${edge.method === 'GET' ? 'badge-low' : edge.method === 'POST' ? 'badge-medium' : 'badge-high'}`}>
                        {edge.method}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{edge.path}</td>
                    <td>{edge.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;
