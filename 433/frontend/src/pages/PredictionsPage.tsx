import { useState, useEffect } from 'react';
import { Card, Table, Spin, Alert, Select, InputNumber, Button, Space } from 'antd';
import { api, CostPrediction, NamespaceCost } from '../services/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export default function PredictionsPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [namespaces, setNamespaces] = useState<string[]>([]);
  const [selectedNamespace, setSelectedNamespace] = useState<string>('');
  const [duration, setDuration] = useState(720);
  const [prediction, setPrediction] = useState<CostPrediction | null>(null);

  useEffect(() => {
    loadNamespaces();
  }, []);

  const loadNamespaces = async () => {
    try {
      setLoading(true);
      const res = await api.getNamespaceCosts(24);
      const nsList = res.data.data.map((nc: NamespaceCost) => nc.namespace);
      setNamespaces(nsList);
      if (nsList.length > 0) {
        setSelectedNamespace(nsList[0]);
      }
      setError(null);
    } catch (err) {
      setError('Failed to load namespaces');
    } finally {
      setLoading(false);
    }
  };

  const loadPrediction = async () => {
    if (!selectedNamespace) return;
    try {
      setLoading(true);
      const res = await api.getCostPrediction(selectedNamespace, duration);
      setPrediction(res.data);
      setError(null);
    } catch (err) {
      setError('Failed to load prediction');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedNamespace) {
      loadPrediction();
    }
  }, [selectedNamespace, duration]);

  const chartData = prediction
    ? [
        { name: 'Current', cost: prediction.currentCost },
        { name: '30 Days', cost: prediction.predictedCost30D },
        { name: '90 Days', cost: prediction.predictedCost90D },
      ]
    : [];

  const columns = [
    {
      title: 'Metric',
      dataIndex: 'metric',
      key: 'metric',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: 'Value',
      dataIndex: 'value',
      key: 'value',
    },
  ];

  const tableData = prediction
    ? [
        { metric: 'Current Monthly Cost', value: `$${prediction.currentCost.toFixed(4)}` },
        { metric: 'Predicted Cost (30 Days)', value: `$${prediction.predictedCost30D.toFixed(4)}` },
        { metric: 'Predicted Cost (90 Days)', value: `$${prediction.predictedCost90D.toFixed(4)}` },
        {
          metric: 'Growth Rate',
          value: (
            <span style={{ color: prediction.growthRate > 0 ? '#ff4d4f' : '#52c41a' }}>
              {prediction.growthRate > 0 ? '+' : ''}
              {(prediction.growthRate * 100).toFixed(2)}%
            </span>
          ),
        },
      ]
    : [];

  return (
    <div>
      {error && (
        <Alert message="Error" description={error} type="error" showIcon style={{ marginBottom: 24 }} />
      )}

      <Card style={{ marginBottom: 24 }}>
        <Space>
          <span>Namespace:</span>
          <Select
            value={selectedNamespace}
            onChange={setSelectedNamespace}
            style={{ width: 200 }}
            options={namespaces.map((ns) => ({ label: ns, value: ns }))}
          />
          <span>Historical Data (hours):</span>
          <InputNumber min={168} max={2160} value={duration} onChange={setDuration} />
          <Button type="primary" onClick={loadPrediction} loading={loading}>
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
          <Card title="Cost Trend Prediction" style={{ marginBottom: 24 }}>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip formatter={(value: number) => `$${value.toFixed(4)}`} />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="cost"
                    stroke="#1890ff"
                    strokeWidth={2}
                    dot={{ r: 6 }}
                    name="Cost (USD)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card title="Prediction Details">
            <Table dataSource={tableData} columns={columns} rowKey="metric" pagination={false} />
          </Card>
        </>
      )}
    </div>
  );
}
