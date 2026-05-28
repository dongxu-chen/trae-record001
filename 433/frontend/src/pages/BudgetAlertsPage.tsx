import { useState, useEffect } from 'react';
import { Card, Table, Spin, Alert, Button, Space, InputNumber, Tag, Progress } from 'antd';
import { api, BudgetAlert } from '../services/api';

export default function BudgetAlertsPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(24);
  const [alerts, setAlerts] = useState<BudgetAlert[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getBudgetAlerts(duration);
      setAlerts(res.data.data);
      setError(null);
    } catch (err) {
      setError('Failed to load budget alerts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [duration]);

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'critical':
        return 'red';
      case 'warning':
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
      title: 'Current Cost',
      dataIndex: 'currentCost',
      key: 'currentCost',
      render: (val: number) => `$${val.toFixed(2)}`,
      sorter: (a: BudgetAlert, b: BudgetAlert) => a.currentCost - b.currentCost,
    },
    {
      title: 'Budget',
      dataIndex: 'budget',
      key: 'budget',
      render: (val: number) => `$${val.toFixed(2)}`,
    },
    {
      title: 'Usage',
      dataIndex: 'percentage',
      key: 'percentage',
      render: (val: number) => (
        <Progress
          percent={val * 100}
          size="small"
          status={val >= 1 ? 'exception' : val >= 0.8 ? 'normal' : 'success'}
        />
      ),
      sorter: (a: BudgetAlert, b: BudgetAlert) => a.percentage - b.percentage,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: 'Projected Cost',
      dataIndex: 'projectedCost',
      key: 'projectedCost',
      render: (val: number, record: BudgetAlert) => (
        <span style={{ color: val > record.budget ? '#ff4d4f' : undefined }}>
          ${val.toFixed(2)}
        </span>
      ),
    },
    {
      title: 'Days Remaining',
      dataIndex: 'daysRemaining',
      key: 'daysRemaining',
    },
    {
      title: 'Level',
      dataIndex: 'level',
      key: 'level',
      render: (val: string) => <Tag color={getLevelColor(val)}>{val.toUpperCase()}</Tag>,
    },
    {
      title: 'Message',
      dataIndex: 'message',
      key: 'message',
    },
  ];

  const criticalCount = alerts.filter((a) => a.level === 'critical').length;
  const warningCount = alerts.filter((a) => a.level === 'warning').length;

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
          <Card title="Alert Summary" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', gap: 24, padding: '16px 0' }}>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
                  {criticalCount}
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>Critical Alerts</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
                  {warningCount}
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>Warning Alerts</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                  {alerts.length}
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>Total Alerts</div>
              </div>
            </div>
          </Card>

          <Card title="Budget Alerts">
            <Table
              dataSource={alerts}
              columns={columns}
              rowKey="namespace"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </>
      )}
    </div>
  );
}
