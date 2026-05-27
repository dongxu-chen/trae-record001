import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  message,
  Input,
  Select,
  Modal,
  Form,
  DatePicker,
  Progress,
  Tabs,
  Tooltip,
  Divider,
  Badge,
  Slider,
  Alert,
  Descriptions,
} from 'antd';
import {
  ExperimentOutlined,
  PlusOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  EditOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { ABTestConfig, ABTestMetrics, ABTestAssignment, ModelInfo } from '@/types';
import {
  createABTest,
  listABTests,
  updateABTest,
  assignABTestGroup,
  getABTestMetrics,
  getModels,
} from '@/services/api';
import dayjs from 'dayjs';

const { TabPane } = Tabs;
const { RangePicker } = DatePicker;
const { Option } = Select;

const ABTesting: React.FC = () => {
  const [tests, setTests] = useState<ABTestConfig[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTest, setSelectedTest] = useState<ABTestConfig | null>(null);
  const [testMetrics, setTestMetrics] = useState<ABTestMetrics | null>(null);
  const [sessionId, setSessionId] = useState('');
  const [assignmentResult, setAssignmentResult] = useState<ABTestAssignment | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [testsRes, modelsRes] = await Promise.all([
        listABTests(),
        getModels(),
      ]);
      setTests(testsRes.data);
      setModels(modelsRes.data);
    } catch (err: any) {
      message.error('加载数据失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const loadTestMetrics = async (testId: string) => {
    try {
      setLoading(true);
      const res = await getABTestMetrics(testId);
      setTestMetrics(res.data);
    } catch (err: any) {
      message.error('加载测试指标失败：' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTest = async (values: any) => {
    try {
      const testData = {
        ...values,
        start_date: values.date_range?.[0]?.toISOString(),
        end_date: values.date_range?.[1]?.toISOString(),
      };
      delete testData.date_range;
      
      await createABTest(testData);
      message.success('A/B测试创建成功');
      setShowCreateModal(false);
      form.resetFields();
      loadData();
    } catch (err: any) {
      message.error('创建失败：' + (err.response?.data?.detail || err.message));
    }
  };

  const handleUpdateTestStatus = async (testId: string, status: string) => {
    try {
      const test = tests.find(t => t.test_id === testId);
      if (test) {
        await updateABTest(testId, { ...test, status });
        message.success(`测试状态已更新为: ${status}`);
        loadData();
      }
    } catch (err: any) {
      message.error('更新失败：' + (err.response?.data?.detail || err.message));
    }
  };

  const handleAssignGroup = async () => {
    if (!selectedTest || !sessionId) {
      message.warning('请选择测试并输入Session ID');
      return;
    }

    try {
      const res = await assignABTestGroup(selectedTest.test_id, sessionId);
      setAssignmentResult(res.data);
      message.success(`已分配到 ${res.data.group === 'treatment' ? '实验组' : '对照组'}，使用模型: ${res.data.model_name}`);
    } catch (err: any) {
      message.error('分配失败：' + (err.response?.data?.detail || err.message));
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'default',
      running: 'processing',
      paused: 'warning',
      completed: 'success',
    };
    return colors[status] || 'default';
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      draft: '草稿',
      running: '运行中',
      paused: '已暂停',
      completed: '已完成',
    };
    return labels[status] || status;
  };

  const getStatusActions = (test: ABTestConfig) => {
    switch (test.status) {
      case 'draft':
        return (
          <Button
            type="primary"
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleUpdateTestStatus(test.test_id, 'running')}
          >
            启动测试
          </Button>
        );
      case 'running':
        return (
          <Button
            size="small"
            icon={<PauseCircleOutlined />}
            onClick={() => handleUpdateTestStatus(test.test_id, 'paused')}
          >
            暂停测试
          </Button>
        );
      case 'paused':
        return (
          <Space>
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleUpdateTestStatus(test.test_id, 'running')}
            >
              继续
            </Button>
            <Button
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleUpdateTestStatus(test.test_id, 'completed')}
            >
              完成
            </Button>
          </Space>
        );
      default:
        return null;
    }
  };

  const getComparisonChartOption = () => {
    if (!testMetrics) return {};

    const metrics = ['avg_recall', 'avg_precision', 'avg_f1', 'avg_ndcg', 'avg_hit_rate'];
    const metricLabels = ['召回率', '精确率', 'F1值', 'NDCG', '命中率'];

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          let result = `${params[0].axisValue}<br/>`;
          params.forEach((item: any) => {
            const value = (item.value * 100).toFixed(2);
            result += `${item.marker} ${item.seriesName}: ${value}%<br/>`;
          });
          return result;
        },
      },
      legend: {
        data: ['对照组', '实验组'],
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: metricLabels,
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (value: number) => `${(value * 100).toFixed(0)}%`,
        },
      },
      series: [
        {
          name: '对照组',
          type: 'bar',
          data: metrics.map(m => testMetrics.control[m] || 0),
          itemStyle: {
            color: '#1677ff',
          },
        },
        {
          name: '实验组',
          type: 'bar',
          data: metrics.map(m => testMetrics.treatment[m] || 0),
          itemStyle: {
            color: '#52c41a',
          },
        },
      ],
    };
  };

  const getLiftChartOption = () => {
    if (!testMetrics) return {};

    const metrics = ['avg_recall', 'avg_precision', 'avg_f1', 'avg_ndcg', 'avg_hit_rate'];
    const metricLabels = ['召回率', '精确率', 'F1值', 'NDCG', '命中率'];

    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          return `${params[0].axisValue}<br/>${params[0].marker} 提升: ${params[0].value.toFixed(2)}%`;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: metricLabels,
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: '{value}%',
        },
      },
      series: [
        {
          name: '提升率',
          type: 'bar',
          data: metrics.map(m => testMetrics.lift[m] || 0),
          itemStyle: {
            color: (params: any) => {
              return params.value >= 0 ? '#52c41a' : '#ff4d4f';
            },
          },
          markLine: {
            data: [{ yAxis: 0, lineStyle: { color: '#999' } }],
          },
        },
      ],
    };
  };

  const columns = [
    {
      title: '测试名称',
      dataIndex: 'test_name',
      key: 'test_name',
      width: 150,
    },
    {
      title: '对照组模型',
      dataIndex: 'control_model',
      key: 'control_model',
      width: 120,
      render: (model: string) => <Tag color="blue">{model}</Tag>,
    },
    {
      title: '实验组模型',
      dataIndex: 'treatment_model',
      key: 'treatment_model',
      width: 120,
      render: (model: string) => <Tag color="green">{model}</Tag>,
    },
    {
      title: '流量分配',
      dataIndex: 'traffic_split',
      key: 'traffic_split',
      width: 120,
      render: (split: number) => (
        <Tooltip title={`实验组: ${(split * 100).toFixed(0)}%, 对照组: ${((1 - split) * 100).toFixed(0)}%`}>
          <Progress
            percent={split * 100}
            size="small"
            strokeColor="#52c41a"
          />
        </Tooltip>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{getStatusLabel(status)}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: ABTestConfig) => (
        <Space>
          <Button
            size="small"
            icon={<LineChartOutlined />}
            onClick={() => {
              setSelectedTest(record);
              loadTestMetrics(record.test_id);
            }}
          >
            查看结果
          </Button>
          {getStatusActions(record)}
        </Space>
      ),
    },
  ];

  const runningTests = tests.filter(t => t.status === 'running').length;
  const draftTests = tests.filter(t => t.status === 'draft').length;
  const completedTests = tests.filter(t => t.status === 'completed').length;

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>
        <ExperimentOutlined style={{ marginRight: 8, color: '#722ed1' }} />
        A/B测试评估
      </h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><ExperimentOutlined /> 测试总数</span>}
              value={tests.length}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><PlayCircleOutlined /> 运行中</span>}
              value={runningTests}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><EditOutlined /> 草稿</span>}
              value={draftTests}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card className="metric-card">
            <Statistic
              title={<span><CheckCircleOutlined /> 已完成</span>}
              value={completedTests}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadData}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setShowCreateModal(true)}
            >
              创建测试
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={tests}
          rowKey="test_id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {selectedTest && (
        <Card
          title={`测试结果分析 - ${selectedTest.test_name}`}
          style={{ marginTop: 24 }}
          extra={
            <Button
              icon={<CloseCircleOutlined />}
              onClick={() => {
                setSelectedTest(null);
                setTestMetrics(null);
              }}
            >
              关闭
            </Button>
          }
        >
          {testMetrics ? (
            <Tabs defaultActiveKey="comparison">
              <TabPane tab="指标对比" key="comparison">
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Card title="指标对比柱状图">
                      <ReactECharts
                        option={getComparisonChartOption()}
                        style={{ height: 350 }}
                      />
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="提升率分析">
                      <ReactECharts
                        option={getLiftChartOption()}
                        style={{ height: 350 }}
                      />
                    </Card>
                  </Col>
                </Row>

                <Divider />

                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="样本量 - 对照组">
                    <Badge count={testMetrics.sample_size.control} style={{ backgroundColor: '#1677ff' }} />
                  </Descriptions.Item>
                  <Descriptions.Item label="样本量 - 实验组">
                    <Badge count={testMetrics.sample_size.treatment} style={{ backgroundColor: '#52c41a' }} />
                  </Descriptions.Item>
                </Descriptions>

                <Divider />

                <Row gutter={[16, 16]}>
                  {['avg_recall', 'avg_precision', 'avg_f1', 'avg_ndcg', 'avg_hit_rate'].map(metric => {
                    const labels: Record<string, string> = {
                      avg_recall: '召回率',
                      avg_precision: '精确率',
                      avg_f1: 'F1值',
                      avg_ndcg: 'NDCG',
                      avg_hit_rate: '命中率',
                    };
                    const lift = testMetrics.lift[metric] || 0;
                    const isPositive = lift >= 0;
                    
                    return (
                      <Col span={8} key={metric}>
                        <Card size="small">
                          <Statistic
                            title={labels[metric]}
                            value={lift}
                            precision={2}
                            suffix="%"
                            valueStyle={{ color: isPositive ? '#52c41a' : '#ff4d4f' }}
                            prefix={isPositive ? '↑' : '↓'}
                          />
                          <div style={{ fontSize: 12, color: '#999', marginTop: 8 }}>
                            对照组: {(testMetrics.control[metric] * 100).toFixed(2)}% → 
                            实验组: {(testMetrics.treatment[metric] * 100).toFixed(2)}%
                          </div>
                        </Card>
                      </Col>
                    );
                  })}
                </Row>
              </TabPane>

              <TabPane tab="流量分配" key="assignment">
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Card title="流量分配模拟器">
                      <Form layout="vertical">
                        <Form.Item label="Session ID">
                          <Input
                            placeholder="输入Session ID"
                            value={sessionId}
                            onChange={(e) => setSessionId(e.target.value)}
                          />
                        </Form.Item>
                        <Button
                          type="primary"
                          icon={<ThunderboltOutlined />}
                          onClick={handleAssignGroup}
                          disabled={!sessionId}
                        >
                          分配流量
                        </Button>
                      </Form>

                      {assignmentResult && (
                        <div style={{ marginTop: 16 }}>
                          <Alert
                            message={`已分配到 ${assignmentResult.group === 'treatment' ? '实验组' : '对照组'}`}
                            description={`使用模型: ${assignmentResult.model_name}`}
                            type={assignmentResult.group === 'treatment' ? 'success' : 'info'}
                            showIcon
                          />
                        </div>
                      )}
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="测试配置">
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="测试ID">{selectedTest.test_id}</Descriptions.Item>
                        <Descriptions.Item label="对照组">{selectedTest.control_model}</Descriptions.Item>
                        <Descriptions.Item label="实验组">{selectedTest.treatment_model}</Descriptions.Item>
                        <Descriptions.Item label="流量分配">
                          实验组: {(selectedTest.traffic_split * 100).toFixed(0)}%
                        </Descriptions.Item>
                        <Descriptions.Item label="状态">{getStatusLabel(selectedTest.status)}</Descriptions.Item>
                      </Descriptions>
                    </Card>
                  </Col>
                </Row>
              </TabPane>
            </Tabs>
          ) : (
            <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
              正在加载测试结果...
            </div>
          )}
        </Card>
      )}

      <Modal
        title="创建A/B测试"
        open={showCreateModal}
        onCancel={() => setShowCreateModal(false)}
        footer={null}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreateTest}>
          <Form.Item
            name="test_name"
            label="测试名称"
            rules={[{ required: true, message: '请输入测试名称' }]}
          >
            <Input placeholder="例如: BM25 vs Dense" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="control_model"
                label="对照组模型"
                rules={[{ required: true, message: '请选择对照组模型' }]}
              >
                <Select placeholder="选择模型">
                  {models.map(m => (
                    <Option key={m.model_name} value={m.model_name}>
                      {m.model_name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="treatment_model"
                label="实验组模型"
                rules={[{ required: true, message: '请选择实验组模型' }]}
              >
                <Select placeholder="选择模型">
                  {models.map(m => (
                    <Option key={m.model_name} value={m.model_name}>
                      {m.model_name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="traffic_split"
            label="实验组流量比例"
            rules={[{ required: true, message: '请设置流量比例' }]}
          >
            <Slider
              min={10}
              max={90}
              marks={{
                10: '10%',
                30: '30%',
                50: '50%',
                70: '70%',
                90: '90%',
              }}
            />
          </Form.Item>
          <Form.Item name="date_range" label="测试周期">
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="description" label="测试描述">
            <Input.TextArea rows={3} placeholder="描述测试目的和假设" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建测试
              </Button>
              <Button onClick={() => setShowCreateModal(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ABTesting;
