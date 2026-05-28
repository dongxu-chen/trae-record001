import { useState, useEffect } from 'react';
import { Card, Table, InputNumber, Button, Space, Spin, Alert, Progress, Tag } from 'antd';
import { api, IdleResource } from '../services/api';

export default function IdleResourcesPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(24);
  const [idleResources, setIdleResources] = useState<IdleResource[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getIdleResources(duration);
      setIdleResources(res.data.data);
      setError(null);
    } catch (err) {
      setError('Failed to load idle resources');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [duration]);

  const getUtilizationColor = (util: number) => {
    if (util < 0.2) return 'red';
    if (util < 0.5) return 'orange';
    return 'green';
  };

  const getSeverityTag = (idleCost: number) => {
    if (idleCost > 100) return <Tag color="red">High</Tag>;
    if (idleCost > 20) return <Tag color="orange">Medium</Tag>;
    return <Tag color="green">Low</Tag>;
  };

  const columns = [
    {
      title: 'Namespace',
      dataIndex: 'namespace',
      key: 'namespace',
      render: (text: string) => <code>{text}</code>,
    },
    {
      title: 'Resource Type',
      dataIndex: 'resourceType',
      key: 'resourceType',
    },
    {
      title: 'Requested',
      dataIndex: 'requested',
      key: 'requested',
      render: (val: number, record: IdleResource) =>
        `${val.toFixed(2)} ${record.resourceType === 'CPU' ? 'cores' : 'GB'}`,
    },
    {
      title: 'Used',
      dataIndex: 'used',
      key: 'used',
      render: (val: number, record: IdleResource) =>
        `${val.toFixed(2)} ${record.resourceType === 'CPU' ? 'cores' : 'GB'}`,
    },
    {
      title: 'Utilization',
      dataIndex: 'utilization',
      key: 'utilization',
      render: (val: number) => (
        <Progress
          percent={val * 100}
          size="small"
          status={val < 0.3 ? 'exception' : val < 0.6 ? 'normal' : 'success'}
          strokeColor={getUtilizationColor(val)}
        />
      ),
      sorter: (a: IdleResource, b: IdleResource) => a.utilization - b.utilization,
    },
    {
      title: 'Idle Amount',
      dataIndex: 'idleAmount',
      key: 'idleAmount',
      render: (val: number, record: IdleResource) =>
        `${val.toFixed(2)} ${record.resourceType === 'CPU' ? 'cores' : 'GB'}`,
    },
    {
      title: 'Monthly Idle Cost',
      dataIndex: 'idleCost',
      key: 'idleCost',
      render: (val: number) => <strong>${val.toFixed(2)}</strong>,
      sorter: (a: IdleResource, b: IdleResource) => a.idleCost - b.idleCost,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: 'Severity',
      dataIndex: 'idleCost',
      key: 'severity',
      render: (val: number) => getSeverityTag(val),
    },
  ];

  const totalIdleCost = idleResources.reduce((sum, ir) => sum + ir.idleCost, 0);
  const totalIdleCPU = idleResources
    .filter((ir) => ir.resourceType === 'CPU')
    .reduce((sum, ir) => sum + ir.idleAmount, 0);
  const totalIdleMemory = idleResources
    .filter((ir) => ir.resourceType === 'Memory')
    .reduce((sum, ir) => sum + ir.idleAmount, 0);

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
          <Card title="Idle Resource Summary" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', gap: 24, padding: '16px 0' }}>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
                  ${totalIdleCost.toFixed(2)}
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>Total Monthly Wasted Cost</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
                  {totalIdleCPU.toFixed(2)} cores
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>Idle CPU</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
                  {totalIdleMemory.toFixed(2)} GB
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>Idle Memory</div>
              </div>
            </div>
          </Card>

          <Card title="Idle Resource Details">
            <Table dataSource={idleResources} columns={columns} rowKey={(record) => `${record.namespace}-${record.resourceType}`} pagination={{ pageSize: 10 }} />
          </Card>
        </>
      )}
    </div>
  );
}
