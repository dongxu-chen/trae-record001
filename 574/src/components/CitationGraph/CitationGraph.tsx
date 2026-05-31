import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import * as d3 from 'd3';
import { ChevronRight, ChevronDown, Loader2, Maximize2, Layers, ZoomIn, ZoomOut, RefreshCw } from 'lucide-react';
import { api } from '@/services/api';
import { useAppStore } from '@/store';
import type { GraphNode, GraphEdge, HierarchicalGraphData, HierarchicalCommunity } from '@/types';

interface CitationGraphProps {
  graphData: HierarchicalGraphData;
  height?: number;
}

interface ClusterNode {
  id: string;
  type: 'cluster';
  level: number;
  cluster_id: number;
  community: HierarchicalCommunity;
  is_expanded: boolean;
  x?: number;
  y?: number;
}

type DisplayNode = GraphNode | ClusterNode;

const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6',
  '#f43f5e', '#06b6d4', '#84cc16', '#f97316',
  '#6366f1', '#ec4899', '#14b8a6', '#a855f7'
];

export function CitationGraph({ graphData, height = 600 }: CitationGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [expandingCluster, setExpandingCluster] = useState<string | null>(null);
  const {
    expandedCommunities,
    toggleCommunityExpanded,
    currentLevel,
    setCurrentLevel,
    selectedNode,
    setSelectedNode,
    highlightedNodes,
    setHighlightedNodes,
  } = useAppStore();

  const displayData = useMemo(() => {
    if (!graphData.hierarchy) {
      return {
        nodes: graphData.nodes,
        edges: graphData.edges,
      };
    }

    const hierarchy = graphData.hierarchy;
    const communities = hierarchy.communities[currentLevel] || {};
    const nodeCommunityMap = hierarchy.node_community_map;

    const visibleNodes: DisplayNode[] = [];
    const visibleEdges: GraphEdge[] = [];
    const addedEdges = new Set<string>();

    const expandedClusters = new Set<string>();
    expandedCommunities.forEach((key) => {
      const [lvl, cid] = key.split('-').map(Number);
      if (lvl === currentLevel) {
        expandedClusters.add(cid.toString());
      }
    });

    const expandedNodes = new Set<string>();
    for (const [clusterId, community] of Object.entries(communities)) {
      const clusterKey = `${currentLevel}-${clusterId}`;
      const isExpanded = expandedCommunities.has(clusterKey);

      if (isExpanded) {
        for (const nodeId of community.nodes) {
          if (!expandedNodes.has(nodeId)) {
            const node = graphData.nodes.find((n) => n.id === nodeId);
            if (node) {
              visibleNodes.push(node);
              expandedNodes.add(nodeId);
            }
          }
        }
      } else {
        visibleNodes.push({
          id: `cluster-${currentLevel}-${clusterId}`,
          type: 'cluster',
          level: currentLevel,
          cluster_id: Number(clusterId),
          community: community,
          is_expanded: false,
        });
      }
    }

    for (const edge of graphData.edges) {
      const sourceInExpanded = expandedNodes.has(edge.source);
      const targetInExpanded = expandedNodes.has(edge.target);

      if (sourceInExpanded && targetInExpanded) {
        const edgeKey = `${edge.source}-${edge.target}`;
        if (!addedEdges.has(edgeKey)) {
          visibleEdges.push(edge);
          addedEdges.add(edgeKey);
        }
      } else {
        const sourceCluster = nodeCommunityMap[edge.source]?.[currentLevel];
        const targetCluster = nodeCommunityMap[edge.target]?.[currentLevel];

        if (sourceCluster !== undefined && targetCluster !== undefined && sourceCluster !== targetCluster) {
          const sourceExpanded = expandedCommunities.has(`${currentLevel}-${sourceCluster}`);
          const targetExpanded = expandedCommunities.has(`${currentLevel}-${targetCluster}`);

          if (!sourceExpanded && !targetExpanded) {
            const clusterEdgeKey = `cluster-${currentLevel}-${sourceCluster}-cluster-${currentLevel}-${targetCluster}`;
            const reverseKey = `cluster-${currentLevel}-${targetCluster}-cluster-${currentLevel}-${sourceCluster}`;
            
            if (!addedEdges.has(clusterEdgeKey) && !addedEdges.has(reverseKey)) {
              visibleEdges.push({
                source: `cluster-${currentLevel}-${sourceCluster}`,
                target: `cluster-${currentLevel}-${targetCluster}`,
                value: 1,
              });
              addedEdges.add(clusterEdgeKey);
            }
          }
        }
      }
    }

    return {
      nodes: visibleNodes,
      edges: visibleEdges,
    };
  }, [graphData, currentLevel, expandedCommunities]);

  const handleClusterClick = useCallback(async (clusterId: string, level: number, cid: number) => {
    setExpandingCluster(clusterId);
    setLoading(true);

    try {
      const response = await api.getClusterPapers(level, cid, 20);
      if (response.success) {
        toggleCommunityExpanded(level, cid);
      }
    } catch (error) {
      console.error('Failed to expand cluster:', error);
    } finally {
      setLoading(false);
      setExpandingCluster(null);
    }
  }, [toggleCommunityExpanded]);

  const handleNodeHover = useCallback((nodeId: string | null) => {
    if (!nodeId) {
      setHighlightedNodes(new Set());
      return;
    }

    const connected = new Set<string>([nodeId]);
    displayData.edges.forEach((edge) => {
      if (edge.source === nodeId) {
        connected.add(edge.target);
      }
      if (edge.target === nodeId) {
        connected.add(edge.source);
      }
    });
    setHighlightedNodes(connected);
  }, [displayData.edges, setHighlightedNodes]);

  useEffect(() => {
    if (!svgRef.current || displayData.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    const width = containerRef.current?.clientWidth || 800;
    const height = height;

    svg.selectAll('*').remove();

    const g = svg.append('g');
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    const simulation = d3.forceSimulation<DisplayNode>(displayData.nodes as any)
      .force('link', d3.forceLink<DisplayNode, GraphEdge>(displayData.edges as any)
        .id((d: any) => d.id)
        .distance((d: any) => {
          const isClusterEdge = d.source.startsWith?.('cluster-') || d.target.startsWith?.('cluster-');
          return isClusterEdge ? 200 : 100;
        })
        .strength(0.5))
      .force('charge', d3.forceManyBody().strength((d: any) => {
        const isCluster = d.type === 'cluster';
        return isCluster ? -500 : -200;
      }))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius((d: any) => {
        const isCluster = d.type === 'cluster';
        return isCluster ? 60 : 25;
      }));

    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(displayData.edges)
      .enter()
      .append('line')
      .attr('stroke', '#4a5568')
      .attr('stroke-opacity', 0.4)
      .attr('stroke-width', (d: any) => Math.sqrt(d.value) || 1);

    const node = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(displayData.nodes)
      .enter()
      .append('g')
      .attr('cursor', 'pointer')
      .call(d3.drag<SVGGElement, DisplayNode>()
        .on('start', (event: any, d: any) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event: any, d: any) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event: any, d: any) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }));

    node.each(function(d: any) {
      const nodeSel = d3.select(this);
      const isCluster = d.type === 'cluster';
      const isHighlighted = highlightedNodes.size === 0 || highlightedNodes.has(d.id);

      if (isCluster) {
        const color = COLORS[d.cluster_id % COLORS.length];
        const size = 40 + Math.min(d.community.size * 2, 40);

        nodeSel.append('circle')
          .attr('r', size)
          .attr('fill', color)
          .attr('fill-opacity', 0.3)
          .attr('stroke', color)
          .attr('stroke-width', 3)
          .attr('opacity', isHighlighted ? 1 : 0.3);

        nodeSel.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', '0.35em')
          .attr('fill', 'white')
          .attr('font-size', '12px')
          .attr('font-weight', 'bold')
          .text(d.community.name || `C${d.cluster_id}`)
          .attr('opacity', isHighlighted ? 1 : 0.3);

        nodeSel.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', '2em')
          .attr('fill', '#a0aec0')
          .attr('font-size', '10px')
          .text(`${d.community.size} 篇论文`)
          .attr('opacity', isHighlighted ? 1 : 0.3);

        const isExpanding = expandingCluster === d.id;
        nodeSel.append('g')
          .attr('transform', `translate(${size - 10}, ${-size + 10})`)
          .append('circle')
          .attr('r', 12)
          .attr('fill', '#1a202c')
          .attr('stroke', color);

        nodeSel.append('g')
          .attr('transform', `translate(${size - 10}, ${-size + 10})`)
          .append(() => 
            isExpanding 
              ? (Loader2 as any).default({ className: 'w-4 h-4', style: { fill: color } })
              : (d.is_expanded 
                ? (ChevronDown as any).default({ className: 'w-4 h-4', style: { fill: color } })
                : (ChevronRight as any).default({ className: 'w-4 h-4', style: { fill: color } }))
          );
      } else {
        const color = COLORS[d.group % COLORS.length];
        const size = Math.max(6, Math.min(20, d.pagerank * 2000 + 8));

        nodeSel.append('circle')
          .attr('r', size)
          .attr('fill', color)
          .attr('stroke', selectedNode?.id === d.id ? '#fff' : color)
          .attr('stroke-width', selectedNode?.id === d.id ? 3 : 1)
          .attr('opacity', isHighlighted ? 1 : 0.3);

        if (d.h_index > 50) {
          nodeSel.append('circle')
            .attr('r', size + 3)
            .attr('fill', 'none')
            .attr('stroke', '#fbbf24')
            .attr('stroke-width', 2)
            .attr('stroke-dasharray', '3,3')
            .attr('opacity', isHighlighted ? 1 : 0.3);
        }
      }
    });

    node.on('click', (event, d: any) => {
      event.stopPropagation();
      if (d.type === 'cluster') {
        handleClusterClick(d.id, d.level, d.cluster_id);
      } else {
        setSelectedNode(d);
      }
    })
    .on('mouseenter', (event, d: any) => {
      handleNodeHover(d.id);
    })
    .on('mouseleave', () => {
      handleNodeHover(null);
    });

    const labels = g.append('g')
      .attr('class', 'labels')
      .selectAll('text')
      .data(displayData.nodes.filter((d: any) => d.type !== 'cluster'))
      .enter()
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', (d: any) => -Math.max(6, Math.min(20, d.pagerank * 2000 + 8)) - 5)
      .attr('fill', 'white')
      .attr('font-size', '10px')
      .attr('opacity', 0)
      .text((d: any) => d.label || d.title?.substring(0, 20));

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);

      labels
        .attr('x', (d: any) => d.x)
        .attr('y', (d: any) => d.y);

      const transform = d3.zoomTransform(svgRef.current!);
      if (transform.k > 1.2) {
        labels.attr('opacity', 1);
      } else {
        labels.attr('opacity', 0);
      }
    });

    svg.on('click', () => {
      setSelectedNode(null);
    });

    return () => {
      simulation.stop();
    };
  }, [displayData, selectedNode, highlightedNodes, expandingCluster, handleClusterClick, handleNodeHover, setSelectedNode]);

  return (
    <div className="relative w-full">
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
        <div className="glass rounded-lg p-2 flex flex-col gap-1">
          <div className="text-xs text-dark-400 mb-1 px-2">粒度层级</div>
          {graphData.hierarchy?.levels.map((level) => (
            <button
              key={level}
              onClick={() => setCurrentLevel(level)}
              className={`px-3 py-1.5 rounded-md text-sm transition-all ${
                currentLevel === level
                  ? 'bg-accent-blue text-white'
                  : 'text-dark-300 hover:bg-dark-700'
              }`}
            >
              层级 {level}
            </button>
          ))}
        </div>
      </div>

      <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
        <div className="glass rounded-lg p-2 flex flex-col gap-1">
          <button
            onClick={() => {
              const svg = d3.select(svgRef.current!);
              svg.transition().duration(300).call(d3.zoom().scaleBy as any, 1.3);
            }}
            className="p-2 rounded-md text-dark-300 hover:bg-dark-700 hover:text-white transition-all"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              const svg = d3.select(svgRef.current!);
              svg.transition().duration(300).call(d3.zoom().scaleBy as any, 0.7);
            }}
            className="p-2 rounded-md text-dark-300 hover:bg-dark-700 hover:text-white transition-all"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              const svg = d3.select(svgRef.current!);
              svg.transition().duration(300).call(d3.zoom().transform as any, d3.zoomIdentity);
            }}
            className="p-2 rounded-md text-dark-300 hover:bg-dark-700 hover:text-white transition-all"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div ref={containerRef} className="w-full bg-dark-900 rounded-xl overflow-hidden">
        <svg
          ref={svgRef}
          width="100%"
          height={height}
          className="cursor-grab active:cursor-grabbing"
        />
      </div>

      {graphData.hierarchy && (
        <div className="absolute bottom-4 left-4 z-10 glass rounded-lg p-3 max-w-xs">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-accent-blue" />
            <span className="text-sm font-medium text-white">聚类图例</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {Object.entries(graphData.hierarchy.communities[currentLevel] || {}).map(([cid, comm]) => (
              <div key={cid} className="flex items-center gap-1 text-xs">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: COLORS[Number(cid) % COLORS.length] }}
                />
                <span className="text-dark-300">{comm.name || `C${cid}`}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="absolute inset-0 bg-dark-900/50 flex items-center justify-center z-20">
          <div className="glass rounded-xl p-6 flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-accent-blue animate-spin" />
            <p className="text-white">正在加载子图...</p>
          </div>
        </div>
      )}
    </div>
  );
}
