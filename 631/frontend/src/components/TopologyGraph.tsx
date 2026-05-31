import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Network } from 'vis-network/standalone/esm/vis-network';
import { DataSet } from 'vis-data/standalone/esm/vis-data';
import type { 
  TopologyData, TopologyNode, TopologyEdge, 
  TopologyGroup, ConsumerGroupNode,
  ImpactAnalysisResult
} from '../types';

interface TopologyGraphProps {
  data: TopologyData;
  groups?: TopologyGroup[];
  consumerGroups?: ConsumerGroupNode[];
  collapsedGroups: Set<string>;
  onNodeClick: (nodeId: string) => void;
  onGroupClick: (groupId: string) => void;
  selectedNode: string | null;
  groupMode: boolean;
  impactAnalysis?: ImpactAnalysisResult | null;
  showQps?: boolean;
}

const TopologyGraph: React.FC<TopologyGraphProps> = ({ 
  data, 
  groups = [], 
  consumerGroups = [], 
  collapsedGroups, 
  onNodeClick, 
  onGroupClick, 
  selectedNode,
  groupMode,
  impactAnalysis,
  showQps = true
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; content: string; type: string } | null>(null);

  const getNodeColor = (node: TopologyNode) => {
    const baseColors: Record<string, string> = {
      'Java': '#b07219',
      'Python': '#3572A5',
      'Go': '#00ADD8',
      'Node.js': '#339933',
      'Rust': '#dea584',
      'C#': '#178600',
      'Ruby': '#701516',
      'PHP': '#4F5D95'
    };
    
    const baseColor = baseColors[node.language] || '#1890ff';
    const borderColor = node.status === 'ACTIVE' ? '#52c41a' : '#ff4d4f';
    
    return {
      background: baseColor,
      border: borderColor,
      highlight: {
        background: baseColor,
        border: '#faad14'
      },
      hover: {
        background: baseColor,
        border: '#faad14'
      }
    };
  };

  const getGroupColor = (group: TopologyGroup, collapsed: boolean) => {
    const baseColors: Record<string, string> = {
      'namespace': '#1890ff',
      'business': '#52c41a',
      'language': '#fa8c16',
      'custom': '#722ed1'
    };
    
    const baseColor = baseColors[group.groupType] || '#722ed1';
    const bgColor = collapsed ? `${baseColor}20` : `${baseColor}10`;
    const borderColor = collapsed ? baseColor : `${baseColor}60`;
    
    return {
      background: bgColor,
      border: borderColor,
      highlight: {
        background: bgColor,
        border: baseColor
      },
      hover: {
        background: `${baseColor}20`,
        border: baseColor
      }
    };
  };

  const getConsumerGroupColor = (cg: ConsumerGroupNode) => {
    const baseColor = '#722ed1';
    const bgColor = cg.status === 'ACTIVE' ? `${baseColor}15` : '#f0f0f0';
    const borderColor = cg.status === 'ACTIVE' ? baseColor : '#bfbfbf';
    
    return {
      background: bgColor,
      border: borderColor,
      highlight: {
        background: bgColor,
        border: baseColor
      },
      hover: {
        background: `${baseColor}25`,
        border: baseColor
      }
    };
  };

  const getEdgeColor = (edge: TopologyEdge) => {
    if (edge.errorCount > 0) {
      return { color: '#ff4d4f', highlight: '#ff4d4f', hover: '#ff4d4f' };
    }
    if (edge.isAsync) {
      return { color: '#fa8c16', highlight: '#fa8c16', hover: '#fa8c16' };
    }
    if (edge.messageQueue) {
      return { color: '#722ed1', highlight: '#722ed1', hover: '#722ed1' };
    }
    return { color: '#1890ff', highlight: '#1890ff', hover: '#1890ff' };
  };

  const getEdgeLabel = (edge: TopologyEdge) => {
    const parts: string[] = [];
    if (edge.protocol) parts.push(edge.protocol);
    if (edge.httpMethod) parts.push(edge.httpMethod);
    if (edge.callCount > 1) parts.push(`x${edge.callCount}`);
    if (showQps && edge.qps && edge.qps > 0) {
      parts.push(`${edge.qps.toFixed(1)} QPS`);
    }
    return parts.length > 0 ? parts.join(' ') : '';
  };

  const getNodeHighlightColor = (nodeId: string, baseColor: any) => {
    if (!impactAnalysis) return baseColor;

    const isUpstream = impactAnalysis.upstreamServices.includes(nodeId);
    const isDownstream = impactAnalysis.downstreamServices.includes(nodeId);
    const isSelected = selectedNode === nodeId;

    if (isSelected) {
      return {
        ...baseColor,
        border: '#faad14',
        background: baseColor.background,
        highlight: {
          ...baseColor.highlight,
          border: '#faad14'
        }
      };
    }

    if (isUpstream) {
      return {
        ...baseColor,
        border: '#52c41a',
        highlight: {
          ...baseColor.highlight,
          border: '#52c41a'
        }
      };
    }

    if (isDownstream) {
      return {
        ...baseColor,
        border: '#ff4d4f',
        highlight: {
          ...baseColor.highlight,
          border: '#ff4d4f'
        }
      };
    }

    return baseColor;
  };

  const getEdgeHighlightColor = (edge: TopologyEdge, baseColor: any) => {
    if (!impactAnalysis) return baseColor;

    const isUpstreamEdge = impactAnalysis.upstreamEdges.some(
      e => e.source === edge.source && e.target === edge.target
    );
    const isDownstreamEdge = impactAnalysis.downstreamEdges.some(
      e => e.source === edge.source && e.target === edge.target
    );

    if (isUpstreamEdge) {
      return { color: '#52c41a', highlight: '#52c41a', hover: '#52c41a' };
    }

    if (isDownstreamEdge) {
      return { color: '#ff4d4f', highlight: '#ff4d4f', hover: '#ff4d4f' };
    }

    return baseColor;
  };

  const buildNodeTooltip = (node: TopologyNode): string => {
    return `
      <div><strong>${node.name}</strong></div>
      <div>命名空间: ${node.namespace}</div>
      <div>类型: ${node.type || '-'}</div>
      <div>语言: ${node.language || 'Unknown'}</div>
      <div>版本: ${node.version || '-'}</div>
      <div>状态: ${node.status}</div>
      <div>IP: ${node.clusterIp || '-'}</div>
      ${node.groupName ? `<div>分组: ${node.groupName}</div>` : ''}
    `;
  };

  const buildGroupTooltip = (group: TopologyGroup, collapsed: boolean, serviceCount: number): string => {
    return `
      <div><strong>${group.name}</strong></div>
      <div>类型: ${group.groupType}</div>
      <div>命名空间: ${group.namespace}</div>
      <div>服务数量: ${serviceCount}</div>
      <div>状态: ${collapsed ? '已折叠' : '已展开'}</div>
      ${group.description ? `<div>描述: ${group.description}</div>` : ''}
      <div style="margin-top: 8px; color: #999; font-size: 12px;">点击${collapsed ? '展开' : '折叠'}分组</div>
    `;
  };

  const buildConsumerGroupTooltip = (cg: ConsumerGroupNode): string => {
    return `
      <div><strong>${cg.name}</strong></div>
      <div>消息队列: ${cg.messageQueue}</div>
      <div>Topic: ${cg.topic}</div>
      <div>命名空间: ${cg.namespace}</div>
      <div>生产者: ${cg.producerIds.length}个</div>
      <div>消费者: ${cg.consumerCount}个</div>
      <div>状态: ${cg.status}</div>
    `;
  };

  const buildEdgeTooltip = (edge: TopologyEdge): string => {
    return `
      <div><strong>${edge.source} → ${edge.target}</strong></div>
      <div>类型: ${edge.callType || '-'}</div>
      <div>协议: ${edge.protocol || '-'}</div>
      <div>异步: ${edge.isAsync ? '是' : '否'}</div>
      ${edge.messageQueue ? `<div>消息队列: ${edge.messageQueue}</div>` : ''}
      ${edge.messageTopic ? `<div>Topic: ${edge.messageTopic}</div>` : ''}
      ${edge.consumerGroup ? `<div>消费组: ${edge.consumerGroup}</div>` : ''}
      ${edge.path ? `<div>路径: ${edge.path}</div>` : ''}
      ${edge.traceId ? `<div>TraceId: ${edge.traceId}</div>` : ''}
      <div>调用次数: ${edge.callCount}</div>
      <div>错误次数: ${edge.errorCount}</div>
      <div>平均延迟: ${edge.avgLatencyMs.toFixed(2)}ms</div>
    `;
  };

  const { visibleNodes, visibleEdges, nodeMap, groupMap, consumerGroupMap } = useMemo(() => {
    const nodeMap = new Map<string, TopologyNode>();
    const groupMap = new Map<string, TopologyGroup>();
    const consumerGroupMap = new Map<string, ConsumerGroupNode>();
    
    data.nodes.forEach(node => nodeMap.set(node.id, node));
    groups.forEach(group => groupMap.set(group.id, group));
    consumerGroups.forEach(cg => consumerGroupMap.set(cg.id, cg));

    if (!groupMode || groups.length === 0) {
      return { 
        visibleNodes: data.nodes, 
        visibleEdges: data.edges,
        nodeMap,
        groupMap,
        consumerGroupMap
      };
    }

    const hiddenServiceIds = new Set<string>();
    groups.forEach(group => {
      if (collapsedGroups.has(group.id)) {
        group.serviceIds.forEach(id => hiddenServiceIds.add(id));
      }
    });

    const visibleNodes = data.nodes.filter(node => !hiddenServiceIds.has(node.id));

    const groupEdgeAggregator = new Map<string, { 
      source: string; 
      target: string; 
      callCount: number; 
      errorCount: number;
      avgLatencyMs: number;
      protocols: Set<string>;
    }>();

    const serviceToGroupId = new Map<string, string>();
    groups.forEach(group => {
      group.serviceIds.forEach(sid => serviceToGroupId.set(sid, group.id));
    });

    data.edges.forEach((edge, idx) => {
      const sourceGroupId = serviceToGroupId.get(edge.source);
      const targetGroupId = serviceToGroupId.get(edge.target);
      
      const sourceHidden = sourceGroupId && collapsedGroups.has(sourceGroupId);
      const targetHidden = targetGroupId && collapsedGroups.has(targetGroupId);
      
      if (sourceHidden || targetHidden) {
        const newSource = sourceHidden ? `group-${sourceGroupId}` : edge.source;
        const newTarget = targetHidden ? `group-${targetGroupId}` : edge.target;
        const edgeKey = `${newSource}->${newTarget}`;
        
        const existing = groupEdgeAggregator.get(edgeKey);
        if (existing) {
          existing.callCount += edge.callCount;
          existing.errorCount += edge.errorCount;
          existing.avgLatencyMs = (existing.avgLatencyMs + edge.avgLatencyMs) / 2;
          if (edge.protocol) existing.protocols.add(edge.protocol);
        } else {
          groupEdgeAggregator.set(edgeKey, {
            source: newSource,
            target: newTarget,
            callCount: edge.callCount,
            errorCount: edge.errorCount,
            avgLatencyMs: edge.avgLatencyMs,
            protocols: edge.protocol ? new Set([edge.protocol]) : new Set()
          });
        }
      }
    });

    const visibleEdges = data.edges.filter(edge => {
      const sourceGroupId = serviceToGroupId.get(edge.source);
      const targetGroupId = serviceToGroupId.get(edge.target);
      const sourceHidden = sourceGroupId && collapsedGroups.has(sourceGroupId);
      const targetHidden = targetGroupId && collapsedGroups.has(targetGroupId);
      return !sourceHidden && !targetHidden;
    });

    groupEdgeAggregator.forEach((agg, key) => {
      const [source, target] = key.split('->');
      visibleEdges.push({
        source,
        target,
        callType: 'AGGREGATED',
        protocol: Array.from(agg.protocols).join('/') || '',
        isAsync: false,
        messageQueue: '',
        httpMethod: '',
        path: '',
        callCount: agg.callCount,
        errorCount: agg.errorCount,
        successCount: agg.callCount - agg.errorCount,
        avgLatencyMs: agg.avgLatencyMs,
        lastSeen: new Date().toISOString()
      });
    });

    return { visibleNodes, visibleEdges, nodeMap, groupMap, consumerGroupMap };
  }, [data, groups, consumerGroups, collapsedGroups, groupMode]);

  useEffect(() => {
    if (!containerRef.current) return;

    const visNodes: any[] = [];
    const visEdges: any[] = [];

    if (groupMode && groups.length > 0) {
      groups.forEach(group => {
        const collapsed = collapsedGroups.has(group.id);
        const color = getGroupColor(group, collapsed);
        
        visNodes.push({
          id: `group-${group.id}`,
          label: `${group.name}\n(${group.serviceCount}个服务)`,
          title: buildGroupTooltip(group, collapsed, group.serviceCount),
          color: color,
          shape: 'box',
          size: 40,
          font: { 
            color: '#333', 
            size: 14,
            multi: false,
            bold: '14px arial #333'
          },
          borderWidth: collapsed ? 3 : 2,
          shadow: true,
          isGroup: true,
          groupId: group.id,
          collapsed: collapsed,
          level: 0
        });
      });
    }

    if (consumerGroups.length > 0) {
      consumerGroups.forEach(cg => {
        const color = getConsumerGroupColor(cg);
        
        visNodes.push({
          id: `cg-${cg.id}`,
          label: `${cg.name}\n(CG: ${cg.consumerCount}消费者)`,
          title: buildConsumerGroupTooltip(cg),
          color: color,
          shape: 'diamond',
          size: 35,
          font: { 
            color: '#722ed1', 
            size: 12,
            multi: false
          },
          borderWidth: 2,
          shadow: true,
          isConsumerGroup: true,
          consumerGroupId: cg.id,
          level: 0
        });

        cg.producerIds.forEach(pid => {
          if (nodeMap.has(pid) || groupMap.has(pid)) {
            visEdges.push({
              id: `prod-cg-${cg.id}-${pid}`,
              from: groupMode && collapsedGroups.has(pid) ? `group-${pid}` : pid,
              to: `cg-${cg.id}`,
              label: '生产',
              color: { color: '#722ed1', highlight: '#722ed1', hover: '#722ed1' },
              width: 2,
              arrows: { to: { enabled: true, scaleFactor: 0.6 } },
              font: { size: 10, align: 'middle', color: '#722ed1' },
              smooth: { type: 'continuous' },
              dashes: false
            });
          }
        });

        cg.consumerIds.forEach(cid => {
          if (nodeMap.has(cid) || groupMap.has(cid)) {
            visEdges.push({
              id: `cg-cons-${cg.id}-${cid}`,
              from: `cg-${cg.id}`,
              to: groupMode && collapsedGroups.has(cid) ? `group-${cid}` : cid,
              label: '消费',
              color: { color: '#13c2c2', highlight: '#13c2c2', hover: '#13c2c2' },
              width: 2,
              arrows: { to: { enabled: true, scaleFactor: 0.6 } },
              font: { size: 10, align: 'middle', color: '#13c2c2' },
              smooth: { type: 'continuous' },
              dashes: [5, 5]
            });
          }
        });
      });
    }

    visibleNodes.forEach(node => {
      const baseColor = getNodeColor(node);
      const finalColor = getNodeHighlightColor(node.id, baseColor);
      const isHighlighted = impactAnalysis && (
        impactAnalysis.upstreamServices.includes(node.id) ||
        impactAnalysis.downstreamServices.includes(node.id) ||
        selectedNode === node.id
      );

      visNodes.push({
        id: node.id,
        label: node.name,
        title: buildNodeTooltip(node),
        color: finalColor,
        shape: 'dot',
        size: isHighlighted ? 30 : 25,
        font: { color: '#333', size: 14 },
        borderWidth: isHighlighted ? 4 : 3,
        shadow: true,
        groupId: node.groupId,
        level: 1
      });
    });

    visibleEdges.forEach((edge, idx) => {
      const baseColor = getEdgeColor(edge);
      const finalColor = getEdgeHighlightColor(edge, baseColor);
      const isHighlighted = impactAnalysis && (
        impactAnalysis.upstreamEdges.some(e => e.source === edge.source && e.target === edge.target) ||
        impactAnalysis.downstreamEdges.some(e => e.source === edge.source && e.target === edge.target)
      );

      visEdges.push({
        id: `edge-${idx}-${Date.now()}`,
        from: edge.source,
        to: edge.target,
        label: getEdgeLabel(edge),
        title: buildEdgeTooltip(edge),
        color: finalColor,
        width: isHighlighted ? 4 : Math.min(Math.max(edge.callCount / 10, 1), 5),
        arrows: { to: { enabled: true, scaleFactor: isHighlighted ? 1.0 : 0.8 } },
        font: { size: 10, align: 'middle' },
        smooth: { type: 'continuous' },
        dashes: edge.isAsync
      });
    });

    const nodes = new DataSet<any>(visNodes);
    const edges = new DataSet<any>(visEdges);

    const networkData = { nodes, edges };
    const options = {
      nodes: {
        shape: 'dot',
        size: 20,
        borderWidth: 2,
        shadow: true
      },
      edges: {
        width: 2,
        shadow: true,
        smooth: {
          type: 'continuous'
        }
      },
      layout: {
        hierarchical: {
          enabled: groupMode && groups.length > 0,
          levelSeparation: 200,
          nodeSpacing: 150,
          treeSpacing: 200,
          blockShifting: true,
          edgeMinimization: true,
          parentCentralization: true,
          direction: 'UD',
          sortMethod: 'directed'
        }
      },
      physics: {
        enabled: !(groupMode && groups.length > 0),
        barnesHut: {
          gravitationalConstant: -3000,
          centralGravity: 0.3,
          springLength: 150,
          springConstant: 0.04
        },
        stabilization: {
          iterations: 100
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        hideEdgesOnDrag: true,
        hideEdgesOnZoom: false
      }
    };

    if (networkRef.current) {
      networkRef.current.setData(networkData);
      networkRef.current.setOptions(options);
    } else {
      networkRef.current = new Network(containerRef.current, networkData, options);

      networkRef.current.on('click', (params: any) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          
          if (nodeId.startsWith('group-')) {
            const groupId = nodeId.replace('group-', '');
            onGroupClick(groupId);
          } else if (nodeId.startsWith('cg-')) {
            return;
          } else {
            onNodeClick(nodeId);
          }
        }
      });

      networkRef.current.on('doubleClick', (params: any) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          if (nodeId.startsWith('group-')) {
            const groupId = nodeId.replace('group-', '');
            onGroupClick(groupId);
          }
        }
      });

      networkRef.current.on('hoverNode', (params: any) => {
        const nodeId = params.node;
        let content = '';
        let type = 'node';
        
        if (nodeId.startsWith('group-')) {
          const groupId = nodeId.replace('group-', '');
          const group = groupMap.get(groupId);
          if (group) {
            const collapsed = collapsedGroups.has(groupId);
            content = buildGroupTooltip(group, collapsed, group.serviceCount);
            type = 'group';
          }
        } else if (nodeId.startsWith('cg-')) {
          const cgId = nodeId.replace('cg-', '');
          const cg = consumerGroupMap.get(cgId);
          if (cg) {
            content = buildConsumerGroupTooltip(cg);
            type = 'consumerGroup';
          }
        } else {
          const node = nodeMap.get(nodeId);
          if (node) {
            content = buildNodeTooltip(node);
          }
        }
        
        if (content && params.event) {
          const rect = containerRef.current?.getBoundingClientRect();
          if (rect) {
            setTooltip({
              x: params.event.srcEvent.clientX - rect.left,
              y: params.event.srcEvent.clientY - rect.top + 10,
              content,
              type
            });
          }
        }
      });

      networkRef.current.on('blurNode', () => {
        setTooltip(null);
      });

      networkRef.current.on('hoverEdge', (params: any) => {
        const edgeId = params.edge;
        const edgeIdx = parseInt(edgeId.split('-')[1]);
        const edge = visibleEdges[edgeIdx];
        
        if (edge && params.event) {
          const rect = containerRef.current?.getBoundingClientRect();
          if (rect) {
            setTooltip({
              x: params.event.srcEvent.clientX - rect.left,
              y: params.event.srcEvent.clientY - rect.top + 10,
              content: buildEdgeTooltip(edge),
              type: 'edge'
            });
          }
        }
      });

      networkRef.current.on('blurEdge', () => {
        setTooltip(null);
      });
    }

    if (selectedNode && networkRef.current) {
      try {
        networkRef.current.selectNodes([selectedNode]);
        networkRef.current.focus(selectedNode, { scale: 1.5, animation: true });
      } catch (e) {
        console.log('Node not found in graph:', selectedNode);
      }
    }
  }, [visibleNodes, visibleEdges, groups, consumerGroups, collapsedGroups, selectedNode, groupMode]);

  return (
    <>
      <div ref={containerRef} id="topology-network" />
      {tooltip && (
        <div
          className={tooltip.type === 'edge' ? 'edge-tooltip' : 'node-tooltip'}
          style={{ left: tooltip.x, top: tooltip.y }}
          dangerouslySetInnerHTML={{ __html: tooltip.content }}
        />
      )}
    </>
  );
};

export default TopologyGraph;
