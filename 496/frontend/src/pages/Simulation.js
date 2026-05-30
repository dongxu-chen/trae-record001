import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Select,
  InputNumber,
  Button,
  Row,
  Col,
  Statistic,
  Space,
  Tag,
  Alert,
} from 'antd';
import {
  PlayCircleOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import { topologyAPI, simulationAPI } from '../services/api';
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

function Simulation() {
  const [form] = Form.useForm();
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [comparisonResult, setComparisonResult] = useState(null);

  useEffect(() => {
    loadServices();
  }, []);

  const loadServices = async () => {
    try {
      const res = await topologyAPI.getServices();
      setServices(res.data);
    } catch (error) {
      console.error('Failed to load services:', error);
    }
  };

  const runSimulation = async (values) => {
    try {
      setLoading(true);
      const request = {
        serviceId: values.serviceId,
        trafficMultiplier: values.trafficMultiplier,
        durationSeconds: values.durationSeconds,
        affectedApis: [],
        simulationType: 'OVERLOAD',
      };

      const res = await simulationAPI.compareSimulation(values.serviceId, request);
      setComparisonResult(res.data);
    } catch (error) {
      console.error('Simulation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatChartData = () => {
    if (!comparisonResult || comparisonResult.length < 2) return [];

    const [withoutLimit, withLimit] = comparisonResult;
    const metrics = withoutLimit.metrics || {};
    const firstApi = Object.keys(metrics)[0];
    if (!firstApi) return [];

    const withoutData = metrics[firstApi] || [];
    const withData = withLimit.metrics?.[firstApi] || [];

    return withoutData.map((item, index) => ({
      time: index + 1,
      无限流QPS: Math.round(item.qps),
      有限流QPS: Math.round(withData[index]?.qps || 0),
      无限流延迟: Math.round(item.latencyMs),
      有限流延迟: Math.round(withData[index]?.latencyMs || 0),
      无限流错误率: Math.round(item.errorRate * 100),
      有限流错误率: Math.round((withData[index]?.errorRate || 0) * 100),
    }));
  };

  const chartData = formatChartData();

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>过载保护模拟</h2>

      <Card title="模拟配置" style={{ marginBottom: 24 }}>
        <Form
          form={form}
          layout="horizontal"
          onFinish={runSimulation}
          initialValues={{
            trafficMultiplier: 3,
            durationSeconds: 30,
          }}
        >
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="目标服务"
                name="serviceId"
                rules={[{ required: true, message: '请选择服务' }]}
              >
                <Select placeholder="选择要模拟的服务">
                  {services.map(s => (
                    <Select.Option key={s.serviceId} value={s.serviceId}>
                      {s.serviceName}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                label="流量倍数"
                name="trafficMultiplier"
                rules={[{ required: true, message: '请输入流量倍数' }]}
              >
                <InputNumber min={1} max={10} step={0.5} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                label="模拟时长(秒)"
                name="durationSeconds"
                rules={[{ required: true, message: '请输入模拟时长' }]}
              >
                <InputNumber min={10} max={120} step={10} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<PlayCircleOutlined />}
                  loading={loading}
                  block
                >
                  开始模拟
                </Button>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>

      {comparisonResult && comparisonResult.length === 2 && (
        <>
          <Alert
            message="模拟完成"
            description="对比有限流保护和无限流保护情况下的系统表现"
            type="info"
            showIcon
            style={{ marginBottom: 24 }}
          />

          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card className="compare-card">
                <Statistic
                  title="无限流 - 错误率"
                  value={(comparisonResult[0].estimatedErrorRate * 100).toFixed(2)}
                  suffix="%"
                  valueStyle={{ color: '#ff4d4f' }}
                  prefix={<CloseCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card className="compare-card">
                <Statistic
                  title="有限流 - 错误率"
                  value={(comparisonResult[1].estimatedErrorRate * 100).toFixed(2)}
                  suffix="%"
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card className="compare-card">
                <Statistic
                  title="无限流 - 延迟增加"
                  value={((comparisonResult[0].estimatedLatencyIncrease - 1) * 100).toFixed(0)}
                  suffix="%"
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card className="compare-card">
                <Statistic
                  title="有限流 - 延迟增加"
                  value={((comparisonResult[1].estimatedLatencyIncrease - 1) * 100).toFixed(0)}
                  suffix="%"
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={12}>
              <Card title="QPS对比" className="compare-card">
                <div className="simulation-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" label={{ value: '时间(秒)', position: 'bottom' }} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="无限流QPS" stroke="#ff4d4f" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="有限流QPS" stroke="#52c41a" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Col>
            <Col span={12}>
              <Card title="延迟对比" className="compare-card">
                <div className="simulation-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" label={{ value: '时间(秒)', position: 'bottom' }} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="无限流延迟" stroke="#ff4d4f" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="有限流延迟" stroke="#52c41a" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Card title="错误率对比" className="compare-card">
                <div className="simulation-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" label={{ value: '时间(秒)', position: 'bottom' }} />
                      <YAxis label={{ value: '错误率(%)', angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="无限流错误率" stroke="#ff4d4f" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="有限流错误率" stroke="#52c41a" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </Col>
            <Col span={12}>
              <Card title="模拟结论" className="compare-card">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Alert
                    message="无限流保护"
                    description={comparisonResult[0].conclusion}
                    type="error"
                    showIcon
                  />
                  <Alert
                    message="有限流保护"
                    description={comparisonResult[1].conclusion}
                    type="success"
                    showIcon
                  />
                  {comparisonResult[1].droppedRequests > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <Tag color="blue">
                        <ThunderboltOutlined /> 限流拦截请求: {comparisonResult[1].droppedRequests} 次
                      </Tag>
                    </div>
                  )}
                </Space>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
}

export default Simulation;
