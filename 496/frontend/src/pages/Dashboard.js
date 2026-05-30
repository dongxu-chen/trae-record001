import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Progress } from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  ApartmentOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { topologyAPI, rateLimitAPI } from '../services/api';

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalServices: 0,
    activeConfigs: 0,
    bottlenecks: 0,
    avgConfidence: 0,
  });
  const [services, setServices] = useState([]);
  const [recommendations, setRecommendations] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [servicesRes, recommendationsRes, bottlenecksRes] = await Promise.all([
        topologyAPI.getServices(),
        rateLimitAPI.getAllRecommendations(),
        topologyAPI.getBottlenecks(),
      ]);

      setServices(servicesRes.data);
      setRecommendations(recommendationsRes.data);

      const avgConfidence = recommendationsRes.data.length > 0
        ? recommendationsRes.data.reduce((sum, r) => sum + (r.recommendedServiceRule?.confidenceScore || 0), 0) / recommendationsRes.data.length
        : 0;

      setStats({
        totalServices: servicesRes.data.length,
        activeConfigs: 3,
        bottlenecks: bottlenecksRes.data.length,
        avgConfidence: (avgConfidence * 100).toFixed(1),
      });
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getHealthStatus = (service) => {
    if (!service.metrics) return { status: 'normal', color: 'green' };
    const { cpuUtilization, errorRate, p99LatencyMs } = service.metrics;
    
    if (cpuUtilization > 0.8 || errorRate > 0.05 || p99LatencyMs > 500) {
      return { status: '危险', color: 'red', icon: <ExclamationCircleOutlined /> };
    }
    if (cpuUtilization > 0.6 || errorRate > 0.02 || p99LatencyMs > 200) {
      return { status: '警告', color: 'orange', icon: <WarningOutlined /> };
    }
    return { status: '健康', color: 'green', icon: <CheckCircleOutlined /> };
  };

  const serviceColumns = [
    {
      title: '服务名称',
      dataIndex: 'serviceName',
      key: 'serviceName',
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record) => {
        const health = getHealthStatus(record);
        return <Tag color={health.color} icon={health.icon}>{health.status}</Tag>;
      },
    },
    {
      title: '平均QPS',
      dataIndex: ['metrics', 'avgQps'],
      key: 'avgQps',
      render: (v) => v?.toFixed(0) || '-',
    },
    {
      title: '峰值QPS',
      dataIndex: ['metrics', 'peakQps'],
      key: 'peakQps',
      render: (v) => v?.toFixed(0) || '-',
    },
    {
      title: 'P99延迟',
      dataIndex: ['metrics', 'p99LatencyMs'],
      key: 'p99Latency',
      render: (v) => v ? `${v.toFixed(0)}ms` : '-',
    },
    {
      title: '错误率',
      dataIndex: ['metrics', 'errorRate'],
      key: 'errorRate',
      render: (v) => v ? `${(v * 100).toFixed(2)}%` : '-',
    },
    {
      title: 'CPU使用率',
      dataIndex: ['metrics', 'cpuUtilization'],
      key: 'cpuUtilization',
      render: (v) => (
        <Progress 
          percent={v ? (v * 100).toFixed(0) : 0} 
          size="small"
          status={v > 0.8 ? 'exception' : v > 0.6 ? 'normal' : 'success'}
        />
      ),
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>系统概览</h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="服务总数"
              value={stats.totalServices}
              prefix={<ApartmentOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="已应用配置"
              value={stats.activeConfigs}
              prefix={<SettingOutlined />}
              valueStyle={{ color: '#1890ff' }}
              suffix={<span style={{ fontSize: 14, color: '#52c41a' }}><ArrowUpOutlined /> 2</span>}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="瓶颈服务"
              value={stats.bottlenecks}
              prefix={<WarningOutlined />}
              valueStyle={{ color: stats.bottlenecks > 0 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card loading={loading}>
            <Statistic
              title="推荐置信度"
              value={stats.avgConfidence}
              suffix="%"
              precision={1}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="服务健康状态" loading={loading}>
        <Table
          columns={serviceColumns}
          dataSource={services}
          rowKey="serviceId"
          pagination={{ pageSize: 5 }}
        />
      </Card>
    </div>
  );
}

export default Dashboard;
