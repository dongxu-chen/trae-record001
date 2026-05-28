import { useState, useEffect } from 'react';
import { Card, Table, Spin, Alert, Tag, Button, Space, InputNumber } from 'antd';
import { api, OptimizationSuggestion } from '../services/api';

export default function OptimizationsPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(24);
  const [suggestions, setSuggestions] = useState<OptimizationSuggestion[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getOptimizations(duration);
      setSuggestions(res.data.data);
      setError(null);
    } catch (err) {
      setError('Failed to load optimizations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [duration]);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'red';
      case 'medium':
        return 'orange';
      case 'low':
        return 'green';
      default:
        return 'default';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'resource-rightsizing':
        return '⚙️';
      case 'environment-tagging':
        return '🏷️';
      default:
        return '💡';
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
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (val: string) => (
        <Space>
          <span>{getTypeIcon(val)}</span>
          <span>{val}</span>
        </Space>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'Estimated Monthly Savings',
      dataIndex: 'estimatedSavings',
      key: 'estimatedSavings',
      render: (val: number) => <strong>${val.toFixed(2)}</strong>,
      sorter: (a: OptimizationSuggestion, b: OptimizationSuggestion) =>
        a.estimatedSavings - b.estimatedSavings,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (val: string) => <Tag color={getSeverityColor(val)}>{val.toUpperCase()}</Tag>,
    },
  ];

  const totalSavings = suggestions.reduce((sum, s) => sum + s.estimatedSavings, 0);
  const highPriorityCount = suggestions.filter((s) => s.severity === 'high').length;

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
          <Card title="Optimization Summary" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', gap: 24, padding: '16px 0' }}>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                  ${totalSavings.toFixed(2)}
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>Total Estimated Monthly Savings</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
                  {highPriorityCount}
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>High Priority Items</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                  {suggestions.length}
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>Total Optimization Opportunities</div>
              </div>
            </div>
          </Card>

          <Card title="Optimization Suggestions">
            <Table
              dataSource={suggestions}
              columns={columns}
              rowKey={(record) => `${record.namespace}-${record.type}`}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </>
      )}
    </div>
  );
}
