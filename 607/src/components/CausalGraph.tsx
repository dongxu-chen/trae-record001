import React, { useMemo } from 'react';
import { GitBranch } from 'lucide-react';

interface CausalNode {
  id: string;
  label: string;
  type: 'treatment' | 'outcome' | 'covariate';
  color: string;
  position: { x: number; y: number };
  size: number;
}

interface CausalEdge {
  source: string;
  target: string;
  type: 'causal' | 'confounder' | 'correlated';
  direction: 'forward' | 'undirected';
  strength: number;
  has_causal_path: boolean;
}

interface CausalGraphProps {
  nodes: CausalNode[];
  edges: CausalEdge[];
  width?: number;
  height?: number;
}

export default function CausalGraph({ nodes, edges, width = 600, height = 300 }: CausalGraphProps) {
  const padding = 60;

  const positionedNodes = useMemo(() => {
    return nodes.map((node) => ({
      ...node,
      x: padding + node.position.x * (width - 2 * padding),
      y: padding + node.position.y * (height - 2 * padding),
    }));
  }, [nodes, width, height]);

  const nodeMap = useMemo(() => {
    const map: Record<string, typeof positionedNodes[0]> = {};
    positionedNodes.forEach((node) => {
      map[node.id] = node;
    });
    return map;
  }, [positionedNodes]);

  const getEdgeColor = (edge: CausalEdge) => {
    switch (edge.type) {
      case 'causal':
        return '#10b981';
      case 'confounder':
        return '#f59e0b';
      default:
        return '#94a3b8';
    }
  };

  const getEdgeWidth = (strength: number) => {
    return Math.max(1, Math.min(4, strength * 4));
  };

  const getNodeTypeLabel = (type: string) => {
    switch (type) {
      case 'treatment':
        return '处理变量';
      case 'outcome':
        return '结果变量';
      default:
        return '协变量';
    }
  };

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-medium text-gray-700 flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-primary-500" />
          变量因果关系图
        </h4>
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-[#d4a855]"></span>
            <span className="text-gray-500">处理变量</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-[#1e3a5f]"></span>
            <span className="text-gray-500">结果变量</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-[#64748b]"></span>
            <span className="text-gray-500">协变量</span>
          </div>
        </div>
      </div>

      <svg width={width} height={height} className="mx-auto">
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#10b981" />
          </marker>
          <marker
            id="arrowhead-confounder"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#f59e0b" />
          </marker>
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="2" dy="2" stdDeviation="3" floodOpacity="0.15" />
          </filter>
        </defs>

        {edges.map((edge, index) => {
          const sourceNode = nodeMap[edge.source];
          const targetNode = nodeMap[edge.target];
          if (!sourceNode || !targetNode) return null;

          const dx = targetNode.x - sourceNode.x;
          const dy = targetNode.y - sourceNode.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const offsetX = (dx / dist) * sourceNode.size * 0.5;
          const offsetY = (dy / dist) * sourceNode.size * 0.5;

          const startX = sourceNode.x + offsetX;
          const startY = sourceNode.y + offsetY;
          const endX = targetNode.x - offsetX;
          const endY = targetNode.y - offsetY;

          const markerId = edge.type === 'causal' ? 'arrowhead' : 'arrowhead-confounder';
          const isDirected = edge.direction === 'forward';

          const midX = (startX + endX) / 2;
          const midY = (startY + endY) / 2;
          const curved = edge.type === 'correlated';
          const controlOffset = curved ? 30 : 0;
          const perpX = -dy / dist * controlOffset;
          const perpY = dx / dist * controlOffset;

          return (
            <g key={index}>
              {curved ? (
                <path
                  d={`M ${startX} ${startY} Q ${midX + perpX} ${midY + perpY} ${endX} ${endY}`}
                  fill="none"
                  stroke={getEdgeColor(edge)}
                  strokeWidth={getEdgeWidth(edge.strength)}
                  strokeDasharray={isDirected ? 'none' : '5,5'}
                  opacity={0.7}
                />
              ) : (
                <line
                  x1={startX}
                  y1={startY}
                  x2={endX}
                  y2={endY}
                  stroke={getEdgeColor(edge)}
                  strokeWidth={getEdgeWidth(edge.strength)}
                  strokeDasharray={isDirected ? 'none' : '5,5'}
                  markerEnd={isDirected ? `url(#${markerId})` : 'none'}
                  opacity={0.7}
                />
              )}
              <title>{`${edge.source} → ${edge.target} (强度: ${edge.strength.toFixed(3)})`}</title>
            </g>
          );
        })}

        {positionedNodes.map((node) => (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={node.size}
              fill={node.color}
              stroke="white"
              strokeWidth="3"
              filter="url(#shadow)"
            />
            <text
              x={node.x}
              y={node.y + 5}
              textAnchor="middle"
              fill="white"
              fontSize="12"
              fontWeight="600"
              style={{ pointerEvents: 'none' }}
            >
              {node.label.length > 8 ? node.label.substring(0, 8) + '...' : node.label}
            </text>
            <title>{`${node.label} (${getNodeTypeLabel(node.type)})`}</title>
          </g>
        ))}
      </svg>

      <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-8 h-0.5 bg-green-500"></div>
          <span className="text-gray-500">因果路径</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-8 h-0.5 bg-amber-500"></div>
          <span className="text-gray-500">混淆路径</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-8 h-0.5 bg-gray-400" style={{ borderStyle: 'dashed' }}></div>
          <span className="text-gray-500">相关关系</span>
        </div>
      </div>
    </div>
  );
}
