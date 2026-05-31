import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Tag, Table, Spin, message } from 'antd';
import {
  CloudServerOutlined,
  BranchesOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { routingAPI, topologyAPI, metricsAPI } from '../services/api';
import type { RoutingRule, TrafficTopology } from '../types';

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [rules, setRules] = useState<RoutingRule[]>([]);
  const [topology, setTopology] = useState<TrafficTopology | null>(null);
  const [namespace, setNamespace] = useState('default');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [rulesRes, topologyRes] = await Promise.allSettled([
        routingAPI.getRoutingRules(namespace),
        topologyAPI.getTopology(namespace),
      ]);

      if (rulesRes.status === 'fulfilled') {
        setRules(rulesRes.value.data?.rules || []);
      }
      if (topologyRes.status === 'fulfilled') {
        setTopology(topologyRes.value.data);
      }
    } catch (err) {
      message.error('获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  const activeRules = rules.filter((r) => r.status === 'active');
  const weightRules = rules.filter((r) => r.type === 'weight');
  const headerRules = rules.filter((r) => r.type === 'header');
  const mirrorRules = rules.filter((r) => r.type === 'mirror');
  const faultRules = rules.filter((r) => r.type === 'fault');

  const typeTagMap: Record<string, { color: string; label: string }> = {
    weight: { color: 'blue', label: '权重路由' },
    header: { color: 'green', label: 'Header路由' },
    mirror: { color: 'purple', label: '流量镜像' },
    fault: { color: 'red', label: '故障注入' },
  };

  const columns = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const tag = typeTagMap[type] || { color: 'default', label: type };
        return <Tag color={tag.color}>{tag.label}</Tag>;
      },
    },
    {
      title: '服务',
      dataIndex: 'serviceName',
      key: 'serviceName',
    },
    {
      title: '命名空间',
      dataIndex: 'namespace',
      key: 'namespace',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status === 'active' ? '活跃' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      render: (v: string) => (v ? new Date(v).toLocaleString('zh-CN') : '-'),
    },
  ];

  return (
    <Spin spinning={loading}>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃路由规则"
              value={activeRules.length}
              prefix={<BranchesOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="服务数量"
              value={topology?.nodes?.length || 0}
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="流量连接数"
              value={topology?.edges?.length || 0}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="系统状态"
              value="正常"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" title="权重路由">
            <Statistic value={weightRules.length} suffix="条" valueStyle={{ fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" title="Header路由">
            <Statistic value={headerRules.length} suffix="条" valueStyle={{ fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" title="流量镜像">
            <Statistic value={mirrorRules.length} suffix="条" valueStyle={{ fontSize: 24 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" title="故障注入">
            <Statistic value={faultRules.length} suffix="条" valueStyle={{ fontSize: 24 }} />
          </Card>
        </Col>
      </Row>

      <Card title="路由规则列表" style={{ marginTop: 16 }}>
        <Table
          columns={columns}
          dataSource={rules}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          size="middle"
        />
      </Card>
    </Spin>
  );
};

export default Dashboard;
