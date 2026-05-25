import React, { useEffect, useRef, useState, useCallback } from 'react';

const NODE_COLORS = {
  start: '#4ade80',
  end: '#f87171',
  process: '#60a5fa',
  decision: '#fbbf24',
  input_output: '#a78bfa',
  unknown: '#9ca3af',
};

const NODE_LABELS = {
  start: '开始',
  end: '结束',
  process: '处理',
  decision: '判断',
  input_output: '输入/输出',
  unknown: '未知',
};

const NODE_TYPES_LIST = [
  { value: 'start', label: '开始' },
  { value: 'end', label: '结束' },
  { value: 'process', label: '处理' },
  { value: 'decision', label: '判断' },
  { value: 'input_output', label: '输入/输出' },
];

const EDGE_COLORS = {
  yes: '#22c55e',
  no: '#ef4444',
  default: '#64748b',
};

function getEdgeColor(label) {
  if (!label) return EDGE_COLORS.default;
  const l = label.toLowerCase();
  if (/是|yes|true|y/i.test(l)) return EDGE_COLORS.yes;
  if (/否|no|false|n/i.test(l)) return EDGE_COLORS.no;
  return EDGE_COLORS.default;
}

export default function FlowchartPreview({
  imageUrl,
  nodes: initialNodes,
  edges: initialEdges,
  editMode = false,
  onNodesChange,
  onEdgesChange,
  selectedNodeId,
  onSelectNode,
  selectedEdgeId,
  onSelectEdge,
}) {
  const imgRef = useRef(null);
  const svgRef = useRef(null);
  const [size, setSize] = useState({ width: 0, height: 0, scale: 1 });
  const [nodes, setNodes] = useState(initialNodes || []);
  const [edges, setEdges] = useState(initialEdges || []);
  const [dragState, setDragState] = useState(null);
  const [resizing, setResizing] = useState(null);

  useEffect(() => {
    setNodes(initialNodes || []);
  }, [initialNodes]);

  useEffect(() => {
    setEdges(initialEdges || []);
  }, [initialEdges]);

  useEffect(() => {
    if (onNodesChange) onNodesChange(nodes);
  }, [nodes, onNodesChange]);

  useEffect(() => {
    if (onEdgesChange) onEdgesChange(edges);
  }, [edges, onEdgesChange]);

  useEffect(() => {
    if (imgRef.current) {
      const rect = imgRef.current.getBoundingClientRect();
      setSize({
        width: rect.width,
        height: rect.height,
        scale: 1,
      });
    }
  }, [imageUrl]);

  const handleImgLoad = () => {
    if (imgRef.current) {
      const rect = imgRef.current.getBoundingClientRect();
      const naturalWidth = imgRef.current.naturalWidth;
      const scale = rect.width / naturalWidth;
      setSize({
        width: rect.width,
        height: rect.height,
        scale,
      });
    }
  };

  const getSvgPoint = useCallback((e) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / size.scale,
      y: (e.clientY - rect.top) / size.scale,
    };
  }, [size.scale]);

  const handleNodeMouseDown = (e, nodeId) => {
    if (!editMode) return;
    e.stopPropagation();
    const point = getSvgPoint(e);
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;

    setDragState({
      type: 'move',
      nodeId,
      offsetX: point.x - node.x,
      offsetY: point.y - node.y,
    });
    if (onSelectNode) onSelectNode(nodeId);
  };

  const handleResizeMouseDown = (e, nodeId, corner) => {
    if (!editMode) return;
    e.stopPropagation();
    setResizing({ nodeId, corner });
    if (onSelectNode) onSelectNode(nodeId);
  };

  const handleSvgMouseMove = useCallback((e) => {
    const point = getSvgPoint(e);

    if (dragState?.type === 'move') {
      setNodes((prev) =>
        prev.map((n) =>
          n.id === dragState.nodeId
            ? {
                ...n,
                x: Math.max(0, point.x - dragState.offsetX),
                y: Math.max(0, point.y - dragState.offsetY),
              }
            : n
        )
      );
    }

    if (resizing) {
      setNodes((prev) =>
        prev.map((n) => {
          if (n.id !== resizing.nodeId) return n;
          let { x, y, width, height } = n;
          switch (resizing.corner) {
            case 'se':
              width = Math.max(40, point.x - x);
              height = Math.max(30, point.y - y);
              break;
            case 'sw':
              const newX = Math.min(point.x, x + width - 40);
              width = x + width - newX;
              x = newX;
              height = Math.max(30, point.y - y);
              break;
            case 'ne':
              width = Math.max(40, point.x - x);
              const newY = Math.min(point.y, y + height - 30);
              height = y + height - newY;
              y = newY;
              break;
            case 'nw':
              const nx = Math.min(point.x, x + width - 40);
              const ny = Math.min(point.y, y + height - 30);
              width = x + width - nx;
              height = y + height - ny;
              x = nx;
              y = ny;
              break;
          }
          return { ...n, x, y, width, height };
        })
      );
    }
  }, [dragState, resizing, getSvgPoint]);

  const handleSvgMouseUp = useCallback(() => {
    setDragState(null);
    setResizing(null);
  }, []);

  useEffect(() => {
    if (editMode && (dragState || resizing)) {
      window.addEventListener('mousemove', handleSvgMouseMove);
      window.addEventListener('mouseup', handleSvgMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleSvgMouseMove);
        window.removeEventListener('mouseup', handleSvgMouseUp);
      };
    }
  }, [editMode, dragState, resizing, handleSvgMouseMove, handleSvgMouseUp]);

  const handleUpdateNode = (nodeId, updates) => {
    setNodes((prev) => prev.map((n) => (n.id === nodeId ? { ...n, ...updates } : n)));
  };

  const handleAddNode = (type) => {
    const newNode = {
      id: `node_${Date.now()}`,
      type,
      x: 50 + Math.random() * 200,
      y: 50 + Math.random() * 200,
      width: 100,
      height: 50,
      text: '',
    };
    setNodes((prev) => [...prev, newNode]);
    if (onSelectNode) onSelectNode(newNode.id);
  };

  const handleDeleteNode = (nodeId) => {
    setNodes((prev) => prev.filter((n) => n.id !== nodeId));
    setEdges((prev) => prev.filter((e) => e.from !== nodeId && e.to !== nodeId));
    if (onSelectNode) onSelectNode(null);
  };

  const handleAddEdge = (fromId, toId, label = '') => {
    const newEdge = {
      id: `edge_${Date.now()}`,
      from: fromId,
      to: toId,
      label,
    };
    setEdges((prev) => [...prev, newEdge]);
  };

  const handleDeleteEdge = (edgeId) => {
    setEdges((prev) => prev.filter((e) => e.id !== edgeId));
    if (onSelectEdge) onSelectEdge(null);
  };

  const handleUpdateEdge = (edgeId, updates) => {
    setEdges((prev) => prev.map((e) => (e.id === edgeId ? { ...e, ...updates } : e)));
  };

  const handleSvgClick = (e) => {
    if (!editMode) return;
    if (e.target === svgRef.current) {
      if (onSelectNode) onSelectNode(null);
      if (onSelectEdge) onSelectEdge(null);
    }
  };

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const selectedEdge = edges.find((e) => e.id === selectedEdgeId);

  const decisionCount = nodes.filter((n) => n.type === 'decision').length;
  const edgeWithLabel = edges.filter((e) => e.label).length;

  if (!imageUrl) return null;

  return (
    <div className="preview-container">
      {editMode && (
        <div className="edit-toolbar">
          <span className="toolbar-title">✏️ 编辑模式</span>
          <div className="toolbar-actions">
            <span className="toolbar-label">添加节点:</span>
            {NODE_TYPES_LIST.map((t) => (
              <button
                key={t.value}
                className="add-node-btn"
                style={{ backgroundColor: NODE_COLORS[t.value] }}
                onClick={() => handleAddNode(t.value)}
              >
                + {t.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="image-wrapper" style={{ position: 'relative' }}>
        <img
          ref={imgRef}
          src={imageUrl}
          alt="Flowchart"
          className="preview-image"
          onLoad={handleImgLoad}
        />

        {size.width > 0 && nodes.length > 0 && (
          <svg
            ref={svgRef}
            className="overlay-svg"
            width={size.width}
            height={size.height}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              pointerEvents: editMode ? 'auto' : 'none',
              cursor: editMode ? 'crosshair' : 'default',
            }}
            onClick={handleSvgClick}
          >
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#64748b" />
              </marker>
              <marker
                id="arrowhead-yes"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill={EDGE_COLORS.yes} />
              </marker>
              <marker
                id="arrowhead-no"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill={EDGE_COLORS.no} />
              </marker>
            </defs>

            {edges.map((edge, i) => {
              const from = nodes.find((n) => n.id === edge.from);
              const to = nodes.find((n) => n.id === edge.to);
              if (!from || !to) return null;
              const fx = (from.x + from.width / 2) * size.scale;
              const fy = (from.y + from.height / 2) * size.scale;
              const tx = (to.x + to.width / 2) * size.scale;
              const ty = (to.y + to.height / 2) * size.scale;
              const midX = (fx + tx) / 2;
              const midY = (fy + ty) / 2;
              const color = getEdgeColor(edge.label);
              const markerId = edge.label
                ? (/是|yes|true|y/i.test(edge.label)
                    ? 'arrowhead-yes'
                    : /否|no|false|n/i.test(edge.label)
                      ? 'arrowhead-no'
                      : 'arrowhead')
                : 'arrowhead';
              const isSelected = edge.id === selectedEdgeId;

              return (
                <g
                  key={`edge-${edge.id || i}`}
                  onClick={(e) => {
                    if (editMode) {
                      e.stopPropagation();
                      if (onSelectEdge) onSelectEdge(edge.id);
                    }
                  }}
                  style={{ cursor: editMode ? 'pointer' : 'default' }}
                >
                  <line
                    x1={fx}
                    y1={fy}
                    x2={tx}
                    y2={ty}
                    stroke={isSelected ? '#f472b6' : color}
                    strokeWidth={isSelected ? 3 : 2}
                    strokeDasharray={edge.label ? '0' : '4,4'}
                    markerEnd={`url(#${markerId})`}
                  />
                  {edge.label && (
                    <g>
                      <rect
                        x={midX - 14}
                        y={midY - 9}
                        width="28"
                        height="16"
                        rx="4"
                        fill={isSelected ? '#f472b6' : color}
                        fillOpacity="0.85"
                      />
                      <text
                        x={midX}
                        y={midY + 3}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fontSize="10"
                        fill="white"
                        fontWeight="bold"
                      >
                        {edge.label}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            {nodes.map((node) => {
              const isSelected = node.id === selectedNodeId;
              const x = node.x * size.scale;
              const y = node.y * size.scale;
              const w = node.width * size.scale;
              const h = node.height * size.scale;

              return (
                <g
                  key={node.id}
                  onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                  onClick={(e) => {
                    if (editMode) {
                      e.stopPropagation();
                      if (onSelectNode) onSelectNode(node.id);
                    }
                  }}
                  style={{ cursor: editMode ? 'move' : 'default' }}
                >
                  <rect
                    x={x}
                    y={y}
                    width={w}
                    height={h}
                    fill={NODE_COLORS[node.type] || NODE_COLORS.unknown}
                    fillOpacity={isSelected ? 0.4 : 0.2}
                    stroke={isSelected ? '#f472b6' : NODE_COLORS[node.type] || NODE_COLORS.unknown}
                    strokeWidth={isSelected ? 3 : 2}
                    rx={node.type === 'start' || node.type === 'end' ? '50%' : '4'}
                  />
                  <text
                    x={x + w / 2}
                    y={y + h / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize="10"
                    fill="#0f172a"
                    fontWeight="bold"
                    pointerEvents="none"
                  >
                    {NODE_LABELS[node.type] || node.type}
                  </text>
                  {isSelected && editMode && (
                    <g className="resize-handles">
                      {['nw', 'ne', 'sw', 'se'].map((corner) => {
                        const cx = corner.includes('e') ? x + w : x;
                        const cy = corner.includes('s') ? y + h : y;
                        return (
                          <rect
                            key={corner}
                            x={cx - 4}
                            y={cy - 4}
                            width="8"
                            height="8"
                            fill="#f472b6"
                            stroke="white"
                            strokeWidth="1"
                            onMouseDown={(e) => handleResizeMouseDown(e, node.id, corner)}
                            style={{ cursor: `${corner}-resize` }}
                          />
                        );
                      })}
                    </g>
                  )}
                </g>
              );
            })}
          </svg>
        )}
      </div>

      {nodes.length > 0 && (
        <div className="node-legend">
          <h4>检测到的节点 ({nodes.length})</h4>
          <div className="stats-row">
            <span className="stat-chip">判断: {decisionCount}</span>
            <span className="stat-chip">连线: {edges.length}</span>
            {edgeWithLabel > 0 && <span className="stat-chip labeled">已标注: {edgeWithLabel}</span>}
          </div>
          <ul className="node-list">
            {nodes.map((node) => (
              <li
                key={node.id}
                className={`node-item ${node.id === selectedNodeId ? 'selected' : ''}`}
                onClick={() => editMode && onSelectNode && onSelectNode(node.id)}
                style={{ cursor: editMode ? 'pointer' : 'default' }}
              >
                <span
                  className="node-badge"
                  style={{ backgroundColor: NODE_COLORS[node.type] || NODE_COLORS.unknown }}
                >
                  {NODE_LABELS[node.type] || node.type}
                </span>
                <span className="node-text">{node.text || '(无文本)'}</span>
                {editMode && node.id === selectedNodeId && (
                  <button
                    className="delete-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteNode(node.id);
                    }}
                  >
                    ×
                  </button>
                )}
              </li>
            ))}
          </ul>

          {editMode && selectedNode && (
            <div className="node-editor">
              <h5>编辑节点</h5>
              <div className="form-group">
                <label>类型</label>
                <select
                  value={selectedNode.type}
                  onChange={(e) => handleUpdateNode(selectedNode.id, { type: e.target.value })}
                >
                  {NODE_TYPES_LIST.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>文本</label>
                <input
                  type="text"
                  value={selectedNode.text || ''}
                  onChange={(e) => handleUpdateNode(selectedNode.id, { text: e.target.value })}
                  placeholder="输入节点文本"
                />
              </div>
              <div className="form-group">
                <label>位置</label>
                <div className="pos-inputs">
                  <input
                    type="number"
                    value={Math.round(selectedNode.x)}
                    onChange={(e) => handleUpdateNode(selectedNode.id, { x: Number(e.target.value) })}
                  />
                  <input
                    type="number"
                    value={Math.round(selectedNode.y)}
                    onChange={(e) => handleUpdateNode(selectedNode.id, { y: Number(e.target.value) })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>大小</label>
                <div className="pos-inputs">
                  <input
                    type="number"
                    value={Math.round(selectedNode.width)}
                    onChange={(e) => handleUpdateNode(selectedNode.id, { width: Number(e.target.value) })}
                  />
                  <input
                    type="number"
                    value={Math.round(selectedNode.height)}
                    onChange={(e) => handleUpdateNode(selectedNode.id, { height: Number(e.target.value) })}
                  />
                </div>
              </div>
            </div>
          )}

          {edges.length > 0 && (
            <div className="edge-list">
              <h4>连线关系 ({edges.length})</h4>
              {editMode && (
                <div className="edge-add-form">
                  <select onChange={(e) => {}} id="from-select">
                    <option value="">选择起点</option>
                    {nodes.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.text || n.id}
                      </option>
                    ))}
                  </select>
                  <span>→</span>
                  <select id="to-select">
                    <option value="">选择终点</option>
                    {nodes.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.text || n.id}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => {
                      const from = document.getElementById('from-select').value;
                      const to = document.getElementById('to-select').value;
                      if (from && to) handleAddEdge(from, to);
                    }}
                  >
                    + 添加
                  </button>
                </div>
              )}
              <ul>
                {edges.map((edge, i) => {
                  const from = nodes.find((n) => n.id === edge.from);
                  const to = nodes.find((n) => n.id === edge.to);
                  const isSelected = edge.id === selectedEdgeId;
                  return (
                    <li
                      key={edge.id || i}
                      className={`edge-item ${isSelected ? 'selected' : ''}`}
                      onClick={() => editMode && onSelectEdge && onSelectEdge(edge.id)}
                      style={{ cursor: editMode ? 'pointer' : 'default' }}
                    >
                      <span className="edge-from">{from?.text || edge.from}</span>
                      <span className="edge-arrow">→</span>
                      <span className="edge-to">{to?.text || edge.to}</span>
                      {edge.label && (
                        <span
                          className="edge-label"
                          style={{
                            backgroundColor: getEdgeColor(edge.label),
                            color: 'white',
                          }}
                        >
                          {edge.label}
                        </span>
                      )}
                      {editMode && (
                        <>
                          {isSelected && (
                            <button
                              className="delete-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteEdge(edge.id);
                              }}
                            >
                              ×
                            </button>
                          )}
                          {isSelected && (
                            <input
                              className="label-input"
                              type="text"
                              value={edge.label || ''}
                              placeholder="标签(是/否)"
                              onClick={(e) => e.stopPropagation()}
                              onChange={(e) => handleUpdateEdge(edge.id, { label: e.target.value })}
                            />
                          )}
                        </>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
