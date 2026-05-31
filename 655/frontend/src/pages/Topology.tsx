import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import {
  Card, Select, Button, Space, Spin, message, Descriptions,
  Drawer, Tag, Tooltip, Radio, Badge, Popover, List, Divider
} from 'antd';
import {
  ReloadOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  FullscreenOutlined,
  ApisOutlined,
  UnorderedListOutlined,
  MinusCircleOutlined,
  PlusCircleOutlined,
} from '@ant-design/icons';
import { topologyAPI } from '../services/api';
import type { TrafficTopology, ServiceNode, ServiceEdge } from '../types';

const { Option } = Select;
const { Group, Button: RadioButton } = Radio;

const TOPOLOGY_COLORS: Record<string, string> = {
  service: '#1890ff',
  gateway: '#fa8c16',
  virtualservice: '#722ed1',
  workload: '#52c41a',
};

type LayoutMode = 'sugiyama' | 'force' | 'circular';

const Topology: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [namespace, setNamespace] = useState('default');
  const [topology, setTopology] = useState<TrafficTopology | null>(null);
  const [selectedNode, setSelectedNode] = useState<ServiceNode | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('sugiyama');
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());
  const [showCollapsedPanel, setShowCollapsedPanel] = useState(false);
  const [layoutTime, setLayoutTime] = useState(0);

  const nodePositions = useRef<Map<string, { x: number; y: number }>>(new Map());

  useEffect(() => {
    fetchTopology();
  }, [namespace]);

  useEffect(() => {
    if (topology) {
      const startTime = performance.now();
      layoutNodes();
      const endTime = performance.now();
      setLayoutTime(Math.round(endTime - startTime));
      drawTopology();
    }
  }, [topology, scale, offset, layoutMode, collapsedNodes]);

  const fetchTopology = async () => {
    setLoading(true);
    try {
      const res = await topologyAPI.getTopology(namespace);
      const data = res.data;
      if (data.nodes && data.nodes.length > 0) {
        setTopology(data);
        message.success(`拓扑数据已加载 (${data.nodes.length} 节点, ${data.edges.length} 边)`);
      } else {
        setTopology(generateLargeDemoTopology());
        message.info('已加载演示拓扑数据 (150节点)');
      }
    } catch {
      setTopology(generateLargeDemoTopology());
      message.info('已加载演示拓扑数据 (150节点)');
    } finally {
      setLoading(false);
    }
  };

  const generateDemoTopology = (): TrafficTopology => {
    const nodes: ServiceNode[] = [
      { id: 'gateway', name: 'istio-gateway', namespace: 'default', type: 'gateway', version: 'v1' },
      { id: 'frontend-v1', name: 'frontend', namespace: 'default', type: 'service', version: 'v1' },
      { id: 'frontend-v2', name: 'frontend', namespace: 'default', type: 'service', version: 'v2' },
      { id: 'user-service', name: 'user-service', namespace: 'default', type: 'service', version: 'v1' },
      { id: 'order-service', name: 'order-service', namespace: 'default', type: 'service', version: 'v1' },
      { id: 'payment-service', name: 'payment-service', namespace: 'default', type: 'service', version: 'v1' },
      { id: 'product-service', name: 'product-service', namespace: 'default', type: 'workload', version: 'v1' },
      { id: 'inventory-service', name: 'inventory-service', namespace: 'default', type: 'workload', version: 'v1' },
    ];

    const edges: ServiceEdge[] = [
      { id: 'e1', source: 'gateway', target: 'frontend-v1', protocol: 'HTTP', traffic: 75, latency: 12, errorRate: 0.5, requestCount: 12500 },
      { id: 'e2', source: 'gateway', target: 'frontend-v2', protocol: 'HTTP', traffic: 25, latency: 15, errorRate: 0.2, requestCount: 4200 },
      { id: 'e3', source: 'frontend-v1', target: 'user-service', protocol: 'gRPC', traffic: 40, latency: 8, errorRate: 0.1, requestCount: 5000 },
      { id: 'e4', source: 'frontend-v1', target: 'order-service', protocol: 'HTTP', traffic: 35, latency: 22, errorRate: 1.2, requestCount: 4400 },
      { id: 'e5', source: 'frontend-v2', target: 'order-service', protocol: 'HTTP', traffic: 25, latency: 18, errorRate: 0.8, requestCount: 3000 },
      { id: 'e6', source: 'order-service', target: 'payment-service', protocol: 'gRPC', traffic: 60, latency: 45, errorRate: 0.3, requestCount: 7400 },
      { id: 'e7', source: 'order-service', target: 'product-service', protocol: 'HTTP', traffic: 30, latency: 15, errorRate: 0.1, requestCount: 3700 },
      { id: 'e8', source: 'order-service', target: 'inventory-service', protocol: 'gRPC', traffic: 28, latency: 20, errorRate: 0.5, requestCount: 3500 },
      { id: 'e9', source: 'user-service', target: 'product-service', protocol: 'HTTP', traffic: 20, latency: 10, errorRate: 0.2, requestCount: 2500 },
    ];

    return { nodes, edges };
  };

  const generateLargeDemoTopology = (): TrafficTopology => {
    const layers = 5;
    const nodesPerLayer = 30;
    const nodes: ServiceNode[] = [];
    const edges: ServiceEdge[] = [];
    let nodeId = 0;
    let edgeId = 0;

    const typeList = ['gateway', 'service', 'service', 'service', 'workload'];
    const serviceNames = ['api-gateway', 'auth', 'frontend', 'user', 'order', 'payment', 'product', 'inventory', 'notification', 'analytics'];

    for (let layer = 0; layer < layers; layer++) {
      for (let i = 0; i < nodesPerLayer; i++) {
        const serviceName = serviceNames[nodeId % serviceNames.length];
        nodes.push({
          id: `node-${nodeId}`,
          name: `${serviceName}-${layer}-${i}`,
          namespace: 'default',
          type: typeList[layer % typeList.length],
          version: `v${(nodeId % 3) + 1}`,
        });
        nodeId++;
      }
    }

    for (let layer = 0; layer < layers - 1; layer++) {
      for (let i = 0; i < nodesPerLayer; i++) {
        const sourceIdx = layer * nodesPerLayer + i;
        const connections = Math.min(3 + Math.floor(Math.random() * 3), nodesPerLayer);
        for (let c = 0; c < connections; c++) {
          const targetOffset = Math.floor(Math.random() * nodesPerLayer);
          const targetIdx = (layer + 1) * nodesPerLayer + targetOffset;
          edges.push({
            id: `e-${edgeId}`,
            source: `node-${sourceIdx}`,
            target: `node-${targetIdx}`,
            protocol: Math.random() > 0.5 ? 'HTTP' : 'gRPC',
            traffic: Math.floor(Math.random() * 100),
            latency: Math.floor(Math.random() * 50) + 5,
            errorRate: Math.random() * 2,
            requestCount: Math.floor(Math.random() * 10000),
          });
          edgeId++;
        }
      }
    }

    return { nodes, edges };
  };

  const sugiyamaLayout = useCallback((nodes: ServiceNode[], edges: ServiceEdge[]) => {
    const positions = new Map<string, { x: number; y: number }>();
    const nodeMap = new Map(nodes.map(n => [n.id, n]));

    const inDegree = new Map<string, number>();
    const outEdges = new Map<string, string[]>();

    nodes.forEach(n => {
      inDegree.set(n.id, 0);
      outEdges.set(n.id, []);
    });

    edges.forEach(e => {
      inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
      outEdges.get(e.source)?.push(e.target);
    });

    const layers: string[][] = [];
    const layerAssignment = new Map<string, number>();
    const queue: string[] = [];
    const tempInDegree = new Map(inDegree);

    nodes.forEach(n => {
      if (tempInDegree.get(n.id) === 0) {
        queue.push(n.id);
      }
    });

    const processed = new Set<string>();
    while (queue.length > 0 || processed.size < nodes.length) {
      const currentLayer: string[] = [];

      if (queue.length === 0) {
        for (const n of nodes) {
          if (!processed.has(n.id)) {
            queue.push(n.id);
            tempInDegree.set(n.id, 0);
            break;
          }
        }
      }

      const levelSize = queue.length;
      for (let i = 0; i < levelSize; i++) {
        const id = queue[i];
        if (processed.has(id)) continue;
        currentLayer.push(id);
        processed.add(id);
        layerAssignment.set(id, layers.length);
      }

      for (let i = 0; i < levelSize; i++) {
        const id = queue.shift()!;
        outEdges.get(id)?.forEach(target => {
          const newDeg = (tempInDegree.get(target) || 0) - 1;
          tempInDegree.set(target, newDeg);
          if (newDeg <= 0 && !processed.has(target) && !queue.includes(target)) {
            queue.push(target);
          }
        });
      }

      if (currentLayer.length > 0) {
        layers.push(currentLayer);
      }
    }

    const layerGap = 120;
    const nodeGap = 65;
    const layerWidths = layers.map(layer => layer.length * (50 + nodeGap) - nodeGap);
    const maxWidth = Math.max(...layerWidths);

    layers.forEach((layer, layerIdx) => {
      const layerWidth = layer.length * (50 + nodeGap) - nodeGap;
      const startX = (maxWidth - layerWidth) / 2 + 50;

      layer.forEach((id, nodeIdx) => {
        positions.set(id, {
          x: startX + nodeIdx * (50 + nodeGap) + 25,
          y: layerIdx * layerGap + 80,
        });
      });
    });

    return positions;
  }, []);

  const forceDirectedLayout = useCallback((nodes: ServiceNode[], edges: ServiceEdge[]) => {
    const positions = new Map<string, { x: number; y: number }>();
    const velocities = new Map<string, { x: number; y: number }>();

    const width = 800;
    const height = 600;
    const iterations = 50;
    const repulsion = 5000;
    const attraction = 0.01;

    nodes.forEach((n, i) => {
      positions.set(n.id, {
        x: Math.random() * width * 0.8 + width * 0.1,
        y: Math.random() * height * 0.8 + height * 0.1,
      });
      velocities.set(n.id, { x: 0, y: 0 });
    });

    for (let iter = 0; iter < iterations; iter++) {
      nodes.forEach(n1 => {
        const p1 = positions.get(n1.id)!;
        nodes.forEach(n2 => {
          if (n1.id >= n2.id) return;
          const p2 = positions.get(n2.id)!;
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = repulsion / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          velocities.get(n1.id)!.x += fx;
          velocities.get(n1.id)!.y += fy;
          velocities.get(n2.id)!.x -= fx;
          velocities.get(n2.id)!.y -= fy;
        });
      });

      edges.forEach(e => {
        const src = positions.get(e.source);
        const tgt = positions.get(e.target);
        if (!src || !tgt) return;
        const dx = tgt.x - src.x;
        const dy = tgt.y - src.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = dist * attraction;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        velocities.get(e.source)!.x += fx;
        velocities.get(e.source)!.y += fy;
        velocities.get(e.target)!.x -= fx;
        velocities.get(e.target)!.y -= fy;
      });

      nodes.forEach(n => {
        const v = velocities.get(n.id)!;
        const p = positions.get(n.id)!;

        v.x *= 0.9;
        v.y *= 0.9;

        p.x += v.x;
        p.y += v.y;

        p.x = Math.max(50, Math.min(width - 50, p.x));
        p.y = Math.max(50, Math.min(height - 50, p.y));
      });
    }

    return positions;
  }, []);

  const circularLayout = useCallback((nodes: ServiceNode[], edges: ServiceEdge[]) => {
    const positions = new Map<string, { x: number; y: number }>();
    const centerX = 450;
    const centerY = 350;
    const radius = 250;

    nodes.forEach((n, i) => {
      const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2;
      positions.set(n.id, {
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
      });
    });

    return positions;
  }, []);

  const layoutNodes = useCallback(() => {
    if (!topology) return;

    const visibleNodes = topology.nodes.filter(n => !collapsedNodes.has(n.id));
    const visibleEdges = topology.edges.filter(e =>
      !collapsedNodes.has(e.source) && !collapsedNodes.has(e.target)
    );

    let positions: Map<string, { x: number; y: number }>;

    switch (layoutMode) {
      case 'sugiyama':
        positions = sugiyamaLayout(visibleNodes, visibleEdges);
        break;
      case 'force':
        positions = forceDirectedLayout(visibleNodes, visibleEdges);
        break;
      case 'circular':
        positions = circularLayout(visibleNodes, visibleEdges);
        break;
      default:
        positions = sugiyamaLayout(visibleNodes, visibleEdges);
    }

    nodePositions.current = positions;
  }, [topology, layoutMode, collapsedNodes, sugiyamaLayout, forceDirectedLayout, circularLayout]);

  const drawTopology = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !topology) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = `${rect.width}px`;
    canvas.style.height = `${rect.height}px`;

    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, rect.width, rect.height);

    ctx.save();
    ctx.translate(offset.x, offset.y);
    ctx.scale(scale, scale);

    const visibleEdges = topology.edges.filter(e =>
      !collapsedNodes.has(e.source) && !collapsedNodes.has(e.target)
    );

    visibleEdges.forEach((edge) => {
      const sourcePos = nodePositions.current.get(edge.source);
      const targetPos = nodePositions.current.get(edge.target);
      if (!sourcePos || !targetPos) return;

      const lineWidth = Math.max(1, Math.min(6, edge.traffic / 20));
      const edgeColor = edge.errorRate > 1 ? '#ff4d4f' : edge.errorRate > 0.5 ? '#faad14' : '#52c41a';

      ctx.beginPath();
      ctx.moveTo(sourcePos.x, sourcePos.y);
      const midY = (sourcePos.y + targetPos.y) / 2;
      ctx.bezierCurveTo(sourcePos.x, midY, targetPos.x, midY, targetPos.x, targetPos.y);
      ctx.strokeStyle = edgeColor;
      ctx.lineWidth = lineWidth;
      ctx.globalAlpha = 0.6;
      ctx.stroke();
      ctx.globalAlpha = 1;

      const arrowSize = 8;
      ctx.beginPath();
      ctx.moveTo(targetPos.x, targetPos.y - 25);
      ctx.lineTo(targetPos.x - arrowSize, targetPos.y - 25 - arrowSize);
      ctx.lineTo(targetPos.x + arrowSize, targetPos.y - 25 - arrowSize);
      ctx.closePath();
      ctx.fillStyle = edgeColor;
      ctx.fill();
    });

    const visibleNodes = topology.nodes.filter(n => !collapsedNodes.has(n.id));

    visibleNodes.forEach((node) => {
      const pos = nodePositions.current.get(node.id);
      if (!pos) return;

      const color = TOPOLOGY_COLORS[node.type] || '#8c8c8c';
      const radius = 25;

      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = color + '20';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      ctx.stroke();

      const hasChildren = topology.edges.some(e => e.source === node.id);
      if (hasChildren) {
        const isCollapsed = collapsedNodes.has(node.id);
        ctx.font = 'bold 14px sans-serif';
        ctx.fillStyle = isCollapsed ? '#1890ff' : '#8c8c8c';
        ctx.textAlign = 'center';
        ctx.fillText(isCollapsed ? '+' : '-', pos.x, pos.y - radius - 8);
      }

      ctx.font = '10px sans-serif';
      ctx.fillStyle = color;
      ctx.textAlign = 'center';
      ctx.fillText(node.name.substring(0, 8), pos.x, pos.y + 4);

      ctx.font = '9px sans-serif';
      ctx.fillStyle = '#8c8c8c';
      ctx.fillText(node.version, pos.x, pos.y + radius + 12);
    });

    ctx.restore();
  }, [topology, scale, offset, collapsedNodes]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!topology) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left - offset.x) / scale;
    const y = (e.clientY - rect.top - offset.y) / scale;

    const visibleNodes = topology.nodes.filter(n => !collapsedNodes.has(n.id));

    for (const node of visibleNodes) {
      const pos = nodePositions.current.get(node.id);
      if (!pos) continue;

      const hasChildren = topology.edges.some(edge => edge.source === node.id);
      const collapseArea = {
        x: pos.x - 10,
        y: pos.y - 25 - 20,
        w: 20,
        h: 20,
      };

      if (hasChildren && x >= collapseArea.x && x <= collapseArea.x + collapseArea.w &&
          y >= collapseArea.y && y <= collapseArea.y + collapseArea.h) {
        const children = findAllChildren(node.id);
        if (collapsedNodes.has(node.id)) {
          const newSet = new Set(collapsedNodes);
          newSet.delete(node.id);
          children.forEach(c => newSet.delete(c));
          setCollapsedNodes(newSet);
        } else {
          const newSet = new Set(collapsedNodes);
          newSet.add(node.id);
          children.forEach(c => newSet.add(c));
          setCollapsedNodes(newSet);
        }
        return;
      }

      const dx = x - pos.x;
      const dy = y - pos.y;
      if (dx * dx + dy * dy < 25 * 25) {
        setSelectedNode(node);
        setDrawerVisible(true);
        return;
      }
    }
  };

  const findAllChildren = (nodeId: string): string[] => {
    if (!topology) return [];
    const children = new Set<string>();
    const queue = [nodeId];

    while (queue.length > 0) {
      const id = queue.shift()!;
      topology.edges
        .filter(e => e.source === id)
        .forEach(e => {
          if (!children.has(e.target)) {
            children.add(e.target);
            queue.push(e.target);
          }
        });
    }

    return Array.from(children);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!dragging) return;
    setOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setDragging(false);
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale((prev) => Math.max(0.3, Math.min(3, prev + delta)));
  };

  const resetView = () => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  };

  const toggleAllCollapse = (collapse: boolean) => {
    if (collapse) {
      const all = new Set<string>();
      topology?.nodes.forEach(n => all.add(n.id));
      setCollapsedNodes(all);
    } else {
      setCollapsedNodes(new Set());
    }
  };

  const layoutModeText: Record<LayoutMode, string> = {
    sugiyama: 'Sugiyama分层',
    force: '力导向',
    circular: '环形',
  };

  return (
    <div>
      <Card
        title={
          <Space>
            流量拓扑可视化
            <Badge count={layoutTime + 'ms'} style={{ backgroundColor: '#52c41a' }} />
          </Space>
        }
        extra={
          <Space wrap>
            <Select value={namespace} onChange={setNamespace} style={{ width: 140 }}>
              <Option value="default">default</Option>
              <Option value="istio-system">istio-system</Option>
              <Option value="production">production</Option>
              <Option value="staging">staging</Option>
            </Select>

            <Group value={layoutMode} onChange={(e) => setLayoutMode(e.target.value)} size="small">
              <RadioButton value="sugiyama">分层</RadioButton>
              <RadioButton value="force">力导向</RadioButton>
              <RadioButton value="circular">环形</RadioButton>
            </Group>

            <Space.Compact>
              <Tooltip title="折叠全部">
                <Button icon={<MinusCircleOutlined />} onClick={() => toggleAllCollapse(true)} />
              </Tooltip>
              <Tooltip title="展开全部">
                <Button icon={<PlusCircleOutlined />} onClick={() => toggleAllCollapse(false)} />
              </Tooltip>
            </Space.Compact>

            <Popover
              title="折叠的节点"
              content={
                <List
                  size="small"
                  dataSource={Array.from(collapsedNodes)}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        <Button
                          type="link"
                          size="small"
                          onClick={() => {
                            const children = findAllChildren(item);
                            const newSet = new Set(collapsedNodes);
                            newSet.delete(item);
                            children.forEach(c => newSet.delete(c));
                            setCollapsedNodes(newSet);
                          }}
                        >
                          展开
                        </Button>
                      ]}
                    >
                      {item}
                    </List.Item>
                  )}
                  style={{ width: 250 }}
                />
              }
              trigger="click"
              open={showCollapsedPanel}
              onOpenChange={setShowCollapsedPanel}
            >
              <Badge count={collapsedNodes.size} size="small">
                <Button icon={<UnorderedListOutlined />}>折叠列表</Button>
              </Badge>
            </Popover>

            <Tooltip title="放大">
              <Button icon={<ZoomInOutlined />} onClick={() => setScale((s) => Math.min(3, s + 0.2))} />
            </Tooltip>
            <Tooltip title="缩小">
              <Button icon={<ZoomOutOutlined />} onClick={() => setScale((s) => Math.max(0.3, s - 0.2))} />
            </Tooltip>
            <Tooltip title="重置视图">
              <Button icon={<FullscreenOutlined />} onClick={resetView} />
            </Tooltip>
            <Button icon={<ReloadOutlined />} onClick={fetchTopology} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <Spin spinning={loading}>
          <div
            ref={containerRef}
            style={{
              width: '100%',
              height: 600,
              border: '1px solid #f0f0f0',
              borderRadius: 8,
              overflow: 'hidden',
              background: '#fafafa',
            }}
          >
            <canvas
              ref={canvasRef}
              style={{ width: '100%', height: '100%', cursor: dragging ? 'grabbing' : 'grab' }}
              onClick={handleCanvasClick}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
            />
          </div>
        </Spin>

        <div style={{ marginTop: 16, display: 'flex', gap: 24, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Space>
            <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: TOPOLOGY_COLORS.service }} />
            <span>Service</span>
          </Space>
          <Space>
            <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: TOPOLOGY_COLORS.gateway }} />
            <span>Gateway</span>
          </Space>
          <Space>
            <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: '50%', background: TOPOLOGY_COLORS.workload }} />
            <span>Workload</span>
          </Space>
          <Divider type="vertical" />
          <Space>
            <span style={{ display: 'inline-block', width: 30, height: 3, background: '#52c41a', borderRadius: 2 }} />
            <span>正常</span>
          </Space>
          <Space>
            <span style={{ display: 'inline-block', width: 30, height: 3, background: '#faad14', borderRadius: 2 }} />
            <span>警告</span>
          </Space>
          <Space>
            <span style={{ display: 'inline-block', width: 30, height: 3, background: '#ff4d4f', borderRadius: 2 }} />
            <span>异常</span>
          </Space>
        </div>
      </Card>

      <Drawer
        title="服务详情"
        placement="right"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        width={400}
      >
        {selectedNode && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="服务名称">{selectedNode.name}</Descriptions.Item>
            <Descriptions.Item label="命名空间">{selectedNode.namespace}</Descriptions.Item>
            <Descriptions.Item label="类型">
              <Tag color={TOPOLOGY_COLORS[selectedNode.type] || 'default'}>{selectedNode.type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="版本">{selectedNode.version || '-'}</Descriptions.Item>
            <Descriptions.Item label="节点ID">{selectedNode.id}</Descriptions.Item>
            {selectedNode.metrics && (
              <>
                <Descriptions.Item label="请求量">{selectedNode.metrics.requestCount}</Descriptions.Item>
                <Descriptions.Item label="错误率">
                  {selectedNode.metrics.errorCount > 0
                    ? ((selectedNode.metrics.errorCount / selectedNode.metrics.requestCount) * 100).toFixed(2) + '%'
                    : '0%'}
                </Descriptions.Item>
                <Descriptions.Item label="P50延迟">{selectedNode.metrics.p50Latency.toFixed(1)}ms</Descriptions.Item>
                <Descriptions.Item label="P95延迟">{selectedNode.metrics.p95Latency.toFixed(1)}ms</Descriptions.Item>
                <Descriptions.Item label="P99延迟">{selectedNode.metrics.p99Latency.toFixed(1)}ms</Descriptions.Item>
                <Descriptions.Item label="成功率">{(selectedNode.metrics.successRate * 100).toFixed(2)}%</Descriptions.Item>
                <Descriptions.Item label="吞吐量">{selectedNode.metrics.throughput.toFixed(1)} req/s</Descriptions.Item>
              </>
            )}
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default Topology;
