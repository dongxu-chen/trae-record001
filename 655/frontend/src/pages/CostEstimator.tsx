import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  Table,
  Tag,
  message,
  Space,
  Statistic,
  Row,
  Col,
  Typography,
  Divider,
  Progress,
  Tooltip,
  Tabs,
  Slider,
  DatePicker,
  Radio,
  Descriptions,
} from 'antd';
import {
  CalculatorOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  GlobalOutlined,
  CloudServerOutlined,
  BarChartOutlined,
  RiseOutlined,
  FallOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { costAPI } from '../services/api';
import type { CostEstimateResult, CostConfig, CostBreakdownItem } from '../types';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

const CostEstimatorPage: React.FC = () => {
  const [providers, setProviders] = useState<string[]>([]);
  const [regions, setRegions] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('aws');
  const [selectedRegion, setSelectedRegion] = useState('us-east-1');
  const [estimateResult, setEstimateResult] = useState<CostEstimateResult | null>(null);
  const [compareResults, setCompareResults] = useState<CostEstimateResult[]>([]);
  const [monthlyResult, setMonthlyResult] = useState<CostEstimateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [estimateForm] = Form.useForm();
  const [monthlyForm] = Form.useForm();
  const [compareForm] = Form.useForm();

  const [dailyTraffic, setDailyTraffic] = useState<number[]>(
    Array.from({ length: 30 }, () => Math.random() * 5 + 2)
  );

  useEffect(() => {
    fetchProviders();
  }, []);

  useEffect(() => {
    if (selectedProvider) {
      fetchRegions(selectedProvider);
    }
  }, [selectedProvider]);

  const fetchProviders = async () => {
    try {
      const res = await costAPI.getProviders();
      setProviders(res.data.providers || []);
    } catch (err) {
      message.error('Failed to fetch providers');
    }
  };

  const fetchRegions = async (provider: string) => {
    try {
      const res = await costAPI.getRegions(provider);
      const regionList = res.data.regions || [];
      setRegions(regionList);
      if (regionList.length > 0) {
        setSelectedRegion(regionList[0]);
      }
    } catch (err) {
      message.error('Failed to fetch regions');
    }
  };

  const handleEstimate = async () => {
    try {
      const values = await estimateForm.validateFields();
      setLoading(true);

      const req = {
        ...values,
        cloudProvider: selectedProvider,
        region: selectedRegion,
        crossAZRatio: values.crossAZRatio / 100,
      };

      const res = await costAPI.estimateCost(req);
      setEstimateResult(res.data);
      message.success('Estimate generated');
    } catch (err) {
      message.error('Failed to generate estimate');
    } finally {
      setLoading(false);
    }
  };

  const handleMonthlyReport = async () => {
    try {
      const values = await monthlyForm.validateFields();
      setLoading(true);

      const req = {
        cloudProvider: selectedProvider,
        region: selectedRegion,
        crossAZRatio: values.crossAZRatio / 100,
        dailyTraffic: dailyTraffic,
      };

      const res = await costAPI.monthlyReport(req);
      setMonthlyResult(res.data);
      message.success('Monthly report generated');
    } catch (err) {
      message.error('Failed to generate monthly report');
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    try {
      const values = await compareForm.validateFields();
      setLoading(true);

      const req = {
        regions: values.regions || [],
        trafficGB: values.trafficGB,
        crossAZRatio: values.crossAZRatio / 100,
      };

      const res = await costAPI.compareProviders(req);
      setCompareResults(res.data.results || []);
      message.success('Comparison generated');
    } catch (err) {
      message.error('Failed to compare providers');
    } finally {
      setLoading(false);
    }
  };

  const totalTraffic = dailyTraffic.reduce((a, b) => a + b, 0);
  const avgTraffic = totalTraffic / dailyTraffic.length;

  const formatCurrency = (amount: number, currency: string) => {
    const symbols: Record<string, string> = {
      'USD': '$',
      'CNY': '¥',
      'EUR': '€',
      'GBP': '£',
    };
    return `${symbols[currency] || currency} ${amount.toFixed(4)}`;
  };

  const providerIcons: Record<string, React.ReactNode> = {
    'aws': <CloudServerOutlined />,
    'azure': <CloudServerOutlined />,
    'aliyun': <CloudServerOutlined />,
  };

  const compareColumns: ColumnsType<CostEstimateResult> = [
    {
      title: 'Provider',
      key: 'provider',
      width: 120,
      render: (_, record) => (
        <Space>
          {providerIcons[record.cloudProvider]}
          <Text strong>{record.cloudProvider.toUpperCase()}</Text>
        </Space>
      ),
    },
    {
      title: 'Region',
      dataIndex: 'region',
      key: 'region',
      width: 150,
    },
    {
      title: 'Total Cost',
      key: 'totalCost',
      width: 140,
      render: (_, record) => {
        const isLowest = compareResults.length > 0 && 
          record.totalCost === Math.min(...compareResults.map(r => r.totalCost));
        return (
          <Space>
            <Text strong style={{ 
              fontSize: 16, 
              color: isLowest ? '#52c41a' : 'inherit' 
            }}>
              {formatCurrency(record.totalCost, record.currency)}
            </Text>
            {isLowest && <Tag color="green">Lowest</Tag>}
          </Space>
        );
      },
      sorter: (a, b) => a.totalCost - b.totalCost,
    },
    {
      title: 'Intra-AZ',
      key: 'intraAZ',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text>{formatCurrency(record.intraAZCost, record.currency)}</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {record.intraAZTrafficGB.toFixed(1)} GB × ${record.costPerGBIntraAZ}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Cross-AZ',
      key: 'crossAZ',
      width: 120,
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text type="danger">{formatCurrency(record.crossAZCost, record.currency)}</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            {record.crossAZTrafficGB.toFixed(1)} GB × ${record.costPerGBCrossAZ}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Cost per GB',
      key: 'costPerGB',
      width: 120,
      render: (_, record) => {
        const effectiveRate = record.totalCost / (record.intraAZTrafficGB + record.crossAZTrafficGB);
        return <Text>${effectiveRate.toFixed(4)}/GB</Text>;
      },
    },
    {
      title: 'Est. Requests',
      dataIndex: 'estimatedRequests',
      key: 'requests',
      width: 120,
      render: (val) => `${(val / 1000000).toFixed(1)}M`,
    },
  ];

  const renderCostBreakdown = (breakdown?: CostBreakdownItem[]) => {
    if (!breakdown || breakdown.length === 0) return null;

    const intraAZItem = breakdown.find(b => b.name === 'Intra-AZ Traffic');
    const crossAZItem = breakdown.find(b => b.name === 'Cross-AZ Traffic');

    return (
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Text>
              <Tag color="green">Intra-AZ</Tag> Same Availability Zone
            </Text>
            <Text strong>{intraAZItem?.percentage?.toFixed(1)}%</Text>
          </Space>
          <Progress
            percent={intraAZItem?.percentage || 0}
            strokeColor="#52c41a"
            showInfo={false}
            size="small"
          />
        </Space>

        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Text>
              <Tag color="red">Cross-AZ</Tag> Across Availability Zones
            </Text>
            <Text strong>{crossAZItem?.percentage?.toFixed(1)}%</Text>
          </Space>
          <Progress
            percent={crossAZItem?.percentage || 0}
            strokeColor="#f5222d"
            showInfo={false}
            size="small"
          />
        </Space>

        <Divider />

        <Table
          dataSource={breakdown}
          rowKey="name"
          pagination={false}
          size="small"
          columns={[
            {
              title: 'Item',
              dataIndex: 'name',
              key: 'name',
            },
            {
              title: 'Description',
              dataIndex: 'description',
              key: 'description',
              render: (text) => <Text type="secondary">{text}</Text>,
            },
            {
              title: 'Amount',
              dataIndex: 'amount',
              key: 'amount',
              width: 120,
              align: 'right',
              render: (val, record) => (
                <Text strong>
                  {estimateResult ? formatCurrency(val, estimateResult.currency) : `$${val.toFixed(4)}`}
                </Text>
              ),
            },
            {
              title: '%',
              dataIndex: 'percentage',
              key: 'percentage',
              width: 80,
              align: 'right',
              render: (val) => val > 0 ? `${val.toFixed(1)}%` : '-',
            },
          ]}
        />
      </Space>
    );
  };

  const renderCostChart = () => (
    <div style={{ 
      background: '#fafafa', 
      padding: 20, 
      borderRadius: 8,
      marginTop: 16,
    }}>
      <Text type="secondary" style={{ fontSize: 12 }}>
        Daily Traffic (GB) - Last 30 Days
      </Text>
      <div style={{ 
        display: 'flex', 
        alignItems: 'flex-end', 
        height: 120, 
        gap: 3,
        marginTop: 8,
      }}>
        {dailyTraffic.map((val, idx) => (
          <Tooltip key={idx} title={`Day ${idx + 1}: ${val.toFixed(2)} GB`}>
            <div
              style={{
                flex: 1,
                background: idx === dailyTraffic.length - 1 ? '#1890ff' : 
                  val > avgTraffic ? '#f5222d' : '#52c41a',
                height: `${(val / Math.max(...dailyTraffic)) * 100}%`,
                borderRadius: 2,
                minHeight: 4,
                transition: 'height 0.3s',
              }}
            />
          </Tooltip>
        ))}
      </div>
      <Space style={{ marginTop: 8, width: '100%', justifyContent: 'space-between' }}>
        <Text type="secondary">Avg: {avgTraffic.toFixed(2)} GB/day</Text>
        <Text type="secondary">Total: {totalTraffic.toFixed(1)} GB</Text>
      </Space>
    </div>
  );

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card
        title={
          <Space>
            <CalculatorOutlined />
            <span>Traffic Cost Estimator</span>
          </Space>
        }
        extra={
          <Space>
            <Select
              value={selectedProvider}
              onChange={setSelectedProvider}
              style={{ width: 140 }}
              prefix={<GlobalOutlined />}
            >
              {providers.map(p => (
                <Option key={p} value={p}>
                  <Space>
                    {providerIcons[p]}
                    <span>{p.toUpperCase()}</span>
                  </Space>
                </Option>
              ))}
            </Select>
            <Select
              value={selectedRegion}
              onChange={setSelectedRegion}
              style={{ width: 160 }}
              disabled={regions.length === 0}
            >
              {regions.map(r => (
                <Option key={r} value={r}>{r}</Option>
              ))}
            </Select>
          </Space>
        }
      >
        <Tabs defaultActiveKey="quick">
          <TabPane
            tab={
              <Space>
                <CalculatorOutlined />
                Quick Estimate
              </Space>
            }
            key="quick"
          >
            <Row gutter={24}>
              <Col span={10}>
                <Card title="Configure" size="small">
                  <Form form={estimateForm} layout="vertical">
                    <Form.Item
                      name="trafficGB"
                      label={
                        <Space>
                          Total Traffic (GB)
                          <Tooltip title="Total estimated data transfer for the period">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                      initialValue={1000}
                      rules={[{ required: true }]}
                    >
                      <InputNumber
                        min={1}
                        style={{ width: '100%' }}
                        addonAfter="GB"
                      />
                    </Form.Item>

                    <Form.Item
                      name="crossAZRatio"
                      label={
                        <Space>
                          Cross-AZ Traffic (%)
                          <Tooltip title="Percentage of traffic crossing availability zones">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                      initialValue={30}
                      rules={[{ required: true }]}
                    >
                      <Slider
                        min={0}
                        max={100}
                        marks={{
                          0: '0%',
                          25: '25%',
                          50: '50%',
                          75: '75%',
                          100: '100%',
                        }}
                      />
                    </Form.Item>

                    <Form.Item
                      name="dateRange"
                      label="Time Period"
                    >
                      <RangePicker style={{ width: '100%' }} />
                    </Form.Item>

                    <Button
                      type="primary"
                      block
                      icon={<CalculatorOutlined />}
                      loading={loading}
                      onClick={handleEstimate}
                    >
                      Calculate Cost
                    </Button>
                  </Form>
                </Card>
              </Col>

              <Col span={14}>
                {estimateResult ? (
                  <Card size="small">
                    <Row gutter={16}>
                      <Col span={12}>
                        <Statistic
                          title={
                            <Space>
                              <GlobalOutlined />
                              Total Estimated Cost
                            </Space>
                          }
                          value={estimateResult.totalCost}
                          precision={4}
                          prefix={
                            estimateResult.currency === 'USD' ? '$' : 
                            estimateResult.currency === 'CNY' ? '¥' : ''
                          }
                          valueStyle={{ color: '#1890ff' }}
                        />
                        <Text type="secondary">
                          {selectedProvider.toUpperCase()} - {selectedRegion}
                        </Text>
                      </Col>
                      <Col span={6}>
                        <Statistic
                          title="Intra-AZ"
                          value={estimateResult.intraAZCost}
                          precision={4}
                          prefix="$"
                          valueStyle={{ color: '#52c41a', fontSize: 18 }}
                        />
                      </Col>
                      <Col span={6}>
                        <Statistic
                          title="Cross-AZ"
                          value={estimateResult.crossAZCost}
                          precision={4}
                          prefix="$"
                          valueStyle={{ color: '#f5222d', fontSize: 18 }}
                        />
                      </Col>
                    </Row>

                    <Divider />

                    <Descriptions column={3} size="small">
                      <Descriptions.Item label="Traffic (Intra-AZ)">
                        {estimateResult.intraAZTrafficGB.toFixed(2)} GB
                      </Descriptions.Item>
                      <Descriptions.Item label="Traffic (Cross-AZ)">
                        {estimateResult.crossAZTrafficGB.toFixed(2)} GB
                      </Descriptions.Item>
                      <Descriptions.Item label="Est. Requests">
                        {(estimateResult.estimatedRequests / 1000000).toFixed(2)}M
                      </Descriptions.Item>
                      <Descriptions.Item label="Rate (Intra-AZ)">
                        ${estimateResult.costPerGBIntraAZ}/GB
                      </Descriptions.Item>
                      <Descriptions.Item label="Rate (Cross-AZ)">
                        ${estimateResult.costPerGBCrossAZ}/GB
                      </Descriptions.Item>
                      <Descriptions.Item label="Avg Request Size">
                        {estimateResult.avgRequestSizeKB} KB
                      </Descriptions.Item>
                    </Descriptions>

                    <Divider />

                    <Title level={5}>Cost Breakdown</Title>
                    {renderCostBreakdown(estimateResult.breakdown)}
                  </Card>
                ) : (
                  <div style={{ 
                    textAlign: 'center', 
                    padding: 60, 
                    color: '#999',
                    background: '#fafafa',
                    borderRadius: 8,
                  }}>
                    <CalculatorOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                    <div>Configure parameters and click "Calculate Cost"</div>
                  </div>
                )}
              </Col>
            </Row>
          </TabPane>

          <TabPane
            tab={
              <Space>
                <BarChartOutlined />
                Monthly Report
              </Space>
            }
            key="monthly"
          >
            <Row gutter={24}>
              <Col span={10}>
                <Card title="Traffic Data" size="small">
                  <Form form={monthlyForm} layout="vertical">
                    <Form.Item
                      name="crossAZRatio"
                      label="Cross-AZ Traffic (%)"
                      initialValue={30}
                    >
                      <Slider min={0} max={100} />
                    </Form.Item>

                    {renderCostChart()}

                    <Space style={{ width: '100%', justifyContent: 'center' }}>
                      <Button
                        icon={<ReloadOutlined />}
                        onClick={() => setDailyTraffic(
                          Array.from({ length: 30 }, () => Math.random() * 5 + 2)
                        )}
                      >
                        Regenerate Data
                      </Button>
                      <Button
                        type="primary"
                        icon={<CalculatorOutlined />}
                        loading={loading}
                        onClick={handleMonthlyReport}
                      >
                        Generate Report
                      </Button>
                    </Space>
                  </Form>
                </Card>
              </Col>

              <Col span={14}>
                {monthlyResult ? (
                  <Card size="small">
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title="Daily Avg"
                          value={monthlyResult.breakdown?.find(b => b.name === 'Average Daily Cost')?.amount || 0}
                          precision={4}
                          prefix="$"
                          valueStyle={{ color: '#1890ff', fontSize: 18 }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="Monthly Total"
                          value={monthlyResult.totalCost}
                          precision={4}
                          prefix="$"
                          valueStyle={{ color: '#722ed1', fontSize: 20 }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="Projected Monthly"
                          value={monthlyResult.breakdown?.find(b => b.name === 'Projected Monthly Cost')?.amount || 0}
                          precision={4}
                          prefix="$"
                          valueStyle={{ color: '#fa8c16', fontSize: 18 }}
                          suffix={<RiseOutlined />}
                        />
                      </Col>
                    </Row>

                    <Divider />

                    {renderCostBreakdown(monthlyResult.breakdown)}
                  </Card>
                ) : (
                  <div style={{ 
                    textAlign: 'center', 
                    padding: 60, 
                    color: '#999',
                    background: '#fafafa',
                    borderRadius: 8,
                  }}>
                    <BarChartOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                    <div>Generate monthly cost report</div>
                  </div>
                )}
              </Col>
            </Row>
          </TabPane>

          <TabPane
            tab={
              <Space>
                <GlobalOutlined />
                Compare Regions
              </Space>
            }
            key="compare"
          >
            <Row gutter={24}>
              <Col span={10}>
                <Card title="Comparison Settings" size="small">
                  <Form form={compareForm} layout="vertical">
                    <Form.Item
                      name="trafficGB"
                      label="Monthly Traffic (GB)"
                      initialValue={1000}
                      rules={[{ required: true }]}
                    >
                      <InputNumber min={1} style={{ width: '100%' }} addonAfter="GB" />
                    </Form.Item>

                    <Form.Item
                      name="crossAZRatio"
                      label="Cross-AZ Traffic (%)"
                      initialValue={30}
                    >
                      <Slider min={0} max={100} />
                    </Form.Item>

                    <Form.Item
                      name="regions"
                      label="Select Regions"
                    >
                      <Select
                        mode="multiple"
                        placeholder="Select regions to compare"
                        style={{ width: '100%' }}
                      >
                        {regions.map(r => (
                          <Option key={r} value={r}>{r}</Option>
                        ))}
                      </Select>
                    </Form.Item>

                    <Button
                      type="primary"
                      block
                      icon={<GlobalOutlined />}
                      loading={loading}
                      onClick={handleCompare}
                    >
                      Compare Costs
                    </Button>
                  </Form>

                  <Divider />

                  <Card size="small" type="inner" title="Cost Factors">
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <div style={{ fontSize: 12 }}>
                        <Text type="secondary">Intra-AZ:</Text> Same data center - lower cost
                      </div>
                      <div style={{ fontSize: 12 }}>
                        <Text type="secondary">Cross-AZ:</Text> Different AZs - higher cost due to inter-AZ data transfer
                      </div>
                      <div style={{ fontSize: 12 }}>
                        <Text type="secondary">Tip:</Text> Reduce cross-AZ traffic to optimize costs
                      </div>
                    </Space>
                  </Card>
                </Card>
              </Col>

              <Col span={14}>
                {compareResults.length > 0 ? (
                  <Table
                    dataSource={compareResults}
                    rowKey="id"
                    columns={compareColumns}
                    pagination={false}
                    size="middle"
                  />
                ) : (
                  <div style={{ 
                    textAlign: 'center', 
                    padding: 80, 
                    color: '#999',
                    background: '#fafafa',
                    borderRadius: 8,
                  }}>
                    <GlobalOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                    <div>Select regions and click "Compare Costs"</div>
                  </div>
                )}
              </Col>
            </Row>
          </TabPane>
        </Tabs>
      </Card>
    </Space>
  );
};

export default CostEstimatorPage;
