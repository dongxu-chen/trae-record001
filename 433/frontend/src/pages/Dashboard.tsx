import { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Spin, Alert } from 'antd';
import { DollarOutlined, CloudServerOutlined, RiseOutlined, AlertOutlined } from '@ant-design/icons';
import { api, NamespaceCost, IdleResource } from '../services/api';

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCost, setTotalCost] = useState(0);
  const [namespaceCount, setNamespaceCount] = useState(0);
  const [idleSavings, setIdleSavings] = useState(0);
  const [topNamespaces, setTopNamespaces] = useState<NamespaceCost[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [costRes, idleRes] = await Promise.all([
        api.getNamespaceCosts(24),
        api.getIdleResources(24),
      ]);

      const costs = costRes.data.data;
      const total = costs.reduce((sum, nc) => sum + nc.cost.total, 0);
      const savings = idleRes.data.data.reduce((sum, ir) => sum + ir.idleCost, 0);

      setTotalCost(total);
      setNamespaceCount(costs.length);
      setIdleSavings(savings);
      setTopNamespaces(costs.slice(0, 5));
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard data. Please ensure the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      {error && (
        <Alert
          message="Error"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Cost (24h)"
              value={totalCost}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="USD"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Namespaces"
              value={namespaceCount}
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Potential Monthly Savings"
              value={idleSavings}
              precision={2}
              prefix={<RiseOutlined />}
              suffix="USD"
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Optimization Opportunities"
              value={topNamespaces.length}
              prefix={<AlertOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={12}>
          <Card title="Top 5 Costly Namespaces">
            {topNamespaces.map((ns, index) => (
              <div
                key={ns.namespace}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '12px 0',
                  borderBottom: index < topNamespaces.length - 1 ? '1px solid #f0f0f0' : 'none',
                }}
              >
                <span>{ns.namespace}</span>
                <strong>${ns.cost.total.toFixed(4)}</strong>
              </div>
            ))}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Cost Breakdown (Total)">
            <div style={{ padding: '12px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <span>CPU</span>
                <strong>${topNamespaces.reduce((s, n) => s + n.cost.cpu, 0).toFixed(4)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <span>Memory</span>
                <strong>${topNamespaces.reduce((s, n) => s + n.cost.memory, 0).toFixed(4)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <span>Storage</span>
                <strong>${topNamespaces.reduce((s, n) => s + n.cost.storage, 0).toFixed(4)}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Network</span>
                <strong>${topNamespaces.reduce((s, n) => s + n.cost.network, 0).toFixed(4)}</strong>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
