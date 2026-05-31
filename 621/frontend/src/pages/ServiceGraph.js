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
import { getServiceGraph, loadSampleData, setSamplingConfig, getSamplingStats, getCallRelations } from '../services/api';

function ServiceGraph() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [samplingStrategy, setSamplingStrategy] = useState('FULL');
  const [samplingStats, setSamplingStats] = useState(null);
  const [ingressServices, setIngressServices] = useState('');
  const [egressServices, setEgressServices] = useState('');
  const [showSamplingPanel, setShowSamplingPanel] = useState(false);
  const [callEdges, setCallEdges] = useState([]);

  useEffect(() => {
    fetchGraph();
  }, []);

  const fetchGraph = async () => {
    setLoading(true);
    try {
      const [graphRes, statsRes, callsRes] = await Promise.all([
        getServiceGraph(),
        getSamplingStats(),
        getCallRelations(),
      ]);
      buildGraph(graphRes.data);
      setSamplingStats(statsRes.data);
      setCallEdges(callsRes.data);
    } catch (error) {
      console.error('Error fetching service graph:', error);
    } finally {
      setLoading(false);
    }
  };

  const buildGraph = (graph) => {
    if (!graph || !graph.services) return;

    const servicePositions = {};
    const cols = Math.ceil(Math.sqrt(graph.services.length));
    const spacing = 180;

    graph.services.forEach((service, idx) => {
      const col = idx % cols;
      const row = Math.floor(idx / cols);
      servicePositions[service.name] = {
        x: col * spacing + 50,
        y: row * spacing + 50,
      };
    });

    const newNodes = graph.services.map((service) => ({
      id: service.name,
      position: servicePositions[service.name],
      data: { label: service.name },
      style: {
        padding: '12px 20px',
        borderRadius: '8px',
        backgroundColor: '#1e293b',
        border: '2px solid #38bdf8',
        color: '#e2e8f0',
        fontWeight: '600',
        minWidth: '120px',
        textAlign: 'center',
      },
    }));

    const edgeMap = {};
    const newEdges = [];

    graph.edges.forEach((edge, idx) => {
      const key = `${edge.source.name}-${edge.destination.name}`;
      if (!edgeMap[key]) {
        edgeMap[key] = {
          methods: [],
          count: 0,
          edgeType: edge.edgeType,
          sampled: edge.sampled,
        };
      }
      if (!edgeMap[key].methods.includes(edge.method)) {
        edgeMap[key].methods.push(edge.method);
      }
      edgeMap[key].count += edge.count;
    });

    Object.entries(edgeMap).forEach(([key, data], idx) => {
      const [source, target] = key.split('-');
      const edgeType = data.edgeType || 'INTERNAL';
      const edgeColors = {
        INGRESS: { stroke: '#10b981', arrow: '#10b981' },
        EGRESS: { stroke: '#f59e0b', arrow: '#f59e0b' },
        INTERNAL: { stroke: '#64748b', arrow: '#38bdf8' },
      };
      const colors = edgeColors[edgeType] || edgeColors.INTERNAL;

      newEdges.push({
        id: `edge-${idx}`,
        source,
        target,
        label: `${data.methods.join(', ')} (${data.count})`,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: colors.arrow,
        },
        style: {
          stroke: colors.stroke,
          strokeWidth: data.sampled ? 3 : 1,
          strokeDasharray: data.sampled ? '' : '5,5',
        },
        labelStyle: {
          fill: '#94a3b8',
          fontSize: '11px',
        },
        labelBgPadding: [4, 4],
        labelBgStyle: {
          fill: '#0f172a',
          fillOpacity: 0.8,
        },
      });
    });

    setNodes(newNodes);
    setEdges(newEdges);
  };

  const handleLoadSampleData = async () => {
    setLoading(true);
    try {
      const res = await loadSampleData();
      setMessage(res.data.message);
      buildGraph(res.data.serviceGraph);
      await fetchGraph();
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error loading sample data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleApplySamplingConfig = async () => {
    setLoading(true);
    try {
      const config = {
        strategy: samplingStrategy,
        ingressServices: ingressServices ? ingressServices.split(',').map(s => s.trim()).filter(Boolean),
        egressServices: egressServices ? egressServices.split(',').map(s => s.trim()).filter(Boolean),
      };
      await setSamplingConfig(config);
      setMessage('Sampling configuration applied');
      await fetchGraph();
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error setting sampling config:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>Service Graph</h2>
        <p>Visual representation of service-to-service communication with sampling support</p>
      </div>

      {message && (
        <div className="alert alert-success">{message}</div>
      )}

      {samplingStats && (
        <div className="card">
          <div className="card-header">
            <h3>Sampling Statistics</h3>
          </div>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{samplingStats.totalEdges}</div>
              <div className="stat-label">Total Edges</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: '#10b981' }}>{samplingStats.sampledEdges}</div>
              <div className="stat-label">Sampled</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: '#f59e0b' }}>{samplingStats.ingressEdges}</div>
              <div className="stat-label">Ingress</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: '#38bdf8' }}>{samplingStats.internalEdges}</div>
              <div className="stat-label">Internal</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: '#ef4444' }}>{samplingStats.egressEdges}</div>
              <div className="stat-label">Egress</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{samplingStats.samplingRate}%</div>
              <div className="stat-label">Sampling Rate</div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h3>Service Topology</h3>
          <div className="flex gap-2">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setShowSamplingPanel(!showSamplingPanel)}
            >
              ⚙️ Sampling Config
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleLoadSampleData}
              disabled={loading}
            >
              {loading ? 'Loading...' : 'Load Sample Data'}
            </button>
          </div>
        </div>

        {showSamplingPanel && (
          <div className="card" style={{ margin: '16px', backgroundColor: '#0f172a' }}>
            <div className="card-header">
              <h4>Sampling Configuration</h4>
            </div>
            <div className="row">
              <div className="col">
                <div className="form-group">
                  <label>Sampling Strategy</label>
                  <select
                    className="form-control"
                    value={samplingStrategy}
                    onChange={(e) => setSamplingStrategy(e.target.value)}
                  >
                    <option value="FULL">FULL - Sample all calls</option>
                    <option value="EDGE">EDGE - Sample only ingress/egress</option>
                    <option value="ADAPTIVE">ADAPTIVE - Dynamic sampling</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="row">
              <div className="col">
                <div className="form-group">
                  <label>Ingress Services (comma-separated)</label>
                  <input
                    type="text"
                    className="form-control"
                    value={ingressServices}
                    onChange={(e) => setIngressServices(e.target.value)}
                    placeholder="frontend-gateway, api-gateway"
                  />
                </div>
              </div>
              <div className="col">
                <div className="form-group">
                  <label>Egress Services (comma-separated)</label>
                  <input
                    type="text"
                    className="form-control"
                    value={egressServices}
                    onChange={(e) => setEgressServices(e.target.value)}
                    placeholder="payment-gateway, external-api"
                  />
                </div>
              </div>
            </div>
            <button
              className="btn btn-primary"
              onClick={handleApplySamplingConfig}
              disabled={loading}
            >
              {loading ? 'Applying...' : 'Apply Configuration'}
            </button>
          </div>
        )}

        {loading ? (
          <div className="loading">
            <div className="spinner"></div>
            Loading graph...
          </div>
        ) : (
          <div className="service-graph-container">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              fitView
            >
              <Controls />
              <MiniMap
                style={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                }}
                nodeColor="#38bdf8"
                maskColor="#0f172a"
              />
              <Background color="#334155" gap={20} />
            </ReactFlow>
          </div>
        )}

        <div className="mt-4">
          <div className="alert alert-info">
            <strong>💡 Tip:</strong> Drag nodes to rearrange the graph. Use the controls
            in the bottom-left to zoom and pan.
          </div>
        </div>

        <div className="mt-4">
          <div className="card-header">
            <h4>Legend</h4>
          </div>
          <div className="flex gap-6 flex-wrap" style={{ padding: '16px' }}>
            <div className="flex items-center gap-2">
              <div style={{ width: '24px', height: '3px', backgroundColor: '#10b981' }}></div>
              <span style={{ color: '#94a3b8' }}>Ingress (入站流量)</span>
            </div>
            <div className="flex items-center gap-2">
              <div style={{ width: '24px', height: '3px', backgroundColor: '#64748b' }}></div>
              <span style={{ color: '#94a3b8' }}>Internal (内部调用)</span>
            </div>
            <div className="flex items-center gap-2">
              <div style={{ width: '24px', height: '3px', backgroundColor: '#f59e0b' }}></div>
              <span style={{ color: '#94a3b8' }}>Egress (出站流量)</span>
            </div>
            <div className="flex items-center gap-2">
              <div style={{ width: '24px', height: '3px', border: '2px dashed #64748b' }}></div>
              <span style={{ color: '#94a3b8' }}>Not Sampled (未采样)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ServiceGraph;
