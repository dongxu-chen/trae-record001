import { useState, useEffect } from 'react';
import { Card, Table, Input, InputNumber, Button, Space, Spin, Alert } from 'antd';
import { api, LabelCost } from '../services/api';

export default function LabelCostPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(24);
  const [labelKey, setLabelKey] = useState('environment');
  const [costs, setCosts] = useState<LabelCost[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getLabelCosts(duration, labelKey);
      setCosts(res.data.data);
      setError(null);
    } catch (err) {
      setError('Failed to load label costs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [duration, labelKey]);

  const columns = [
    {
      title: 'Label Key',
      dataIndex: 'labelKey',
      key: 'labelKey',
    },
    {
      title: 'Label Value',
      dataIndex: 'labelValue',
      key: 'labelValue',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: 'Namespaces',
      dataIndex: 'namespaces',
      key: 'namespaces',
      render: (val: string[]) => val.join(', '),
    },
    {
      title: 'CPU Cost',
      dataIndex: ['cost', 'cpu'],
      key: 'cpu',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: LabelCost, b: LabelCost) => a.cost.cpu - b.cost.cpu,
    },
    {
      title: 'Memory Cost',
      dataIndex: ['cost', 'memory'],
      key: 'memory',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: LabelCost, b: LabelCost) => a.cost.memory - b.cost.memory,
    },
    {
      title: 'Storage Cost',
      dataIndex: ['cost', 'storage'],
      key: 'storage',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: LabelCost, b: LabelCost) => a.cost.storage - b.cost.storage,
    },
    {
      title: 'Network Cost',
      dataIndex: ['cost', 'network'],
      key: 'network',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: LabelCost, b: LabelCost) => a.cost.network - b.cost.network,
    },
    {
      title: 'Total Cost',
      dataIndex: ['cost', 'total'],
      key: 'total',
      render: (val: number) => <strong>${val.toFixed(4)}</strong>,
      sorter: (a: LabelCost, b: LabelCost) => a.cost.total - b.cost.total,
      defaultSortOrder: 'descend' as const,
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
          <span>Label Key:</span>
          <Input value={labelKey} onChange={(e) => setLabelKey(e.target.value)} style={{ width: 150 }} />
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
        <Card title="Label Cost Details">
          <Table dataSource={costs} columns={columns} rowKey={(record) => `${record.labelKey}-${record.labelValue}`} pagination={{ pageSize: 10 }} />
        </Card>
      )}
    </div>
  );
}
