import React, { useState, useEffect, useMemo } from 'react';
import { GitBranch, Clock, ArrowRight, AlertCircle } from 'lucide-react';

function CorrelationBadge({ strength }) {
  const level = strength > 0.8 ? 'high' : strength > 0.5 ? 'medium' : 'low';
  return (
    <span className={`correlation-badge ${level}`}>
      {(strength * 100).toFixed(0)}%
    </span>
  );
}

function ScaleChange({ value }) {
  if (!value) return null;
  const isUp = value > 0;
  return (
    <span className={`scale-change ${isUp ? 'scale-up' : 'scale-down'}`}>
      {isUp ? '+' : ''}{value}
    </span>
  );
}

function CountdownTimer({ effectiveTime }) {
  const [timeLeft, setTimeLeft] = useState('');

  useEffect(() => {
    const calculateTimeLeft = () => {
      const target = new Date(effectiveTime).getTime();
      const now = Date.now();
      const diff = target - now;

      if (diff <= 0) {
        setTimeLeft('Effective now');
        return;
      }

      const minutes = Math.floor(diff / 60000);
      const seconds = Math.floor((diff % 60000) / 1000);
      setTimeLeft(`${minutes}:${seconds.toString().padStart(2, '0')}`);
    };

    calculateTimeLeft();
    const interval = setInterval(calculateTimeLeft, 1000);
    return () => clearInterval(interval);
  }, [effectiveTime]);

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#00d4ff' }}>
      <Clock size={14} />
      {timeLeft}
    </span>
  );
}

