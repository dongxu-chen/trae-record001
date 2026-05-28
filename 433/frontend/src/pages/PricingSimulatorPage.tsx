import { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  InputNumber,
  Typography,
  Row,
  Col,
  Statistic,
  Tag,
} from 'antd';
import { api, PriceComparison } from '../services/api';
import { DollarOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';

const { Title } = Typography;

export default function PricingSimulatorPage() {
  const [cpuCores, setCpuCores] = useState(10);
  const [memoryGB, setMemoryGB] = useState(32);
  const [comparison, setComparison] = useState<PriceComparison[]>([]);
  const [loading, setLoading] = useState(false);

  const loadComparison = async () => {
    try {
      setLoading(true);
      const res = await api.comparePricing(cpuCores, memoryGB);
      setComparison(res.data.data);
    } catch (err) {
      console.error('Failed to load pricing comparison');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Scenario',
      dataIndex: 'scenario',
      key: 'scenario',
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: 'Monthly CPU Cost',
      dataIndex: 'monthlyCpuCost',
      key: 'monthlyCpuCost',
      render: (val: number) => `$${val.toFixed(2)}`,
    },
    {
      title: 'Monthly Memory Cost',
      dataIndex: 'monthlyMemoryCost',
      key: 'monthlyMemoryCost',
      render: (val: number) => `$${val.toFixed(2)}`,
    },
    {
      title: 'Total Monthly Cost',
      dataIndex: 'totalMonthlyCost',
      key: 'totalMonthlyCost',
      render: (val: number, record: PriceComparison) => {
        const onDemandCost = comparison.find((c) => c.scenario === 'On-Demand')?.totalMonthlyCost || 0;
        const isCheaper = record.scenario !== 'On-Demand' && val < onDemandCost;
        return (
          <Space>
            <strong>${val.toFixed(2)}</strong>
            {isCheaper && record.savingsPercent && (
              <Tag color="green">Save {record.savingsPercent.toFixed(1)}%</Tag>
            )}
          </Space>
        );
      },
      sorter: (a: PriceComparison, b: PriceComparison) => a.totalMonthlyCost - b.totalMonthlyCost,
    },
    {
      title: 'Upfront Cost',
      dataIndex: 'upfrontCost',
      key: 'upfrontCost',
      render: (val?: number) => (val !== undefined ? `$${val.toFixed(2)}` : '-'),
    },
    {
      title: 'Annual Savings',
      dataIndex: 'annualSavings',
      key: 'annualSavings',
      render: (val?: number) => (val !== undefined ? `$${val.toFixed(2)}` : '-'),
    },
    {
      title: 'Break-Even Months',
      dataIndex: 'breakEvenMonths',
      key: 'breakEvenMonths',
      render: (val?: number) =>
        val !== undefined ? `${val.toFixed(1)} months` : '-',
    },
  ];

  const cheapestOption = comparison.length > 0 ? [...comparison].sort((a, b) => a.totalMonthlyCost - b.totalMonthlyCost)[0] : null;
  const onDemandOption = comparison.find((c) => c.scenario === 'On-Demand');
  const savings = onDemandOption && cheapestOption && cheapestOption.scenario !== 'On-Demand'
    ? onDemandOption.totalMonthlyCost - cheapestOption.totalMonthlyCost
    : 0;

  return (
    <div>
      <Card title="Pricing Simulator" style={{ marginBottom: 24 }}>
        <Space wrap>
          <div>
            <label style={{ marginRight: 8 }}>CPU Cores:</label>
            <InputNumber min={0.1} max={1000} step={0.5} value={cpuCores} onChange={setCpuCores} />
          </div>
          <div>
            <label style={{ marginRight: 8 }}>Memory (GB):</label>
            <InputNumber min={0.1} max={10000} step={1} value={memoryGB} onChange={setMemoryGB} />
          </div>
          <Button type="primary" onClick={loadComparison} loading={loading}>
            Calculate
          </Button>
        </Space>
      </Card>

      {comparison.length > 0 && (
        <>
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Best Option"
                  value={cheapestOption?.scenario}
                  prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Monthly Cost"
                  value={cheapestOption?.totalMonthlyCost || 0}
                  precision={2}
                  prefix={<DollarOutlined />}
                />
              </Card>
            </Col>
            <Col span={8}>
              <Card>
                <Statistic
                  title="Monthly Savings vs On-Demand"
                  value={savings}
                  precision={2}
                  prefix={<DollarOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
          </Row>

          <Card title="Price Comparison">
            <Table
              dataSource={comparison}
              columns={columns}
              rowKey="scenario"
              pagination={false}
            />
          </Card>

          <Card title="Recommendations" style={{ marginTop: 24 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {comparison.find((c) => c.scenario === 'Reserved Instances') && (
                <Alert
                  message="Reserved Instances"
                  description={`Save money with long-term commitment. Break-even in ${comparison.find((c) => c.scenario === 'Reserved Instances')?.breakEvenMonths?.toFixed(1)} months. Best for stable, long-running workloads.`}
                  type="info"
                  showIcon
                  icon={<ClockCircleOutlined />}
                />
              )}
              {comparison.find((c) => c.scenario === 'Spot Instances') && (
                <Alert
                  message="Spot Instances"
                  description="Highest savings but with interruption risk. Best for fault-tolerant, stateless, or batch processing workloads."
                  type="warning"
                  showIcon
                />
              )}
            </Space>
          </Card>
        </>
      )}
    </div>
  );
}
