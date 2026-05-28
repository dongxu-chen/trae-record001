import { useState, useEffect } from 'react';
import { Card, Table, Spin, Alert, Button, Space, InputNumber, Tag, Progress } from 'antd';
import { api, ResourceContention } from '../services/api';

export default function ContentionPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duration, setDuration] = useState(24);
  const [contentions, setContentions] = useState<ResourceContention[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await api.getResourceContention(duration);
      setContentions(res.data.data);
      setError(null);
    } catch (err) {
      setError('Failed to load resource contention data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [duration]);

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'high':
        return 'red';
      case 'medium':
        return 'orange';
      default:
        return 'green';
    }
  };

  const getLevelText = (level: string) => {
    switch (level) {
      case 'high':
        return 'HIGH';
      case 'medium':
        return 'MEDIUM';
      default:
        return 'LOW';
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
      title: 'CPU Throttled Time (s)',
      dataIndex: 'cpuThrottledTime',
      key: 'cpuThrottledTime',
      render: (val: number) => val.toFixed(2),
      sorter: (a: ResourceContention, b: ResourceContention) =>
        a.cpuThrottledTime - b.cpuThrottledTime,
    },
    {
      title: 'OOM Events',
      dataIndex: 'memoryOOMCount',
      key: 'memoryOOMCount',
      sorter: (a: ResourceContention, b: ResourceContention) =>
        a.memoryOOMCount - b.memoryOOMCount,
    },
    {
      title: 'Contention Score',
      dataIndex: 'contentionScore',
      key: 'contentionScore',
      render: (val: number) => (
        <Progress
          percent={val * 100}
          size="small"
          status={val >= 0.5 ? 'exception' : val >= 0.2 ? 'normal' : 'success'}
        />
      ),
      sorter: (a: ResourceContention, b: ResourceContention) =>
        a.contentionScore - b.contentionScore,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: 'Contention Level',
      dataIndex: 'contentionLevel',
      key: 'contentionLevel',
      render: (val: string) => <Tag color={getLevelColor(val)}>{getLevelText(val)}</Tag>,
    },
    {
      title: 'Recommended CPU (cores)',
      dataIndex: 'recommendedCPU',
      key: 'recommendedCPU',
      render: (val: number) => val.toFixed(3),
    },
    {
      title: 'Recommended Memory (GB)',
      dataIndex: 'recommendedMemory',
      key: 'recommendedMemory',
      render: (val: number) => val.toFixed(3),
    },
  ];

  const highCount = contentions.filter((c) => c.contentionLevel === 'high').length;
  const mediumCount = contentions.filter((c) => c.contentionLevel === 'medium').length;
  const lowCount = contentions.filter((c) => c.contentionLevel === 'low').length;

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
          <Card title="Contention Summary" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', gap: 24, padding: '16px 0' }}>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
                  {highCount}
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>High Contention</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#faad14' }}>
                  {mediumCount}
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>Medium Contention</div>
              </div>
              <div style={{ flex: 1, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
                  {lowCount}
                </div>
                <div style={{ color: '#666', marginTop: 8 }}>Low Contention</div>
              </div>
            </div>
          </Card>

          <Card title="Resource Contention Details">
            <Table
              dataSource={contentions}
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
