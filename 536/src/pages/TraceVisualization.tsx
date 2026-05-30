import { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Box } from 'lucide-react';
import ReactFlow, {
  type Node,
  type Edge,
  Background,
  Controls,
  type NodeTypes,
  Position,
  MarkerType,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import Dagre from '@dagrejs/dagre';
import { api } from '@/api';
import { statusColor, modeColor } from '@/utils/format';
import type { TraceSpan, TraceDag } from '@/types';

function TraceNode({ data }: { data: { label: string; serviceName: string; durationMs: number; status: string; mode?: string; depth?: number } }) {
  const depthIndent = (data.depth || 0) * 8;
  return (
    <div
      className="bg-monitor-card border border-monitor-border rounded-lg px-4 py-3 min-w-[180px] shadow-lg backdrop-blur-sm"
      style={{ marginLeft: depthIndent }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <div
          className="w-2 h-2 rounded-full"
          style={{
            backgroundColor:
              data.status === 'COMMITTED' || data.status === 'PHASE_TWO_COMMIT'
                ? '#10B981'
                : data.status === 'FAILED' || data.status === 'ROLLEDBACK'
                  ? '#EF4444'
                  : data.status === 'ROLLBACKING' || data.status === 'TIMEOUT'
                    ? '#FFB800'
                    : '#3B82F6',
          }}
        />
        <span className="text-xs font-sans font-semibold text-monitor-text">{data.label}</span>
        {data.mode && (
          <span className={`px-1.5 py-0.5 rounded text-[8px] font-mono font-semibold ${modeColor(data.mode)}`}>
            {data.mode}
          </span>
        )}
      </div>
      <p className="text-[10px] font-mono text-monitor-text-muted">{data.serviceName}</p>
      <div className="flex items-center gap-2 mt-1.5">
        <span className="text-[10px] font-mono text-monitor-accent">{data.durationMs}ms</span>
        {data.status && (
          <span className={`px-1.5 py-0.5 rounded text-[8px] font-mono font-semibold ${statusColor(data.status)}`}>
            {data.status}
          </span>
        )}
      </div>
    </div>
  );
}

const nodeTypes: NodeTypes = {
  traceNode: TraceNode,
};

function useDagreLayout(nodes: Node[], edges: Edge[]) {
  return useMemo(() => {
    if (nodes.length === 0) return { nodes: [], edges };

    const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
    g.setGraph({
      rankdir: 'LR',
      nodesep: 60,
      ranksep: 120,
      align: 'UL',
      marginx: 40,
      marginy: 40,
    });

    nodes.forEach((node) => {
      const nodeWidth = 180;
      const nodeHeight = 70;
      g.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    edges.forEach((edge) => {
      g.setEdge(edge.source, edge.target);
    });

    Dagre.layout(g);

    const layoutedNodes = nodes.map((node) => {
      const dagreNode = g.node(node.id);
      return {
        ...node,
        position: {
          x: dagreNode.x - dagreNode.width / 2,
          y: dagreNode.y - dagreNode.height / 2,
        },
      };
    });

    return { nodes: layoutedNodes, edges };
  }, [nodes, edges]);
}

function applyForceOverlap(nodes: Node[]): Node[] {
  const nodeMap = new Map<string, { x: number; y: number; w: number; h: number }>();
  nodes.forEach((n) => {
    nodeMap.set(n.id, { x: n.position.x, y: n.position.y, w: 180, h: 70 });
  });

  for (let iter = 0; iter < 50; iter++) {
    const moves: Map<string, { dx: number; dy: number }> = new Map();
    nodes.forEach((n) => moves.set(n.id, { dx: 0, dy: 0 }));

    for (let i = 0; i < nodes.length; i++) {
      const a = nodeMap.get(nodes[i].id)!;
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodeMap.get(nodes[j].id)!;
        const overlapX = (a.w / 2 + b.w / 2 + 20) - Math.abs(a.x + a.w / 2 - b.x - b.w / 2);
        const overlapY = (a.h / 2 + b.h / 2 + 16) - Math.abs(a.y + a.h / 2 - b.y + b.h / 2);

        if (overlapX > 0 && overlapY > 0) {
          const pushX = overlapX / 2;
          const pushY = overlapY / 2;
          const dirX = a.x < b.x ? -1 : 1;
          const dirY = a.y < b.y ? -1 : 1;

          const mA = moves.get(nodes[i].id)!;
          const mB = moves.get(nodes[j].id)!;
          if (overlapX < overlapY) {
            mA.dx += dirX * pushX * 0.5;
            mB.dx -= dirX * pushX * 0.5;
          } else {
            mA.dy += dirY * pushY * 0.5;
            mB.dy -= dirY * pushY * 0.5;
          }
        }
      }
    }

    let hasMovement = false;
    nodes.forEach((n) => {
      const m = moves.get(n.id)!;
      if (Math.abs(m.dx) > 0.1 || Math.abs(m.dy) > 0.1) {
        hasMovement = true;
        const pos = nodeMap.get(n.id)!;
        pos.x += m.dx;
        pos.y += m.dy;
      }
    });

    if (!hasMovement) break;
  }

  return nodes.map((n) => {
    const pos = nodeMap.get(n.id)!;
    return { ...n, position: { x: pos.x, y: pos.y } };
  });
}

function FlowInner({
  flowNodes,
  flowEdges,
}: {
  flowNodes: Node[];
  flowEdges: Edge[];
}) {
  const { fitView } = useReactFlow();

  useEffect(() => {
    if (flowNodes.length > 0) {
      const timer = setTimeout(() => fitView({ padding: 0.15, duration: 400 }), 100);
      return () => clearTimeout(timer);
    }
  }, [flowNodes, fitView]);

  return (
    <ReactFlow
      nodes={flowNodes}
      edges={flowEdges}
      nodeTypes={nodeTypes}
      fitView
      style={{ background: '#1A2332' }}
      minZoom={0.2}
      maxZoom={2}
      proOptions={{ hideAttribution: true }}
    >
      <Background color="#1E2D3D" gap={20} />
      <Controls
        style={{ background: '#111827', borderColor: '#1E2D3D' }}
      />
    </ReactFlow>
  );
}

export default function TraceVisualization() {
  const { traceId: urlTraceId } = useParams<{ traceId: string }>();
  const navigate = useNavigate();
  const [inputTraceId, setInputTraceId] = useState(urlTraceId || '');
  const [activeTraceId, setActiveTraceId] = useState(urlTraceId || '');
  const [spans, setSpans] = useState<TraceSpan[]>([]);
  const [dag, setDag] = useState<TraceDag | null>(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<'dag' | 'waterfall'>('dag');

  useEffect(() => {
    if (!activeTraceId) return;
    setLoading(true);
    Promise.all([api.trace.getSpans(activeTraceId), api.trace.getDag(activeTraceId)])
      .then(([spansData, dagData]) => {
        setSpans(spansData);
        setDag(dagData);
      })
      .catch(() => {
        setSpans([]);
        setDag(null);
      })
      .finally(() => setLoading(false));
  }, [activeTraceId]);

  const rawNodes: Node[] = useMemo(() => {
    if (!dag || !dag.nodes) return [];
    return dag.nodes.map((node) => ({
      id: node.id,
      type: 'traceNode',
      position: { x: 0, y: 0 },
      data: {
        label: node.name,
        serviceName: node.serviceName,
        durationMs: node.durationMs,
        status: node.status,
        mode: node.transactionMode,
        depth: node.depth,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    }));
  }, [dag]);

  const rawEdges: Edge[] = useMemo(() => {
    if (!dag || !dag.edges) return [];
    return dag.edges.map((edge) => ({
      id: `${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      animated: true,
      style: { stroke: '#06D6A0', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#06D6A0' },
      labelStyle: { fill: '#94A3B8', fontSize: 10, fontFamily: 'JetBrains Mono' },
    }));
  }, [dag]);

  const { nodes: dagreNodes, edges: dagreEdges } = useDagreLayout(rawNodes, rawEdges);
  const flowNodes = useMemo(() => applyForceOverlap(dagreNodes), [dagreNodes]);

  const handleSearch = () => {
    if (inputTraceId.trim()) {
      setActiveTraceId(inputTraceId.trim());
    }
  };

  const minStart = spans.length > 0 ? Math.min(...spans.map((s) => s.startMicros)) : 0;
  const maxEnd = spans.length > 0 ? Math.max(...spans.map((s) => s.endMicros)) : 1;
  const totalRange = maxEnd - minStart || 1;

  const serviceColors = useMemo(() => {
    const services = [...new Set(spans.map((s) => s.serviceName))];
    const colors = ['#06D6A0', '#3B82F6', '#A855F7', '#F59E0B', '#EF4444', '#EC4899', '#14B8A6'];
    const map: Record<string, string> = {};
    services.forEach((svc, i) => {
      map[svc] = colors[i % colors.length];
    });
    return map;
  }, [spans]);

  const depthGroups = useMemo(() => {
    if (spans.length === 0) return {};
    const spanMap = new Map(spans.map((s) => [s.spanId, s]));
    const groups: Record<number, TraceSpan[]> = {};

    function getDepth(spanId: string, visited: Set<string>): number {
      if (visited.has(spanId)) return 0;
      visited.add(spanId);
      const span = spanMap.get(spanId);
      if (!span || !span.parentSpanId) return 0;
      return 1 + getDepth(span.parentSpanId, visited);
    }

    spans.forEach((span) => {
      const depth = getDepth(span.spanId, new Set());
      if (!groups[depth]) groups[depth] = [];
      groups[depth].push(span);
    });
    return groups;
  }, [spans]);

  return (
    <div className="p-8">
      <div className="flex items-center gap-4 mb-8">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-lg bg-monitor-card border border-monitor-border text-monitor-text-muted hover:text-monitor-text hover:border-monitor-accent transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h2 className="text-2xl font-sans font-bold text-monitor-text">链路可视化</h2>
          <p className="text-monitor-text-muted text-sm mt-1 font-sans">力导向分层布局 · 自动防重叠 · 分布式事务执行链路追踪</p>
        </div>
        {dag && dag.nodes && dag.nodes.length > 0 && (
          <div className="flex items-center gap-2 text-[10px] font-mono text-monitor-text-muted">
            <div className="w-2 h-2 rounded-full bg-monitor-accent" />
            {dag.nodes.length} 节点 · {dag.edges?.length || 0} 连接
          </div>
        )}
      </div>

      <div className="bg-monitor-card border border-monitor-border rounded-xl p-5 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <input
              type="text"
              placeholder="输入 Trace ID 查询链路..."
              value={inputTraceId}
              onChange={(e) => setInputTraceId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full bg-monitor-surface border border-monitor-border rounded-lg px-4 py-2.5 text-sm font-mono text-monitor-text placeholder:text-monitor-text-muted focus:outline-none focus:border-monitor-accent"
            />
          </div>
          <button
            onClick={handleSearch}
            className="px-5 py-2.5 rounded-lg bg-monitor-accent text-monitor-bg text-sm font-sans font-semibold hover:bg-monitor-accent/90 transition-colors"
          >
            查询
          </button>
          <div className="flex bg-monitor-surface border border-monitor-border rounded-lg overflow-hidden">
            <button
              onClick={() => setView('dag')}
              className={`px-4 py-2.5 text-xs font-sans font-medium transition-colors ${
                view === 'dag' ? 'bg-monitor-accent/10 text-monitor-accent' : 'text-monitor-text-muted hover:text-monitor-text'
              }`}
            >
              DAG 图
            </button>
            <button
              onClick={() => setView('waterfall')}
              className={`px-4 py-2.5 text-xs font-sans font-medium transition-colors ${
                view === 'waterfall' ? 'bg-monitor-accent/10 text-monitor-accent' : 'text-monitor-text-muted hover:text-monitor-text'
              }`}
            >
              瀑布图
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="bg-monitor-card border border-monitor-border rounded-xl h-96 flex items-center justify-center">
          <div className="animate-pulse text-monitor-text-muted text-sm font-sans">加载链路数据中...</div>
        </div>
      ) : !activeTraceId ? (
        <div className="bg-monitor-card border border-monitor-border rounded-xl h-96 flex items-center justify-center">
          <div className="text-center">
            <Box className="w-12 h-12 text-monitor-text-muted mx-auto mb-3" />
            <p className="text-monitor-text-muted text-sm font-sans">输入 Trace ID 开始查询</p>
          </div>
        </div>
      ) : view === 'dag' ? (
        <div className="bg-monitor-card border border-monitor-border rounded-xl overflow-hidden" style={{ height: 560 }}>
          <ReactFlowProvider>
            <FlowInner flowNodes={flowNodes} flowEdges={dagreEdges} />
          </ReactFlowProvider>
        </div>
      ) : (
        <div className="bg-monitor-card border border-monitor-border rounded-xl p-6">
          {spans.length === 0 ? (
            <div className="text-center py-12 text-monitor-text-muted text-sm font-sans">无Span数据</div>
          ) : (
            <div>
              <div className="flex items-center gap-4 mb-4">
                {Object.entries(serviceColors).map(([svc, color]) => (
                  <div key={svc} className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color }} />
                    <span className="text-[10px] font-mono text-monitor-text-muted">{svc}</span>
                  </div>
                ))}
              </div>

              {Object.entries(depthGroups)
                .sort(([a], [b]) => Number(a) - Number(b))
                .map(([depth, groupSpans]) => (
                  <div key={depth} className="mb-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[10px] font-mono text-monitor-text-muted bg-monitor-surface px-2 py-0.5 rounded">
                        Layer {depth}
                      </span>
                      <div className="flex-1 h-px bg-monitor-border" />
                    </div>
                    <div className="space-y-1">
                      {groupSpans.map((span) => {
                        const leftPercent = ((span.startMicros - minStart) / totalRange) * 100;
                        const widthPercent = Math.max((span.durationMicros / totalRange) * 100, 0.5);
                        return (
                          <div
                            key={span.spanId}
                            className="flex items-center gap-3 group hover:bg-monitor-hover/20 rounded px-2 py-1 transition-colors"
                            style={{ paddingLeft: `${Number(depth) * 24 + 8}px` }}
                          >
                            <div className="w-32 flex-shrink-0">
                              <span className="text-[10px] font-mono text-monitor-text-dim truncate block">
                                {span.name}
                              </span>
                            </div>
                            <div className="flex-1 h-6 bg-monitor-surface rounded relative overflow-hidden">
                              <div
                                className="absolute top-0.5 bottom-0.5 rounded"
                                style={{
                                  left: `${leftPercent}%`,
                                  width: `${widthPercent}%`,
                                  backgroundColor: serviceColors[span.serviceName] || '#06D6A0',
                                  opacity: 0.8,
                                }}
                              />
                            </div>
                            <div className="w-20 text-right flex-shrink-0">
                              <span className="text-[10px] font-mono text-monitor-text-muted">
                                {(span.durationMicros / 1000).toFixed(1)}ms
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}

              <div className="flex items-center justify-between mt-4 text-[10px] font-mono text-monitor-text-muted">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{new Date(minStart / 1000).toLocaleTimeString('zh-CN')}</span>
                </div>
                <span>总时长: {((maxEnd - minStart) / 1000).toFixed(1)}ms</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
