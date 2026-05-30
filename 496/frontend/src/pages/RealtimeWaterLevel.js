import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Tag,
  Badge,
  List,
  Alert,
  Space,
  Button,
  Statistic,
  Tooltip,
  Modal,
  Form,
  InputNumber,
  Select,
  message,
} from 'antd';
import {
  ThunderboltOutlined,
  SyncOutlined,
  RocketOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  PlayCircleOutlined,
  DownCircleOutlined,
} from '@ant-design/icons';
import { useWebSocket } from '../hooks/useWebSocket';
import { realtimeAPI, topologyAPI } from '../services/api';

function RealtimeWaterLevel() {
  const { connected, waterLevelData, coordinationEvents } = useWebSocket();
  const [services, setServices] = useState([]);
  const [burstModalVisible, setBurstModalVisible] = useState(false);
  const [coordModalVisible, setCoordModalVisible] = useState(false);
  const [selectedService, setSelectedService] = useState(null);
  const [form] = Form.useForm();

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

  const getWaterLevelColor = (level) => {
    if (level >= 1.0) return '#ff4d4f';
    if (level >= 0.9) return '#fa8c16';
    if (level >= 0.7) return '#faad14';
    if (level >= 0.5) return '#52c41a';
    return '#1890ff';
  };

  const getWaterLevelStatus = (level) => {
    if (level >= 1.0) return '超载';
    if (level >= 0.9) return '危险';
    if (level >= 0.7) return '警告';
    if (level >= 0.5) return '正常';
    return '空闲';
  };

  const triggerBurst = async (values) => {
    try {
      await realtimeAPI.triggerBurst(values.serviceId, values.intensity, values.durationMinutes);
      message.success('突发流量已触发');
      setBurstModalVisible(false);
      form.resetFields();
    } catch (error) {
      message.error('触发失败');
    }
  };

  const triggerCoordination = async (values) => {
    try {
      await realtimeAPI.triggerCoordination(values.serviceId, values.waterLevel, 'MANUAL');
      message.success('协同限流已触发');
      setCoordModalVisible(false);
      form.resetFields();
    } catch (error) {
      message.error('触发失败');
    }
  };

  const releaseCoordination = async (coordinationId) => {
    try {
      await realtimeAPI.releaseCoordination(coordinationId);
      message.success('协同限流已解除');
    } catch (error) {
      message.error('解除失败');
    }
  };

  const getServiceName = (serviceId) => {
    const service = services.find(s => s.serviceId === serviceId);
    return service?.serviceName || serviceId;
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>实时限流水位监控</h2>
        <Space>
          <Badge status={connected ? 'success' : 'error'} text={connected ? '实时连接' : '离线'} />
          <Button
            type="primary"
            icon={<RocketOutlined />}
            onClick={() => {
              setSelectedService(null);
              setBurstModalVisible(true);
            }}
          >
            触发突发流量
          </Button>
          <Button
            icon={<ThunderboltOutlined />}
            onClick={() => {
              setSelectedService(null);
              setCoordModalVisible(true);
            }}
          >
            触发协同限流
          </Button>
        </Space>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="活跃协同限流"
              value={waterLevelData?.activeCoordinations || 0}
              prefix={<ThunderboltOutlined style={{ color: '#fa8c16' }} />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="危险水位服务"
              value={Object.entries(waterLevelData?.waterLevels || {}).filter(([_, v]) => v >= 0.9).length}
              prefix={<WarningOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="正常水位服务"
              value={Object.entries(waterLevelData?.waterLevels || {}).filter(([_, v]) => v >= 0.5 && v < 0.9).length}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="更新频率"
              value="100"
              suffix="ms"
              prefix={<SyncOutlined spin style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {services.slice(0, 10).map(service => {
          const serviceId = service.serviceId;
          const waterLevel = waterLevelData?.waterLevels?.[serviceId] || 0;
          const currentQps = waterLevelData?.currentQps?.[serviceId] || 0;
          const limitQps = waterLevelData?.limitQps?.[serviceId] || 0;
          const adjustedQps = waterLevelData?.adjustedQps?.[serviceId] || 0;
          const isAdjusted = adjustedQps < limitQps;

          return (
            <Col span={12} key={serviceId}>
              <Card
                size="small"
                title={
                  <Space>
                    {service.serviceName}
                    {isAdjusted && (
                      <Tag color="orange" icon={<DownCircleOutlined />}>
                        协同降额
                      </Tag>
                    )}
                    <Tag color={getWaterLevelColor(waterLevel)}>
                      {getWaterLevelStatus(waterLevel)}
                    </Tag>
                  </Space>
                }
                extra={
                  <Space>
                    <Button
                      size="small"
                      type="link"
                      icon={<RocketOutlined />}
                      onClick={() => {
                        setSelectedService(serviceId);
                        setBurstModalVisible(true);
                      }}
                    >
                      突发
                    </Button>
                  </Space>
                }
              >
                <div className="water-level-item">
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span style={{ fontWeight: 'bold' }}>限流水位</span>
                    <span style={{ color: getWaterLevelColor(waterLevel), fontWeight: 'bold' }}>
                      {(waterLevel * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="water-level-bar" style={{ height: 30, borderRadius: 15 }}>
                    <div
                      className="water-level-fill"
                      style={{
                        width: `${Math.min(100, waterLevel * 100)}%`,
                        backgroundColor: getWaterLevelColor(waterLevel),
                        transition: 'all 0.1s ease',
                      }}
                    />
                    <span className="water-level-label" style={{ fontSize: 12 }}>
                      {currentQps.toFixed(0)} / {adjustedQps.toFixed(0)} QPS
                    </span>
                  </div>
                </div>
                <Row style={{ marginTop: 12, fontSize: 12, color: '#666' }}>
                  <Col span={8}>
                    <div>原始阈值</div>
                    <div style={{ fontWeight: 'bold', color: '#333' }}>{limitQps.toFixed(0)}</div>
                  </Col>
                  <Col span={8}>
                    <div>调整后阈值</div>
                    <div style={{ fontWeight: 'bold', color: isAdjusted ? '#fa8c16' : '#333' }}>
                      {adjustedQps.toFixed(0)}
                    </div>
                  </Col>
                  <Col span={8}>
                    <div>当前流量</div>
                    <div style={{ fontWeight: 'bold', color: '#333' }}>{currentQps.toFixed(0)}</div>
                  </Col>
                </Row>
              </Card>
            </Col>
          );
        })}
      </Row>

      {coordinationEvents.length > 0 && (
        <Card title="协同限流事件" style={{ marginTop: 24 }}>
          <List
            dataSource={coordinationEvents}
            renderItem={event => (
              <List.Item
                actions={[
                  event.coordination?.status === 'ACTIVE' && (
                    <Button
                      size="small"
                      type="link"
                      onClick={() => releaseCoordination(event.coordination.coordinationId)}
                    >
                      解除
                    </Button>
                  ),
                ]}
              >
                <List.Item.Meta
                  avatar={<ThunderboltOutlined style={{ fontSize: 24, color: '#fa8c16' }} />}
                  title={
                    <Space>
                      <span>协同限流触发</span>
                      <Tag color="orange">{event.coordination?.triggerServiceId}</Tag>
                      <Tag>
                        降额 {(event.coordination?.reductionPercentage * 100).toFixed(0)}%
                      </Tag>
                      <Tag color="blue">
                        影响 {event.coordination?.affectedUpstreamServices?.length || 0} 个服务
                      </Tag>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={0}>
                      <span>触发原因: {event.coordination?.triggerReason}</span>
                      <span>
                        影响服务: {event.coordination?.affectedUpstreamServices?.map(s => getServiceName(s)).join(', ')}
                      </span>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      <Modal
        title="触发突发流量"
        visible={burstModalVisible}
        onCancel={() => setBurstModalVisible(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={triggerBurst}>
          <Form.Item
            label="目标服务"
            name="serviceId"
            initialValue={selectedService}
            rules={[{ required: true }]}
          >
            <Select placeholder="选择服务">
              {services.map(s => (
                <Select.Option key={s.serviceId} value={s.serviceId}>
                  {s.serviceName}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="突发强度 (倍数)"
            name="intensity"
            initialValue={3.0}
            rules={[{ required: true }]}
          >
            <InputNumber min={1.5} max={10} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            label="持续时间 (分钟)"
            name="durationMinutes"
            initialValue={5}
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={60} step={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block icon={<PlayCircleOutlined />}>
              触发突发流量
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="触发协同限流"
        visible={coordModalVisible}
        onCancel={() => setCoordModalVisible(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={triggerCoordination}>
          <Form.Item
            label="下游服务 (触发源)"
            name="serviceId"
            initialValue={selectedService}
            rules={[{ required: true }]}
          >
            <Select placeholder="选择触发限流的服务">
              {services.map(s => (
                <Select.Option key={s.serviceId} value={s.serviceId}>
                  {s.serviceName}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="触发水位阈值"
            name="waterLevel"
            initialValue={0.95}
            rules={[{ required: true }]}
          >
            <InputNumber min={0.8} max={1.5} step={0.05} style={{ width: '100%' }} />
          </Form.Item>
          <Alert
            message="协同限流说明"
            description="当下游服务水位达到阈值时，将自动通知所有上游服务降低流量，形成连锁保护机制。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Form.Item>
            <Button type="primary" htmlType="submit" block icon={<ThunderboltOutlined />}>
              触发协同限流
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default RealtimeWaterLevel;
