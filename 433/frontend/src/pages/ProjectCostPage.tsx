import { useState, useEffect } from 'react';
import { Card, Table, Input, InputNumber, Button, Space, Spin, Alert } from 'antd';
import { api, ProjectCost } from '../services/api';
import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

export default function ProjectCostPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(24);
  const [projectLabel, setProjectLabel] = useState('project');
  const [costs, setCosts] = useState<ProjectCost[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getProjectCosts(duration, projectLabel);
      setCosts(res.data.data);
      setError(null);
    } catch (err) {
      setError('Failed to load project costs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [duration, projectLabel]);

  const columns = [
    {
      title: 'Project',
      dataIndex: 'projectName',
      key: 'projectName',
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
      sorter: (a: ProjectCost, b: ProjectCost) => a.cost.cpu - b.cost.cpu,
    },
    {
      title: 'Memory Cost',
      dataIndex: ['cost', 'memory'],
      key: 'memory',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: ProjectCost, b: ProjectCost) => a.cost.memory - b.cost.memory,
    },
    {
      title: 'Storage Cost',
      dataIndex: ['cost', 'storage'],
      key: 'storage',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: ProjectCost, b: ProjectCost) => a.cost.storage - b.cost.storage,
    },
    {
      title: 'Network Cost',
      dataIndex: ['cost', 'network'],
      key: 'network',
      render: (val: number) => `$${val.toFixed(4)}`,
      sorter: (a: ProjectCost, b: ProjectCost) => a.cost.network - b.cost.network,
    },
    {
      title: 'Total Cost',
      dataIndex: ['cost', 'total'],
      key: 'total',
      render: (val: number) => <strong>${val.toFixed(4)}</strong>,
      sorter: (a: ProjectCost, b: ProjectCost) => a.cost.total - b.cost.total,
      defaultSortOrder: 'descend' as const,
    },
  ];

  const pieData = costs.map((pc) => ({
    name: pc.projectName,
    value: pc.cost.total,
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
          <span>Project Label:</span>
          <Input value={projectLabel} onChange={(e) => setProjectLabel(e.target.value)} style={{ width: 150 }} />
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
          <Card title="Project Cost Distribution" style={{ marginBottom: 24 }}>
            <div className="chart-container" style={{ textAlign: 'center' }}>
              <PieChart width={500} height={400}>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={150}
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

          <Card title="Project Cost Details">
            <Table dataSource={costs} columns={columns} rowKey="projectName" pagination={{ pageSize: 10 }} />
          </Card>
        </>
      )}
    </div>
  );
}
