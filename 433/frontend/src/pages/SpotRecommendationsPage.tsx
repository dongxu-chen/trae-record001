import { useState, useEffect } from 'react';
import { Card, Table, Spin, Alert, Button, Space, InputNumber, Tag, Row, Col, Statistic } from 'antd';
import { api, SpotRecommendation } from '../services/api';
import { ThunderboltOutlined, DollarOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';

export default function SpotRecommendationsPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(24);
  const [recommendations, setRecommendations] = useState<SpotRecommendation[]>([]);
  const [totalSavings, setTotalSavings] = useState(0);
  const [eligibleCount, setEligibleCount] = useState(0);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getSpotRecommendations(duration);
      setRecommendations(res.data.data);
      setTotalSavings(res.data.totalMonthlySavings);
      setEligibleCount(res.data.eligibleCount);
      setError(null);
    } catch (err) {
      setError('Failed to load spot recommendations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [duration]);

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high':
        return 'red';
      case 'medium':
        return 'orange';
      default:
        return 'green';
    }
  };

  const columns = [
    {
      title: 'Namespace',
      dataIndex: 'namespace',
      key: 'namespace',
      render: (text: string) => <code>{text}</code>,
    },
    {
      title: 'CPU Requested',
      dataIndex: 'cpuCores',
      key: 'cpuCores',
      render: (val: number) => `${val.toFixed(2)} cores`,
    },
    {
      title: 'Memory Requested',
      dataIndex: 'memoryGB',
      key: 'memoryGB',
      render: (val: number) => `${val.toFixed(2)} GB`,
    },
    {
      title: 'On-Demand Monthly',
      dataIndex: 'onDemandMonthly',
      key: 'onDemandMonthly',
      render: (val: number) => `$${val.toFixed(2)}`,
    },
    {
      title: 'Spot Monthly',
      dataIndex: 'spotMonthly',
      key: 'spotMonthly',
      render: (val: number) => `$${val.toFixed(2)}`,
    },
    {
      title: 'Monthly Savings',
      dataIndex: 'monthlySavings',
      key: 'monthlySavings',
      render: (val: number) => <strong style={{ color: '#52c41a' }}>${val.toFixed(2)}</strong>,
      sorter: (a: SpotRecommendation, b: SpotRecommendation) => a.monthlySavings - b.monthlySavings,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: 'Savings %',
      dataIndex: 'savingsPercent',
      key: 'savingsPercent',
      render: (val: number) => `${val.toFixed(1)}%`,
    },
    {
      title: 'Interruption Risk',
      dataIndex: 'interruptionRisk',
      key: 'interruptionRisk',
      render: (val: string) => <Tag color={getRiskColor(val)}>{val.toUpperCase()}</Tag>,
    },
    {
      title: 'Workload Type',
      dataIndex: 'workloadType',
      key: 'workloadType',
    },
    {
      title: 'Eligible',
      dataIndex: 'eligible',
      key: 'eligible',
      render: (val: boolean) =>
        val ? (
          <Tag icon={<CheckCircleOutlined />} color="green">
            Yes
          </Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="red">
            No
          </Tag>
        ),
    },
    {
      title: 'Reason',
      dataIndex: 'reason',
      key: 'reason',
    },
  ];

  return (
    <div>
      {error && (
        <Alert message="Error" description={error} type="error" showIcon style={{ marginBottom: 24 }} />
      )}

      <Card style={{ marginBottom: 24 }}>
        <Space>
          <span>Duration (hours):</span>
          <InputNumber min={1} max={720} value={duration} onChange={setDuration} />
          <Button type="primary" onClick={loadData} loading={loading}>
            Refresh
          </Button>
        </Space>
      </Card>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Eligible Namespaces"
                  value={eligibleCount}
                  prefix={<ThunderboltOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Total Namespaces"
                  value={recommendations.length}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Potential Monthly Savings"
                  value={totalSavings}
                  precision={2}
                  prefix={<DollarOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
          </Row>

          <Card title="Spot Instance Recommendations">
            <Table
              dataSource={recommendations}
              columns={columns}
              rowKey="namespace"
              pagination={{ pageSize: 10 }}
            />
          </Card>

          <Card title="Spot Instance Best Practices" style={{ marginTop: 24 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Alert
                message="Good Candidates for Spot"
                description="Batch processing, CI/CD workers, stateless APIs, development/staging environments, machine learning training"
                type="success"
                showIcon
              />
              <Alert
                message="Poor Candidates for Spot"
                description="Production databases, stateful applications, real-time services, critical workloads that cannot tolerate interruptions"
                type="error"
                showIcon
              />
              <Alert
                message="Implementation Tips"
                description="Use Spot with Auto Scaling Groups, implement graceful shutdown handlers, distribute workloads across multiple instance types and AZs"
                type="info"
                showIcon
              />
            </Space>
          </Card>
        </>
      )}
    </div>
  );
}
