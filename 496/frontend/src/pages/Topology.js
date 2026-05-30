import React, { useState, useEffect, useRef } from 'react';
import { Card, Spin, Row, Col, Descriptions, Tag, Table, Space } from 'antd';
import { topologyAPI } from '../services/api';

function Topology() {
  const [loading, setLoading] = useState(true);
  const [topology, setTopology] = useState(null);
  const [selectedService, setSelectedService] = useState(null);
  const containerRef = useRef(null);

  useEffect(() => {
    loadTopology();
  }, []);

  const loadTopology = async () => {
    try {
      setLoading(true);
      const res = await topologyAPI.getTopology();
      setTopology(res.data);
    } catch (error) {
      console.error('Failed to load topology:', error);
    } finally {
      setLoading(false);
    }
  };

  const getNodeColor = (service) => {
    if (!service?.metrics) return '#1890ff';
    const { cpuUtilization, errorRate } = service.metrics;
    if (cpuUtilization > 0.8 || errorRate > 0.05) return '#ff4d4f';
    if (cpuUtilization > 0.6 || errorRate > 0.02) return '#faad14';
    return '#52c41a';
  };

  const renderTopology = () => {
    if (!topology) return null;

    const width = 900;
    const height = 500;
    const nodes = topology.nodes || [];
    const edges = topology.edges || [];

    const levels = {};
    const visited = new Set();
    const nodeMap = {};

    nodes.forEach(node => {
      nodeMap[node.serviceId] = node;
    });

    const calculateLevel = (serviceId, level) => {
      if (visited.has(serviceId)) return;
      visited.add(serviceId);
      levels[serviceId] = Math.max(levels[serviceId] || 0, level);

      const node = nodeMap[serviceId];
      if (node?.dependencies) {
        node.dependencies.forEach(dep => calculateLevel(dep, level + 1));
      }
    };

    nodes.forEach(node => {
      if (!visited.has(node.serviceId)) {
        calculateLevel(node.serviceId, 0);
      }
    });

    const levelGroups = {};
    Object.entries(levels).forEach(([id, level]) => {
      if (!levelGroups[level]) levelGroups[level] = [];
      levelGroups[level].push(id);
    });

    const positions = {};
    const maxLevel = Math.max(...Object.values(levels), 0);

    Object.entries(levelGroups).forEach(([level, ids]) => {
      const levelWidth = width / (maxLevel + 2);
      const x = levelWidth * (maxLevel - parseInt(level) + 1);
      const spacing = height / (ids.length + 1);
      ids.forEach((id, index) => {
        positions[id] = {
          x: x + levelWidth / 2,
          y: spacing * (index + 1),
        };
      });
    });

    return (
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`}>
        {edges.map((edge, index) => {
          const from = positions[edge.sourceServiceId];
          const to = positions[edge.targetServiceId];
          if (!from || !to) return null;

          return (
            <line
              key={`edge-${index}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="#d9d9d9"
              strokeWidth={Math.min(3, Math.max(1, edge.weight / 10))}
              markerEnd="url(#arrowhead)"
            />
          );
        })}

        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#d9d9d9" />
          </marker>
        </defs>

        {nodes.map(node => {
          const pos = positions[node.serviceId];
          if (!pos) return null;

          return (
            <g key={node.serviceId}>
              <circle
                cx={pos.x}
                cy={pos.y}
                r={35}
                fill={getNodeColor(node)}
                stroke="#fff"
                strokeWidth={3}
                className="node-circle"
                onClick={() => setSelectedService(node)}
              />
              <text
                x={pos.x}
                y={pos.y + 5}
                textAnchor="middle"
                fill="#fff"
                fontSize="11"
                fontWeight="bold"
                style={{ pointerEvents: 'none' }}
              >
                {node.serviceName.length > 8 ? node.serviceName.substring(0, 8) + '...' : node.serviceName}
              </text>
            </g>
          );
        })}
      </svg>
    );
  };

  const edgeColumns = [
    { title: '源服务', dataIndex: 'sourceServiceId', key: 'source' },
    { title: '目标服务', dataIndex: 'targetServiceId', key: 'target' },
    { title: '调用频率', dataIndex: 'callRate', key: 'callRate', render: v => `${v.toFixed(1)}/s` },
    { title: '平均延迟', dataIndex: 'avgLatencyMs', key: 'latency', render: v => `${v.toFixed(0)}ms` },
    { title: '错误率', dataIndex: 'errorRate', key: 'errorRate', render: v => `${(v * 100).toFixed(2)}%` },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>服务拓扑分析</h2>

      <Row gutter={24}>
        <Col span={24}>
          <Card
            title="服务调用拓扑图"
            extra={
              <Space>
                <Tag color="green">健康</Tag>
                <Tag color="orange">警告</Tag>
                <Tag color="red">异常</Tag>
              </Space>
            }
            loading={loading}
          >
            <div className="topology-container" ref={containerRef}>
              <Spin spinning={loading}>
                {renderTopology()}
              </Spin>
            </div>
          </Card>
        </Col>
      </Row>

      {selectedService && (
        <Card
          title={`服务详情: ${selectedService.serviceName}`}
          style={{ marginTop: 24 }}
          className="service-detail-card"
        >
          <Descriptions bordered column={3}>
            <Descriptions.Item label="服务ID">{selectedService.serviceId}</Descriptions.Item>
            <Descriptions.Item label="版本">{selectedService.version}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color="green">{selectedService.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="平均QPS" span={1}>
              {selectedService.metrics?.avgQps?.toFixed(0) || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="峰值QPS" span={1}>
              {selectedService.metrics?.peakQps?.toFixed(0) || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="实例数" span={1}>
              {selectedService.metrics?.instanceCount || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="平均延迟" span={1}>
              {selectedService.metrics?.avgLatencyMs?.toFixed(0)}ms
            </Descriptions.Item>
            <Descriptions.Item label="P95延迟" span={1}>
              {selectedService.metrics?.p95LatencyMs?.toFixed(0)}ms
            </Descriptions.Item>
            <Descriptions.Item label="P99延迟" span={1}>
              {selectedService.metrics?.p99LatencyMs?.toFixed(0)}ms
            </Descriptions.Item>
            <Descriptions.Item label="错误率" span={1}>
              {(selectedService.metrics?.errorRate * 100)?.toFixed(2)}%
            </Descriptions.Item>
            <Descriptions.Item label="CPU使用率" span={1}>
              {(selectedService.metrics?.cpuUtilization * 100)?.toFixed(1)}%
            </Descriptions.Item>
            <Descriptions.Item label="内存使用率" span={1}>
              {(selectedService.metrics?.memoryUtilization * 100)?.toFixed(1)}%
            </Descriptions.Item>
            <Descriptions.Item label="依赖服务" span={3}>
              {selectedService.dependencies?.map(dep => (
                <Tag key={dep} color="blue">{dep}</Tag>
              )) || '-'}
            </Descriptions.Item>
          </Descriptions>

          {selectedService.endpoints && (
            <div style={{ marginTop: 16 }}>
              <h4>API端点</h4>
              <Table
                dataSource={Object.entries(selectedService.endpoints).map(([key, val]) => ({
                  key,
                  ...val,
                }))}
                columns={[
                  { title: '路径', dataIndex: 'path', key: 'path' },
                  { title: '方法', dataIndex: 'method', key: 'method',
                    render: v => <Tag color={v === 'GET' ? 'green' : v === 'POST' ? 'blue' : 'orange'}>{v}</Tag>
                  },
                  { title: '平均QPS', dataIndex: ['metrics', 'avgQps'], key: 'qps', render: v => v?.toFixed(0) },
                  { title: '平均延迟', dataIndex: ['metrics', 'avgLatencyMs'], key: 'latency', render: v => `${v?.toFixed(0)}ms` },
                  { title: '错误率', dataIndex: ['metrics', 'errorRate'], key: 'error', render: v => `${(v * 100)?.toFixed(2)}%` },
                ]}
                pagination={false}
                size="small"
              />
            </div>
          )}
        </Card>
      )}

      <Card title="服务调用关系" style={{ marginTop: 24 }} loading={loading}>
        <Table
          columns={edgeColumns}
          dataSource={topology?.edges || []}
          rowKey={(e, i) => i}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
}

export default Topology;
