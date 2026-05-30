import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Button,
  Modal,
  message,
  Space,
  Row,
  Col,
  Statistic,
  Progress,
  Collapse,
  List,
  Tooltip,
} from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import { rateLimitAPI, topologyAPI, predictionAPI } from '../services/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';

function Recommendations() {
  const [loading, setLoading] = useState(true);
  const [services, setServices] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [selectedService, setSelectedService] = useState(null);
  const [selectedRecommendation, setSelectedRecommendation] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [applyLoading, setApplyLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [servicesRes, recommendationsRes] = await Promise.all([
        topologyAPI.getServices(),
        rateLimitAPI.getAllRecommendations(),
      ]);
      setServices(servicesRes.data);
      setRecommendations(recommendationsRes.data);
    } catch (error) {
      console.error('Failed to load recommendations:', error);
      message.error('加载推荐数据失败');
    } finally {
      setLoading(false);
    }
  };

  const loadPrediction = async (serviceId) => {
    try {
      const res = await predictionAPI.getTrafficPrediction(serviceId, 60);
      setPrediction(res.data);
    } catch (error) {
      console.error('Failed to load prediction:', error);
    }
  };

  const viewDetail = async (recommendation, service) => {
    setSelectedRecommendation(recommendation);
    setSelectedService(service);
    setDetailModalVisible(true);
    await loadPrediction(service.serviceId);
  };

  const applyRecommendation = async (recommendation) => {
    try {
      setApplyLoading(true);
      await rateLimitAPI.applyRecommendation(recommendation);
      message.success('限流配置已成功应用');
      setDetailModalVisible(false);
    } catch (error) {
      console.error('Failed to apply recommendation:', error);
      message.error('应用配置失败');
    } finally {
      setApplyLoading(false);
    }
  };

  const getRiskColor = (risk) => {
    if (risk < 0.3) return '#52c41a';
    if (risk < 0.6) return '#faad14';
    return '#ff4d4f';
  };

  const getRiskLevel = (risk) => {
    if (risk < 0.3) return '低风险';
    if (risk < 0.6) return '中风险';
    return '高风险';
  };

  const getWaterLevelColor = (current, limit) => {
    const ratio = current / limit;
    if (ratio < 0.5) return '#52c41a';
    if (ratio < 0.8) return '#faad14';
    return '#ff4d4f';
  };

  const formatPredictionData = () => {
    if (!prediction) return [];

    const historical = (prediction.historicalData || []).slice(-24).map(p => ({
      time: new Date(p.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      value: Math.round(p.value),
      type: '历史流量',
    }));

    const predicted = (prediction.predictedData || []).map(p => ({
      time: new Date(p.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      value: Math.round(p.value),
      upper: Math.round(p.upperBound),
      lower: Math.round(p.lowerBound),
      type: '预测流量',
    }));

    return [...historical, ...predicted];
  };

  const columns = [
    {
      title: '服务名称',
      dataIndex: 'serviceName',
      key: 'serviceName',
      render: (_, record) => {
        const rec = recommendations.find(r => r.serviceId === record.serviceId);
        const risk = rec?.riskScore || 0;
        return (
          <Space>
            <span>{record.serviceName}</span>
            <Tag color={getRiskColor(risk)}>
              {getRiskLevel(risk)}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: '当前QPS/推荐QPS',
      key: 'qps',
      render: (_, record) => {
        const rec = recommendations.find(r => r.serviceId === record.serviceId);
        const current = record.metrics?.avgQps || 0;
        const recommended = rec?.recommendedServiceRule?.qpsThreshold || 0;
        const ratio = current / recommended;

        return (
          <Tooltip title={`当前QPS: ${current.toFixed(0)}, 推荐QPS: ${recommended}`}>
            <div style={{ width: 200 }}>
              <Progress
                percent={(ratio * 100).toFixed(0)}
                size="small"
                strokeColor={getWaterLevelColor(current, recommended)}
                format={() => `${current.toFixed(0)} / ${recommended}`}
              />
            </div>
          </Tooltip>
        );
      },
    },
    {
      title: '突发容量',
      key: 'burst',
      render: (_, record) => {
        const rec = recommendations.find(r => r.serviceId === record.serviceId);
        return rec?.recommendedServiceRule?.burstCapacity || '-';
      },
    },
    {
      title: '置信度',
      key: 'confidence',
      render: (_, record) => {
        const rec = recommendations.find(r => r.serviceId === record.serviceId);
        const conf = rec?.recommendedServiceRule?.confidenceScore || 0;
        return (
          <Progress
            type="circle"
            size="small"
            percent={(conf * 100).toFixed(0)}
          />
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => {
        const rec = recommendations.find(r => r.serviceId === record.serviceId);
        return (
          <Button
            type="primary"
            size="small"
            icon={<BulbOutlined />}
            onClick={() => viewDetail(rec, record)}
          >
            查看详情
          </Button>
        );
      },
    },
  ];

  const apiColumns = [
    { title: 'API路径', dataIndex: 'path', key: 'path' },
    { title: '方法', dataIndex: 'method', key: 'method',
      render: v => <Tag color={v === 'GET' ? 'green' : 'blue'}>{v}</Tag>
    },
    { title: '推荐QPS', key: 'qps',
      render: (_, record) => {
        const rec = selectedRecommendation?.recommendedApiRules?.[record.key];
        return rec?.qpsThreshold || '-';
      }
    },
    { title: '突发容量', key: 'burst',
      render: (_, record) => {
        const rec = selectedRecommendation?.recommendedApiRules?.[record.key];
        return rec?.burstCapacity || '-';
      }
    },
    { title: '限流类型', key: 'type',
      render: (_, record) => {
        const rec = selectedRecommendation?.recommendedApiRules?.[record.key];
        return rec?.limitType || '-';
      }
    },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>限流配置推荐</h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="待处理推荐"
              value={recommendations.length}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="高风险服务"
              value={recommendations.filter(r => r.riskScore > 0.6).length}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="中风险服务"
              value={recommendations.filter(r => r.riskScore >= 0.3 && r.riskScore <= 0.6).length}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="低风险服务"
              value={recommendations.filter(r => r.riskScore < 0.3).length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="限流水位监控" style={{ marginBottom: 24 }}>
        <Row gutter={[16, 16]}>
          {services.slice(0, 6).map(service => {
            const rec = recommendations.find(r => r.serviceId === service.serviceId);
            const current = service.metrics?.avgQps || 0;
            const limit = rec?.recommendedServiceRule?.qpsThreshold || current * 1.5;
            const ratio = current / limit;

            return (
              <Col span={8} key={service.serviceId}>
                <div className="water-level-item">
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontWeight: 'bold' }}>{service.serviceName}</span>
                    <span style={{ color: getWaterLevelColor(current, limit) }}>
                      {(ratio * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="water-level-bar">
                    <div
                      className="water-level-fill"
                      style={{
                        width: `${Math.min(100, ratio * 100)}%`,
                        backgroundColor: getWaterLevelColor(current, limit),
                      }}
                    />
                    <span className="water-level-label">
                      {current.toFixed(0)} / {limit} QPS
                    </span>
                  </div>
                </div>
              </Col>
            );
          })}
        </Row>
      </Card>

      <Card title="推荐列表" loading={loading}>
        <Table
          columns={columns}
          dataSource={services}
          rowKey="serviceId"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={`限流推荐详情 - ${selectedService?.serviceName}`}
        visible={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={1000}
        footer={[
          <Button key="cancel" onClick={() => setDetailModalVisible(false)}>
            取消
          </Button>,
          <Button
            key="apply"
            type="primary"
            className="apply-button"
            loading={applyLoading}
            onClick={() => applyRecommendation(selectedRecommendation)}
          >
            一键应用配置
          </Button>,
        ]}
      >
        {selectedRecommendation && (
          <div>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="推荐QPS阈值"
                    value={selectedRecommendation.recommendedServiceRule?.qpsThreshold}
                    suffix="QPS"
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <Statistic
                    title="突发容量"
                    value={selectedRecommendation.recommendedServiceRule?.burstCapacity}
                    valueStyle={{ color: '#722ed1' }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small">
                  <div className="risk-indicator">
                    <span>风险等级:</span>
                    <div className="risk-bar">
                      <div
                        className="risk-fill"
                        style={{
                          width: `${(selectedRecommendation.riskScore * 100)}%`,
                          backgroundColor: getRiskColor(selectedRecommendation.riskScore),
                        }}
                      />
                    </div>
                    <Tag color={getRiskColor(selectedRecommendation.riskScore)}>
                      {getRiskLevel(selectedRecommendation.riskScore)}
                    </Tag>
                  </div>
                </Card>
              </Col>
            </Row>

            <Collapse defaultActiveKey={['1', '2']}>
              <Collapse.Panel header="算法推理" key="1">
                <div className="reasoning-list">
                  <List
                    dataSource={selectedRecommendation.reasoning}
                    renderItem={item => <List.Item>💡 {item}</List.Item>}
                  />
                </div>
              </Collapse.Panel>

              <Collapse.Panel header="流量预测" key="2">
                <div style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={formatPredictionData()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <RechartsTooltip />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke="#1890ff"
                        fill="#1890ff"
                        fillOpacity={0.3}
                        name="QPS"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                {prediction && (
                  <div style={{ marginTop: 16 }}>
                    <Tag>预测置信度: {(prediction.predictionConfidence * 100).toFixed(1)}%</Tag>
                    <Tag>预测时长: {prediction.predictionHorizonMinutes}分钟</Tag>
                  </div>
                )}
              </Collapse.Panel>

              <Collapse.Panel header="接口级限流配置" key="3">
                <Table
                  columns={apiColumns}
                  dataSource={selectedService?.endpoints ?
                    Object.entries(selectedService.endpoints).map(([key, val]) => ({
                      key,
                      ...val,
                    })) : []
                  }
                  pagination={false}
                  size="small"
                />
              </Collapse.Panel>
            </Collapse>
          </div>
        )}
      </Modal>
    </div>
  );
}

export default Recommendations;
