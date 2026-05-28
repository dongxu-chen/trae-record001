import { useState, useEffect } from 'react';
import { Card, Table, InputNumber, Button, Space, Spin, Alert } from 'antd';
import { api, NamespaceCost } from '../services/api';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

export default function NamespaceCostPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(24);
  const [costs, setCosts] = useState<NamespaceCost[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getNamespaceCosts(duration);
      setCosts(res.data.data);
      setError(null);
    } catch (err) {
      setError('Failed to load namespace costs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [duration]);

  const columns = [
    {
      title: 'Namespace',
      dataIndex: 'namespace',
      key: 'namespace',
      render: (text: string) => <code>{text}</code>,
    },
    {
      title: 'CPU Cost',
      dataIndex: ['cost', 'cpu'],
      key: 'cpu',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: NamespaceCost, b: NamespaceCost) => a.cost.cpu - b.cost.cpu,
    },
    {
      title: 'Memory Cost',
      dataIndex: ['cost', 'memory'],
      key: 'memory',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: NamespaceCost, b: NamespaceCost) => a.cost.memory - b.cost.memory,
    },
    {
      title: 'Storage Cost',
      dataIndex: ['cost', 'storage'],
      key: 'storage',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: NamespaceCost, b: NamespaceCost) => a.cost.storage - b.cost.storage,
    },
    {
      title: 'Network Cost',
      dataIndex: ['cost', 'network'],
      key: 'network',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: NamespaceCost, b: NamespaceCost) => a.cost.network - b.cost.network,
    },
    {
      title: 'Total Cost',
      dataIndex: ['cost', 'total'],
      key: 'total',
      render: (val: number) => <strong>${val.toFixed(4)}</strong>,
      sorter: (a: NamespaceCost, b: NamespaceCost) => a.cost.total - b.cost.total,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: 'Storage Used (GB)',
      dataIndex: ['resourceUsage', 'storageUsedGB'],
      key: 'storageUsed',
      render: (val: number) => val.toFixed(3),
      sorter: (a: NamespaceCost, b: NamespaceCost) => a.resourceUsage.storageUsedGB - b.resourceUsage.storageUsedGB,
    },
    {
      title: 'External RX (GB)',
      dataIndex: ['resourceUsage', 'networkExternalRxGB'],
      key: 'externalRx',
      render: (val: number) => val.toFixed(3),
    },
    {
      title: 'External TX (GB)',
      dataIndex: ['resourceUsage', 'networkExternalTxGB'],
      key: 'externalTx',
      render: (val: number) => val.toFixed(3),
    },
    {
      title: 'Custom Factor',
      dataIndex: 'customFactor',
      key: 'factor',
      render: (val: number) => val.toFixed(2),
    },
  ];

  const pieData = costs.map((nc) => ({
    name: nc.namespace,
    value: nc.cost.total,
  }));

  const barData = costs.map((nc) => ({
    name: nc.namespace,
    CPU: nc.cost.cpu,
    Memory: nc.cost.memory,
    Storage: nc.cost.storage,
    Network: nc.cost.network,
  }));

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
          <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
            <Card title="Cost Distribution" style={{ flex: 1 }}>
              <div className="chart-container">
                <PieChart width={400} height={300}>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label
                  >
                    {pieData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => `$${value.toFixed(4)}`} />
                  <Legend />
                </PieChart>
              </div>
            </Card>

            <Card title="Cost Breakdown by Resource" style={{ flex: 1 }}>
              <div className="chart-container">
                <BarChart width={400} height={300} data={barData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis />
                  <Tooltip formatter={(value: number) => `$${value.toFixed(4)}`} />
                  <Legend />
                  <Bar dataKey="CPU" fill="#0088FE" />
                  <Bar dataKey="Memory" fill="#00C49F" />
                  <Bar dataKey="Storage" fill="#FFBB28" />
                  <Bar dataKey="Network" fill="#FF8042" />
                </BarChart>
              </div>
            </Card>
          </div>

          <Card title="Namespace Cost Details">
            <Table dataSource={costs} columns={columns} rowKey="namespace" pagination={{ pageSize: 10 }} />
          </Card>
        </>
      )}
    </div>
  );
}
