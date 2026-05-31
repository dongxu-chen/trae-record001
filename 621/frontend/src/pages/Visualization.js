import React, { useState, useEffect } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  generatePolicies,
  getCallRelations,
  getCoverageVisualization,
  loadSampleData,
} from '../services/api';

function Visualization() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [policies, setPolicies] = useState([]);
  const [coverage, setCoverage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [callRelations, setCallRelations] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const callsRes = await getCallRelations();
      const calls = callsRes.data;
      setCallRelations(calls);

      const policiesRes = await generatePolicies(calls);
      setPolicies(policiesRes.data);

      await updateCoverage(policiesRes.data, calls);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateCoverage = async (pols, calls) => {
    try {
      const graph = {
        services: [...new Set(calls.flatMap(c => [c.source.name, c.destination.name]))].map(name => ({ name })),
        edges: calls,
      };

      const res = await getCoverageVisualization(pols, graph);
      setCoverage(res.data);
      buildGraph(res.data);
    } catch (error) {
      console.error('Error getting coverage:', error);
    }
  };

  const buildGraph = (coverageData) => {
    if (!coverageData || !coverageData.serviceGraph) return;

    const graph = coverageData.serviceGraph;
    const coveredEdgeKeys = new Set(coverageData.coveredEdgeKeys || []);

    const servicePositions = {};
    const services = [...new Set([...graph.edges.map(e => e.source.name), ...graph.edges.map(e => e.destination.name)])];
    const cols = Math.ceil(Math.sqrt(services.length));

    services.forEach((service, idx) => {
      const row = Math.floor(idx / cols);
      const col = idx % cols;
      servicePositions[service] = {
        x: 100 + col * 180,
        y: 100 + row * 120,
      };
    });

    const newNodes = services.map(service => ({
      id: service,
      data: { label: service },
      position: servicePositions[service],
      style: {
        padding: '10px 16px',
        borderRadius: '8px',
        backgroundColor: '#1e293b',
        border: '2px solid #334155',
        color: '#e2e8f0',
        fontWeight: '500',
      },
    }));

    const newEdges = graph.edges.map((edge, idx) => {
      const edgeKey = `${edge.source.name}->${edge.destination.name}`;
      const isCovered = coveredEdgeKeys.has(edgeKey);

      return {
        id: `edge-${idx}`,
        source: edge.source.name,
        target: edge.destination.name,
        label: isCovered ? '✓' : '✗',
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isCovered ? '#10b981' : '#ef4444',
        },
        style: {
          stroke: isCovered ? '#10b981' : '#ef4444',
          strokeWidth: isCovered ? 3 : 2,
          strokeDasharray: isCovered ? '' : '5,5',
        },
        labelStyle: {
          fill: isCovered ? '#10b981' : '#ef4444',
          fontWeight: 'bold',
          fontSize: '14px',
        },
        labelBgStyle: {
          fill: '#0f172a',
          fillOpacity: 0.9,
        },
      };
    });

    setNodes(newNodes);
    setEdges(newEdges);
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
        <h2>Policy Coverage Visualization</h2>
        <p>Visualize which service communications are covered by your policies</p>
      </div>

      {message && (
        <div className="alert alert-info">{message}</div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Controls</h3>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleLoadSampleData}
            disabled={loading}
          >
            {loading ? 'Loading...' : '📊 Load Sample Data'}
          </button>
        </div>
      </div>

      {coverage && (
        <div className="card">
          <div className="compliance-score">
            <div
              className={`score-circle ${getScoreClass(coverage.overallCoverage)}`}
              style={{ '--score': `${coverage.overallCoverage}%` }}
            >
              {coverage.overallCoverage.toFixed(1)}%
            </div>
            <div className="score-label">Overall Policy Coverage</div>
          </div>

          <div className="stats-grid" style={{ marginTop: '16px' }}>
            <div className="stat-card">
              <div className="stat-value">{coverage.totalServices}</div>
              <div className="stat-label">Total Services</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: '#38bdf8' }}>{coverage.totalEdges}</div>
              <div className="stat-label">Total Edges</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: '#10b981' }}>{coverage.coveredEdges}</div>
              <div className="stat-label">Covered</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: '#ef4444' }}>{coverage.uncoveredEdges}</div>
              <div className="stat-label">Uncovered</div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Coverage Topology</h3>
        </div>
        <div style={{ height: '500px', border: '1px solid #334155', borderRadius: '8px' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
          >
            <MiniMap
              style={{ backgroundColor: '#0f172a' }}
              nodeColor={(node) => node.style?.backgroundColor || '#334155'}
              maskColor="rgba(15, 23, 42, 0.8)"
            />
            <Controls />
            <Background color="#334155" gap={16} />
          </ReactFlow>
        </div>
        <div className="mt-4">
          <div className="card-header">
            <h4>Legend</h4>
          </div>
          <div className="flex gap-6 flex-wrap" style={{ padding: '16px' }}>
            <div className="flex items-center gap-2">
              <div style={{ width: '24px', height: '3px', backgroundColor: '#10b981' }}></div>
              <span style={{ color: '#94a3b8' }}>✓ Covered by policy</span>
            </div>
            <div className="flex items-center gap-2">
              <div style={{ width: '24px', height: '3px', border: '2px dashed #ef4444' }}></div>
              <span style={{ color: '#94a3b8' }}>✗ Not covered</span>
            </div>
          </div>
        </div>
      </div>

      {coverage && coverage.policyCoverages && (
        <div className="card">
          <div className="card-header">
            <h3>Policy-by-Policy Coverage</h3>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Policy Name</th>
                <th>Covered</th>
                <th>Coverage %</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {coverage.policyCoverages.map((pc, idx) => (
                <tr key={idx}>
                  <td style={{ fontFamily: 'monospace' }}>{pc.policyName}</td>
                  <td>{pc.coveredCalls} / {pc.totalCalls}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '100px', height: '8px', backgroundColor: '#334155', borderRadius: '4px', overflow: 'hidden' }}>
                        <div
                          style={{
                            width: `${pc.coverageRate}%`,
                            height: '100%',
                            backgroundColor: pc.coverageRate >= 50 ? '#10b981' : '#ef4444',
                          }}
                        ></div>
                      </div>
                      <span>{pc.coverageRate.toFixed(1)}%</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${pc.coverageRate >= 50 ? 'badge-allow' : 'badge-deny'}`}>
                      {pc.coverageRate >= 50 ? 'Good' : 'Low'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Policies ({policies.length})</h3>
        </div>
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {policies.map((policy, idx) => (
            <div key={idx} className="card" style={{ margin: '8px', padding: '12px' }}>
              <div className="flex justify-between items-start">
                <div>
                  <div style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{policy.name}</div>
                  <div style={{ color: '#94a3b8', fontSize: '12px', marginTop: '4px' }}>
                    Namespace: {policy.namespace || 'default'}
                  </div>
                </div>
                <span className={`badge ${policy.action === 'ALLOW' ? 'badge-allow' : 'badge-deny'}`}>
                  {policy.action}
                </span>
              </div>
              <div style={{ marginTop: '8px', fontSize: '12px', color: '#94a3b8' }}>
                Rules: {policy.rules?.length || 0}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Visualization;
