import React, { useState, useEffect } from 'react';
import {
  Card, Button, Row, Col, Statistic, Select, Tag, message,
  Form, InputNumber, Switch, Steps, Descriptions, List, Alert,
  Table, Space, Progress,
} from 'antd';
import {
  ExperimentOutlined, PlayCircleOutlined, StopOutlined,
  SafetyCertificateOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { drillAPI, topologyAPI } from '../services/api';

function DrillPage() {
  const [loading, setLoading] = useState(false);
  const [services, setServices] = useState([]);
  const [selectedService, setSelectedService] = useState(null);
  const [drill, setDrill] = useState(null);
  const [completedDrills, setCompletedDrills] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [servicesRes, completedRes] = await Promise.all([
        topologyAPI.getServices(),
        drillAPI.getCompletedDrills(),
      ]);
      setServices(servicesRes.data);
      setCompletedDrills(completedRes.data);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const startDrill = async () => {
    if (!selectedService) {
      message.warning('请选择服务');
      return;
    }

    try {
      setLoading(true);
      const configRes = await drillAPI.getDefaultConfig(selectedService);
      const res = await drillAPI.startDrill(selectedService, configRes.data);
      setDrill(res.data);
      message.success('限流演练已启动');
      loadData();
    } catch (error) {
      message.error('启动失败');
    } finally {
      setLoading(false);
    }
  };

  const abortDrill = async (drillId) => {
    try {
      await drillAPI.abortDrill(drillId);
      message.info('演练已中止');
      loadData();
    } catch (error) {
      message.error('中止失败');
    }
  };

  const formatTimeSeriesData = (series, key) => {
    if (!series?.[key]) return [];
    return series[key].map((point, i) => ({
      time: i,
      value: Math.round(point.value * 100) / 100,
      upper: Math.round(point.upperBound * 100) / 100,
      lower: Math.round(point.lowerBound * 100) / 100,
    }));
  };

  const phaseColumns = [
    { title: '阶段', dataIndex: 'phaseName', key: 'phase',
      render: (v) => {
        const colorMap = { '流量爬坡': 'blue', '稳态运行': 'green', '达到限流阈值': 'orange', '超限流量': 'red', '流量回落': 'cyan' };
        return <Tag color={colorMap[v] || 'default'}>{v}</Tag>;
      }
    },
    { title: 'QPS', dataIndex: 'qps', key: 'qps', render: v => v?.toFixed(0) },
    { title: '平均延迟', dataIndex: 'avgLatencyMs', key: 'latency', render: v => `${v?.toFixed(1)}ms` },
    { title: '错误率', dataIndex: 'errorRate', key: 'error', render: v => `${(v * 100)?.toFixed(2)}%` },
    { title: '接受请求', dataIndex: 'acceptedRequests', key: 'accepted' },
    { title: '拒绝请求', dataIndex: 'rejectedRequests', key: 'rejected',
      render: v => v > 0 ? <Tag color="red">{v}</Tag> : 0
    },
    { title: '排队等待', dataIndex: 'queueWaitTimeMs', key: 'queue', render: v => `${v?.toFixed(1)}ms` },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>限流演练</h2>

      <Alert
        message="模拟达到限流阈值后的系统表现"
        description="通过五阶段演练（流量爬坡 → 稳态运行 → 达到限流阈值 → 超限流量 → 流量回落），验证限流配置在真实压力下的保护效果。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col span={8}>
            <Select
              style={{ width: '100%' }}
              placeholder="选择演练服务"
              onChange={setSelectedService}
              value={selectedService}
            >
              {services.map(s => (
                <Select.Option key={s.serviceId} value={s.serviceId}>
                  {s.serviceName}
                </Select.Option>
              ))}
            </Select>
          </Col>
          <Col span={6}>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              size="large"
              loading={loading}
              onClick={startDrill}
              disabled={!selectedService}
            >
              启动限流演练
            </Button>
          </Col>
        </Row>
      </Card>

      {drill && (
        <>
          <Card title="演练进度" style={{ marginBottom: 24 }}>
            <Steps current={drill.phases?.length || 0} status="finish">
              {(drill.phases || []).map((phase, i) => (
                <Steps.Step key={i} title={phase.phaseName}
                  description={`QPS: ${phase.qps?.toFixed(0)} | 延迟: ${phase.avgLatencyMs?.toFixed(0)}ms`} />
              ))}
            </Steps>
          </Card>

          {drill.summary && (
            <>
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col span={6}>
                  <Card>
                    <Statistic title="保护效果评分" value={drill.summary.protectionEffectiveness?.toFixed(1)} suffix="%"
                      valueStyle={{ color: drill.summary.protectionEffectiveness >= 70 ? '#52c41a' : '#faad14' }}
                      prefix={<SafetyCertificateOutlined />} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="总请求量" value={drill.summary.totalRequests} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="拒绝率" value={(drill.summary.rejectionRate * 100)?.toFixed(2)} suffix="%"
                      valueStyle={{ color: drill.summary.rejectionRate > 0.1 ? '#fa8c16' : '#52c41a' }} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="峰值延迟" value={drill.summary.peakLatencyMs?.toFixed(0)} suffix="ms"
                      valueStyle={{ color: drill.summary.peakLatencyMs > 500 ? '#ff4d4f' : '#333' }} />
                  </Card>
                </Col>
              </Row>

              <Card title="演练结论" style={{ marginBottom: 24 }}>
                <Alert
                  message={drill.summary.conclusion}
                  type={drill.summary.protectionEffectiveness >= 70 ? 'success' : 'warning'}
                  showIcon
                  description={
                    <List
                      size="small"
                      dataSource={drill.summary.observations || []}
                      renderItem={item => <List.Item style={{ fontSize: 13 }}>{item}</List.Item>}
                    />
                  }
                />
              </Card>
            </>
          )}

          <Card title="演练阶段详情" style={{ marginBottom: 24 }}>
            <Table columns={phaseColumns} dataSource={drill.phases} rowKey="phaseName" pagination={false} size="small" />
          </Card>

          {drill.metricsTimeSeries && (
            <Row gutter={16}>
              <Col span={8}>
                <Card title="QPS变化">
                  <div style={{ height: 250 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={formatTimeSeriesData(drill.metricsTimeSeries, 'qps')}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="time" />
                        <YAxis />
                        <Tooltip />
                        <ReferenceLine y={drill.config?.thresholdQps} stroke="#ff4d4f" strokeDasharray="5 5" label="限流阈值" />
                        <Line type="monotone" dataKey="value" stroke="#1890ff" strokeWidth={2} dot={false} name="QPS" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </Col>
              <Col span={8}>
                <Card title="延迟变化">
                  <div style={{ height: 250 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={formatTimeSeriesData(drill.metricsTimeSeries, 'latency')}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="time" />
                        <YAxis />
                        <Tooltip />
                        <Line type="monotone" dataKey="value" stroke="#722ed1" strokeWidth={2} dot={false} name="延迟(ms)" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </Col>
              <Col span={8}>
                <Card title="错误率变化">
                  <div style={{ height: 250 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={formatTimeSeriesData(drill.metricsTimeSeries, 'errorRate')}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="time" />
                        <YAxis />
                        <Tooltip />
                        <Line type="monotone" dataKey="value" stroke="#ff4d4f" strokeWidth={2} dot={false} name="错误率" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </Col>
            </Row>
          )}
        </>
      )}

      <Card title="历史演练" style={{ marginTop: 24 }}>
        {completedDrills.length > 0 ? (
          <List
            dataSource={completedDrills}
            renderItem={item => (
              <List.Item
                actions={[
                  <Tag color={item.status === 'COMPLETED' ? 'green' : 'orange'}>{item.status}</Tag>,
                  item.summary?.protectionEffectiveness != null && (
                    <Progress type="circle" size="small" percent={item.summary.protectionEffectiveness} />
                  ),
                ]}
              >
                <List.Item.Meta
                  title={`${item.serviceId} - ${item.drillId}`}
                  description={
                    item.summary ? `保护效果: ${item.summary.protectionEffectiveness?.toFixed(0)}% | 结论: ${item.summary.conclusion}` : '-'
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无演练记录</div>
        )}
      </Card>
    </div>
  );
}

export default DrillPage;
