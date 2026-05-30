import { useRef, useCallback, useEffect, useState, useMemo } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import { ZoomIn, ZoomOut, Maximize2, RotateCcw, Circle, ChevronDown, ChevronRight, Layers, LayersOff } from 'lucide-react';
import { useLineageStore } from '@/stores/useLineageStore';
import { FieldNode, LineageEdge } from '@/types';

interface GraphNode extends FieldNode {
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

interface GraphEdge extends LineageEdge {
  source: string | GraphNode;
  target: string | GraphNode;
}

const getNodeColor = (type: string, isSelected: boolean, isCollapsed: boolean) => {
  if (isSelected) return '#165DFF';
  if (isCollapsed) return '#86909C';
  
  const colors: Record<string, string> = {
    field: '#69b1ff',
    table: '#36CFC9',
    etl: '#FF7D00',
    report: '#F759AB',
  };
  return colors[type] || '#86909C';
};

const getNodeSize = (type: string, isCollapsed: boolean) => {
  if (isCollapsed) return 20;
  const sizes: Record<string, number> = {
    field: 8,
    table: 14,
    etl: 16,
    report: 18,
  };
  return sizes[type] || 10;
};

const getNodeLabel = (node: GraphNode) => {
  if (node.type === 'field') return node.name;
  if (node.type === 'table') return node.name;
  return node.name;
};

export const LineageGraph = () => {
  const graphRef = useRef<ForceGraphMethods>();
  const containerRef = useRef<HTMLDivElement>(null);
  const { 
    analysisResult, 
    selectedNode, 
    setSelectedNode, 
    isAnalyzing,
    collapsedNodes,
    toggleNodeExpand,
    expandAll,
    collapseAll,
    getVisibleNodes,
    getVisibleEdges,
  } = useLineageStore();
  
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    if (graphRef.current && analysisResult) {
      setTimeout(() => {
        graphRef.current?.zoomToFit(400, 60);
      }, 500);
    }
  }, [analysisResult, collapsedNodes.size]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
  }, [setSelectedNode]);

  const handleNodeRightClick = useCallback((node: GraphNode) => {
    if (node.hasChildren) {
      toggleNodeExpand(node.id);
    }
  }, [toggleNodeExpand]);

  const handleNodeHover = useCallback((node: GraphNode | null) => {
    setHoveredNode(node);
    if (containerRef.current) {
      containerRef.current.style.cursor = node ? (node.hasChildren ? 'pointer' : 'default') : 'default';
    }
  }, []);

  const zoomIn = () => {
    graphRef.current?.zoom(1.2, 200);
  };

  const zoomOut = () => {
    graphRef.current?.zoom(0.8, 200);
  };

  const centerView = () => {
    graphRef.current?.zoomToFit(400, 60);
  };

  const resetView = () => {
    graphRef.current?.zoomToFit(400, 60);
    graphRef.current?.d3Force('center')?.strength(0.05);
    graphRef.current?.d3ReheatSimulation();
  };

  const visibleNodes = useMemo(() => getVisibleNodes(), [getVisibleNodes, collapsedNodes, analysisResult]);
  const visibleEdges = useMemo(() => getVisibleEdges(), [getVisibleEdges, collapsedNodes, analysisResult]);

  const graphData = useMemo(() => ({
    nodes: visibleNodes as GraphNode[],
    links: visibleEdges.map(e => ({
      ...e,
      source: e.source,
      target: e.target,
    })) as GraphEdge[],
  }), [visibleNodes, visibleEdges]);

  if (!analysisResult && !isAnalyzing) {
    return (
      <div ref={containerRef} className="flex-1 bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-24 h-24 mx-auto mb-6 bg-gray-100 rounded-full flex items-center justify-center">
            <Circle className="w-12 h-12 text-gray-300" />
          </div>
          <h3 className="text-lg font-medium text-gray-600 mb-2">开始血缘分析</h3>
          <p className="text-sm text-gray-400">
            在左侧输入字段名称，点击"开始分析"查看影响链路
          </p>
        </div>
      </div>
    );
  }

  if (isAnalyzing) {
    return (
      <div ref={containerRef} className="flex-1 bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
          <h3 className="text-lg font-medium text-gray-600 mb-2">正在分析血缘关系...</h3>
          <p className="text-sm text-gray-400">
            正在解析SQL脚本，构建字段依赖图谱
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex-1 relative bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
        <button
          onClick={zoomIn}
          className="w-10 h-10 bg-white rounded-lg shadow-md flex items-center justify-center hover:bg-gray-50 transition-colors"
          title="放大"
        >
          <ZoomIn className="w-5 h-5 text-gray-600" />
        </button>
        <button
          onClick={zoomOut}
          className="w-10 h-10 bg-white rounded-lg shadow-md flex items-center justify-center hover:bg-gray-50 transition-colors"
          title="缩小"
        >
          <ZoomOut className="w-5 h-5 text-gray-600" />
        </button>
        <button
          onClick={centerView}
          className="w-10 h-10 bg-white rounded-lg shadow-md flex items-center justify-center hover:bg-gray-50 transition-colors"
          title="居中"
        >
          <Maximize2 className="w-5 h-5 text-gray-600" />
        </button>
        <button
          onClick={resetView}
          className="w-10 h-10 bg-white rounded-lg shadow-md flex items-center justify-center hover:bg-gray-50 transition-colors"
          title="重置"
        >
          <RotateCcw className="w-5 h-5 text-gray-600" />
        </button>
        <div className="border-t border-gray-200 my-1" />
        <button
          onClick={expandAll}
          className="w-10 h-10 bg-white rounded-lg shadow-md flex items-center justify-center hover:bg-gray-50 transition-colors"
          title="展开全部"
        >
          <Layers className="w-5 h-5 text-gray-600" />
        </button>
        <button
          onClick={collapseAll}
          className="w-10 h-10 bg-white rounded-lg shadow-md flex items-center justify-center hover:bg-gray-50 transition-colors"
          title="折叠全部"
        >
          <Minimize2 className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      <div className="absolute bottom-4 left-4 z-10 bg-white rounded-lg shadow-md p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">图例</h4>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-[#69b1ff]" />
            <span className="text-xs text-gray-600">字段</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-[#36CFC9]" />
            <span className="text-xs text-gray-600">数据表</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-[#FF7D00]" />
            <span className="text-xs text-gray-600">ETL任务</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-[#F759AB]" />
            <span className="text-xs text-gray-600">报表/看板</span>
          </div>
          <div className="border-t border-gray-200 my-2 pt-2">
            <div className="flex items-center gap-2">
              <ChevronDown className="w-4 h-4 text-gray-500" />
              <span className="text-xs text-gray-600">已展开</span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <ChevronRight className="w-4 h-4 text-gray-500" />
              <span className="text-xs text-gray-600">已折叠（右键切换）</span>
            </div>
          </div>
        </div>
      </div>

      {hoveredNode && hoveredNode.hasChildren && (
        <div className="absolute top-4 right-4 z-10 bg-white rounded-lg shadow-md p-3 text-sm">
          <p className="text-gray-600">右键点击节点可折叠/展开子节点</p>
        </div>
      )}

      <ForceGraph2D
        ref={graphRef as any}
        graphData={graphData}
        width={dimensions.width}
        height={dimensions.height}
        nodeLabel={(node: any) => {
          const isCollapsed = collapsedNodes.has(node.id);
          const childCount = node.hasChildren 
            ? visibleEdges.filter((e: LineageEdge) => e.source === node.id).length 
            : 0;
          return `${getNodeLabel(node)}${isCollapsed && childCount > 0 ? ` (+${childCount}个子节点)` : ''}`;
        }}
        nodeColor={(node: any) => {
          const isCollapsed = collapsedNodes.has(node.id);
          return getNodeColor(node.type, selectedNode?.id === node.id, isCollapsed);
        }}
        nodeVal={(node: any) => {
          const isCollapsed = collapsedNodes.has(node.id);
          return getNodeSize(node.type, isCollapsed);
        }}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const isCollapsed = collapsedNodes.has(node.id);
          const isSelected = selectedNode?.id === node.id;
          const size = getNodeSize(node.type, isCollapsed) * (globalScale > 1 ? 1 : 1 / globalScale);
          const color = getNodeColor(node.type, isSelected, isCollapsed);

          ctx.beginPath();
          ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();

          if (node.hasChildren) {
            const iconSize = size * 0.8;
            ctx.fillStyle = '#fff';
            ctx.font = `${iconSize * 1.5}px sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(isCollapsed ? '+' : '−', node.x, node.y);
          }

          if (isSelected) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
            ctx.strokeStyle = '#165DFF';
            ctx.lineWidth = 2;
            ctx.stroke();
          }

          if (node.depth !== undefined && node.depth > 0) {
            ctx.fillStyle = '#fff';
            ctx.font = `${8 / globalScale}px Inter, sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(`L${node.depth}`, node.x, node.y - size - 6);
          }

          if (globalScale >= 0.8) {
            const label = getNodeLabel(node);
            ctx.font = `${12 / globalScale}px Inter, sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#1D2129';
            ctx.fillText(label, node.x, node.y + size + 14 / globalScale);
          }
        }}
        nodeCanvasObjectMode={() => 'replace'}
        linkColor={() => '#C9CDD4'}
        linkWidth={1.5}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={3}
        linkDirectionalParticleColor={() => '#165DFF'}
        linkDirectionalParticleSpeed={0.005}
        onNodeClick={handleNodeClick}
        onNodeRightClick={handleNodeRightClick}
        onNodeHover={handleNodeHover}
        cooldownTicks={100}
        d3ForceLink={(link: any) => ({
          distance: 120,
          strength: 0.5,
        })}
        d3ForceCharge={-300}
        d3ForceCenter={(0.05 as any)}
        enableNodeDrag={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        d3ForceManyBody={(node: any) => ({
          strength: node.type === 'etl' ? -400 : -300,
        })}
      />
    </div>
  );
};