function DependencyGraph({ linkages }) {
  const nodes = useMemo(() => {
    const set = new Set();
    linkages.forEach(l => {
      set.add(`${l.sourceNamespace}/${l.sourceService}`);
      set.add(`${l.targetNamespace}/${l.targetService}`);
    });
    return Array.from(set);
  }, [linkages]);

  const nodePositions = useMemo(() => {
    const pos = {};
    const cols = Math.ceil(Math.sqrt(nodes.length));
    nodes.forEach((node, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      pos[node] = { x: col * 180 + 80, y: row * 100 + 60 };
    });
    return pos;
  }, [nodes]);

  const width = Math.ceil(Math.sqrt(nodes.length)) * 180 + 80;
  const height = Math.ceil(nodes.length / Math.ceil(Math.sqrt(nodes.length))) * 100 + 80;

  return (
    <div className="dependency-graph" style={{ position: 'relative', width: '100%', overflowX: 'auto' }}>
      <svg width={width} height={height} style={{ minWidth: width }}>
        {linkages.map((linkage, idx) => {
          const sourceKey = `${linkage.sourceNamespace}/${linkage.sourceService}`;
          const targetKey = `${linkage.targetNamespace}/${linkage.targetService}`;
          const sourcePos = nodePositions[sourceKey];
          const targetPos = nodePositions[targetKey];
          if (!sourcePos || !targetPos) return null;

          const midX = (sourcePos.x + targetPos.x) / 2;
          const midY = (sourcePos.y + targetPos.y) / 2;
          const color = linkage.correlationStrength > 0.8 ? '#10b981' : linkage.correlationStrength > 0.5 ? '#f59e0b' : '#6b7280';
          const strokeWidth = 1 + linkage.correlationStrength * 3;

          return (
            <g key={`edge-${idx}`}>
              <defs>
                <marker id={`arrow-${idx}`} markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
                  <path d="M0,0 L0,6 L9,3 z" fill={color} />
                </marker>
              </defs>
              <line
                x1={sourcePos.x + 40}
                y1={sourcePos.y}
                x2={targetPos.x - 40}
                y2={targetPos.y}
                stroke={color}
                strokeWidth={strokeWidth}
                markerEnd={`url(#arrow-${idx})`}
                opacity="0.8"
              />
              <rect
                x={midX - 24}
                y={midY - 10}
                width="48"
                height="20"
                rx="10"
                fill="#1a1a2e"
                stroke={color}
                strokeWidth="1"
              />
              <text
                x={midX}
                y={midY + 4}
                textAnchor="middle"
                fill={color}
                fontSize="11"
                fontWeight="600"
              >
                {(linkage.correlationStrength * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}

        {nodes.map((node) => {
          const pos = nodePositions[node];
          const [namespace, service] = node.split('/');
          return (
            <g key={node}>
              <rect
                x={pos.x - 60}
                y={pos.y - 20}
                width="120"
                height="40"
                rx="20"
                fill="#2a2a4e"
                stroke="#00d4ff"
                strokeWidth="2"
              />
              <text
                x={pos.x}
                y={pos.y - 2}
                textAnchor="middle"
                fill="#e2e8f0"
                fontSize="12"
                fontWeight="600"
              >
                {service}
              </text>
              <text
                x={pos.x}
                y={pos.y + 12}
                textAnchor="middle"
                fill="#6b7280"
                fontSize="9"
              >
                {namespace}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function ScalingLinkage({ linkages = [], pendingLinkages = [] }) {
  return (
    <div className="linkage-panel">
      <style>{`
        .linkage-panel {
          background: #1a1a2e;
          border: 1px solid #2a2a4e;
          border-radius: 12px;
          padding: 24px;
          color: #e2e8f0;
        }
        .linkage-panel h2 {
          display: flex;
          align-items: center;
          gap: 10px;
          margin: 0 0 20px 0;
          font-size: 20px;
          font-weight: 600;
          color: #ffffff;
        }
        .linkage-panel h3 {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 0 0 12px 0;
          font-size: 14px;
          font-weight: 600;
          color: #94a3b8;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .dependency-graph {
          background: #0f0f1e;
          border: 1px solid #2a2a4e;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 24px;
        }
        .graph-node {
          display: inline-flex;
          align-items: center;
          padding: 6px 16px;
          background: #2a2a4e;
          border: 2px solid #00d4ff;
          border-radius: 9999px;
          font-size: 12px;
          font-weight: 600;
          color: #e2e8f0;
        }
        .graph-arrow {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 0 12px;
          color: #00d4ff;
        }
        .linkages-table {
          width: 100%;
          border-collapse: collapse;
          background: #0f0f1e;
          border-radius: 8px;
          overflow: hidden;
          margin-bottom: 24px;
        }
        .linkages-table th {
          padding: 12px 16px;
          text-align: left;
          color: #94a3b8;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          background: #1a1a2e;
        }
        .linkages-table td {
          padding: 12px 16px;
          border-top: 1px solid #2a2a4e;
          font-size: 13px;
        }
        .linkages-table tbody tr:hover {
          background: #2a2a4e;
        }
        .pending-linkages-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .pending-linkage-item {
          background: #0f0f1e;
          border: 1px solid #2a2a4e;
          border-left: 3px solid #f59e0b;
          border-radius: 8px;
          padding: 16px;
        }
        .pending-linkage-item.effective {
          border-left-color: #10b981;
        }
        .pending-linkage-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .pending-linkage-path {
          display: flex;
          align-items: center;
          gap: 10px;
          font-weight: 500;
        }
        .pending-linkage-reason {
          color: #94a3b8;
          font-size: 12px;
          margin-top: 8px;
          display: flex;
          align-items: flex-start;
          gap: 6px;
        }
        .correlation-badge {
          display: inline-flex;
          align-items: center;
          padding: 2px 10px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 600;
        }
        .correlation-badge.high {
          background: rgba(16, 185, 129, 0.15);
          color: #10b981;
        }
        .correlation-badge.medium {
          background: rgba(245, 158, 11, 0.15);
          color: #f59e0b;
        }
        .correlation-badge.low {
          background: rgba(107, 114, 128, 0.15);
          color: #6b7280;
        }
        .scale-change {
          display: inline-flex;
          align-items: center;
          padding: 2px 10px;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 700;
        }
        .scale-change.scale-up {
          background: rgba(16, 185, 129, 0.15);
          color: #10b981;
        }
        .scale-change.scale-down {
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
        }
        .service-path {
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }
        .service-name {
          font-weight: 600;
          color: #e2e8f0;
        }
        .namespace {
          font-size: 11px;
          color: #6b7280;
        }
      `}</style>

      <h2>
        <GitBranch size={22} style={{ color: '#00d4ff' }} />
        Service Scaling Linkage
      </h2>

      {linkages.length > 0 && (
        <>
          <h3>Dependency Graph</h3>
          <DependencyGraph linkages={linkages} />
        </>
      )}

      {linkages.length > 0 && (
        <>
          <h3>Active Linkages</h3>
          <table className="linkages-table">
            <thead>
              <tr>
                <th>Source → Target</th>
                <th>Correlation</th>
                <th>Lag</th>
                <th>Weight</th>
                <th>Min Trigger</th>
              </tr>
            </thead>
            <tbody>
              {linkages.map((linkage, idx) => (
                <tr key={idx}>
                  <td>
                    <span className="service-path">
                      <span>
                        <span className="service-name">{linkage.sourceService}</span>
                        <span className="namespace"> ({linkage.sourceNamespace})</span>
                      </span>
                      <ArrowRight size={14} style={{ color: '#00d4ff' }} />
                      <span>
                        <span className="service-name">{linkage.targetService}</span>
                        <span className="namespace"> ({linkage.targetNamespace})</span>
                      </span>
                    </span>
                  </td>
                  <td><CorrelationBadge strength={linkage.correlationStrength} /></td>
                  <td>{linkage.lagSeconds}s</td>
                  <td>{linkage.weight.toFixed(2)}</td>
                  <td>{linkage.minTriggerScale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {pendingLinkages.length > 0 && (
        <>
          <h3>Pending Decisions</h3>
          <div className="pending-linkages-list">
            {pendingLinkages.map((linkage, idx) => {
              const isEffective = new Date(linkage.effectiveTime).getTime() <= Date.now();
              return (
                <div key={idx} className={`pending-linkage-item ${isEffective ? 'effective' : ''}`}>
                  <div className="pending-linkage-header">
                    <div className="pending-linkage-path">
                      <span className="service-name">{linkage.sourceService}</span>
                      <ScaleChange value={linkage.sourceScaleChange} />
                      <ArrowRight size={16} style={{ color: '#00d4ff' }} />
                      <span className="service-name">{linkage.targetService}</span>
                      <ScaleChange value={linkage.targetRecommendedChange} />
                      <CorrelationBadge strength={linkage.correlationStrength} />
                    </div>
                    <CountdownTimer effectiveTime={linkage.effectiveTime} />
                  </div>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>
                    {linkage.sourceNamespace} → {linkage.targetNamespace}
                  </div>
                  <div className="pending-linkage-reason">
                    <AlertCircle size={14} style={{ marginTop: 1, flexShrink: 0 }} />
                    {linkage.reason}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {linkages.length === 0 && pendingLinkages.length === 0 && (
        <div style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280' }}>
          <GitBranch size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
          <div>No scaling linkages configured</div>
        </div>
      )}
    </div>
  );
}
