import React, { useState, useEffect } from 'react';
import {
  Card, Table, Tag, Space, Typography, Statistic, Row, Col,
  Select, Alert, Descriptions, Progress, Button, Divider, List
} from 'antd';
import {
  ExclamationCircleOutlined, WarningOutlined, CheckCircleOutlined,
  ArrowUpOutlined, ArrowDownOutlined, RocketOutlined
} from '@ant-design/icons';
import { topologyApi } from '../services/api';
import type { ImpactAnalysisResult, ChangePredictionResult, ImpactedService } from '../types';

const { Title, Text } = Typography;
const { Option } = Select;

interface ImpactAnalysisPanelProps {
  serviceId: string | null;
  serviceName: string | null;
  onClose: () => void;
}

const ImpactAnalysisPanel: React.FC<ImpactAnalysisPanelProps> = ({ serviceId, serviceName, onClose }) => {
  const [impactAnalysis, setImpactAnalysis] = useState<ImpactAnalysisResult | null>(null);
  const [changePrediction, setChangePrediction] = useState<ChangePredictionResult | null>(null);
  const [changeType, setChangeType] = useState<string>('code');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'impact' | 'prediction'>('impact');

  useEffect(() => {
    if (serviceId) {
      fetchImpactAnalysis();
      fetchChangePrediction();
    }
  }, [serviceId, changeType]);

  const fetchImpactAnalysis = async () => {
    if (!serviceId) return;
    setLoading(true);
    try {
      const result = await topologyApi.getImpactAnalysis(serviceId);
      setImpactAnalysis(result);
    } catch (error) {
      console.error('Failed to fetch impact analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchChangePrediction = async () => {
    if (!serviceId) return;
    setLoading(true);
    try {
      const result = await topologyApi.getChangePrediction(serviceId, changeType);
      setChangePrediction(result);
    } catch (error) {
      console.error('Failed to fetch change prediction:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level?.toUpperCase()) {
      case 'HIGH': return 'red';
      case 'MEDIUM': return 'orange';
      case 'LOW': return 'green';
      default: return 'default';
    }
  };

  const getRiskLevelIcon = (level: string) => {
    switch (level?.toUpperCase()) {
      case 'HIGH': return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'MEDIUM': return <WarningOutlined style={{ color: '#faad14' }} />;
      case 'LOW': return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      default: return null;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'HIGH': return 'red';
      case 'MEDIUM': return 'orange';
      case 'LOW': return 'green';
      default: return 'default';
    }
  };

  const impactedServiceColumns = [
    {
      title: '服务ID',
      dataIndex: 'serviceId',
      key: 'serviceId',
      render: (id: string) => <Text code>{id}</Text>
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{severity}</Tag>
      )
    },
    {
      title: '调用量',
      dataIndex: 'callCount',
      key: 'callCount',
      sorter: (a: ImpactedService, b: ImpactedService) => a.callCount - b.callCount
    },
    {
      title: 'QPS',
      dataIndex: 'qps',
      key: 'qps',
      render: (qps: number) => qps?.toFixed(2),
      sorter: (a: ImpactedService, b: ImpactedService) => a.qps - b.qps
    },
    {
      title: '平均延迟',
      dataIndex: 'avgLatencyMs',
      key: 'avgLatencyMs',
      render: (ms: number) => `${ms?.toFixed(2)}ms`,
      sorter: (a: ImpactedService, b: ImpactedService) => a.avgLatencyMs - b.avgLatencyMs
    },
    {
      title: '影响分数',
      dataIndex: 'impactScore',
      key: 'impactScore',
      render: (score: number) => score?.toFixed(1),
      sorter: (a: ImpactedService, b: ImpactedService) => a.impactScore - b.impactScore
    }
  ];

  if (!serviceId) {
    return (
      <Card>
        <Alert
          message="请选择服务"
          description="点击拓扑图中的服务节点查看影响分析和变更预测"
          type="info"
          showIcon
        />
      </Card>
    );
  }

  return (
    <Card
      title={
        <Space>
          <RocketOutlined />
          <span>影响分析 & 变更预测</span>
          {serviceName && <Tag color="blue">{serviceName}</Tag>}
        </Space>
      }
      extra={
        <Space>
          <Select
            value={changeType}
            onChange={setChangeType}
            style={{ width: 150 }}
            size="small"
          >
            <Option value="code">代码变更</Option>
            <Option value="api">API变更</Option>
            <Option value="database">数据库变更</Option>
            <Option value="schema">Schema变更</Option>
            <Option value="config">配置变更</Option>
          </Select>
          <Button size="small" onClick={onClose}>关闭</Button>
        </Space>
      }
      loading={loading}
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Space>
            <Button
              type={activeTab === 'impact' ? 'primary' : 'default'}
              onClick={() => setActiveTab('impact')}
            >
              <ArrowUpOutlined /> 影响分析
            </Button>
            <Button
              type={activeTab === 'prediction' ? 'primary' : 'default'}
              onClick={() => setActiveTab('prediction')}
            >
              <RocketOutlined /> 变更预测
            </Button>
          </Space>
        </div>

        {activeTab === 'impact' && impactAnalysis && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="风险等级"
                    value={impactAnalysis.riskLevel}
                    prefix={getRiskLevelIcon(impactAnalysis.riskLevel)}
                    valueStyle={{ color: getRiskLevelColor(impactAnalysis.riskLevel) === 'red' ? '#cf1322' : undefined }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="上游服务"
                    value={impactAnalysis.totalUpstreamImpact}
                    prefix={<ArrowUpOutlined style={{ color: '#52c41a' }} />}
                    valueStyle={{ color: '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="下游服务"
                    value={impactAnalysis.totalDownstreamImpact}
                    prefix={<ArrowDownOutlined style={{ color: '#ff4d4f' }} />}
                    valueStyle={{ color: '#cf1322' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="总影响范围"
                    value={impactAnalysis.totalUpstreamImpact + impactAnalysis.totalDownstreamImpact}
                    prefix={<ExclamationCircleOutlined />}
                  />
                </Card>
              </Col>
            </Row>

            <Divider orientation="left">上游依赖</Divider>
            {impactAnalysis.upstreamServices.length > 0 ? (
              <List
                size="small"
                dataSource={impactAnalysis.upstreamServices}
                renderItem={(item) => (
                  <List.Item>
                    <Space>
                      <ArrowUpOutlined style={{ color: '#52c41a' }} />
                      <Tag color="green">上游</Tag>
                      <Text code>{item}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Text type="secondary">无上游依赖</Text>
            )}

            <Divider orientation="left">下游影响</Divider>
            {impactAnalysis.downstreamServices.length > 0 ? (
              <List
                size="small"
                dataSource={impactAnalysis.downstreamServices}
                renderItem={(item) => (
                  <List.Item>
                    <Space>
                      <ArrowDownOutlined style={{ color: '#ff4d4f' }} />
                      <Tag color="red">下游</Tag>
                      <Text code>{item}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            ) : (
              <Text type="secondary">无下游影响</Text>
            )}
          </Space>
        )}

        {activeTab === 'prediction' && changePrediction && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="受影响服务"
                    value={changePrediction.totalImpactedServices}
                    suffix="个"
                    valueStyle={{ color: changePrediction.totalImpactedServices > 0 ? '#cf1322' : '#3f8600' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="高风险服务"
                    value={changePrediction.highSeverityCount}
                    suffix="个"
                    valueStyle={{ color: '#cf1322' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="预估停机时间"
                    value={changePrediction.estimatedDowntimeMinutes}
                    suffix="分钟"
                    valueStyle={{ color: changePrediction.estimatedDowntimeMinutes > 30 ? '#cf1322' : '#faad14' }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic
                    title="预估恢复时间"
                    value={changePrediction.estimatedRecoveryHours}
                    suffix="小时"
                    valueStyle={{ color: changePrediction.estimatedRecoveryHours > 1 ? '#cf1322' : '#faad14' }}
                  />
                </Card>
              </Col>
            </Row>

            <Card size="small" title="严重程度分布">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Space>
                    <Text>高风险</Text>
                    <Progress
                      percent={changePrediction.totalImpactedServices > 0 
                        ? Math.round((changePrediction.highSeverityCount / changePrediction.totalImpactedServices) * 100) 
                        : 0}
                      strokeColor="#ff4d4f"
                      size="small"
                      style={{ width: 200 }}
                    />
                    <Tag color="red">{changePrediction.highSeverityCount}个</Tag>
                  </Space>
                </div>
                <div>
                  <Space>
                    <Text>中风险</Text>
                    <Progress
                      percent={changePrediction.totalImpactedServices > 0 
                        ? Math.round((changePrediction.mediumSeverityCount / changePrediction.totalImpactedServices) * 100) 
                        : 0}
                      strokeColor="#faad14"
                      size="small"
                      style={{ width: 200 }}
                    />
                    <Tag color="orange">{changePrediction.mediumSeverityCount}个</Tag>
                  </Space>
                </div>
                <div>
                  <Space>
                    <Text>低风险</Text>
                    <Progress
                      percent={changePrediction.totalImpactedServices > 0 
                        ? Math.round((changePrediction.lowSeverityCount / changePrediction.totalImpactedServices) * 100) 
                        : 0}
                      strokeColor="#52c41a"
                      size="small"
                      style={{ width: 200 }}
                    />
                    <Tag color="green">{changePrediction.lowSeverityCount}个</Tag>
                  </Space>
                </div>
              </Space>
            </Card>

            <Alert
              message="发布建议"
              description={changePrediction.recommendation}
              type={changePrediction.highSeverityCount > 0 ? 'warning' : 'info'}
              showIcon
            />

            <Divider orientation="left">受影响服务详情</Divider>
            {changePrediction.impactedServices.length > 0 ? (
              <Table
                size="small"
                dataSource={changePrediction.impactedServices}
                columns={impactedServiceColumns}
                rowKey="serviceId"
                pagination={{ pageSize: 5 }}
              />
            ) : (
              <Text type="secondary">无直接受影响的服务</Text>
            )}
          </Space>
        )}
      </Space>
    </Card>
  );
};

export default ImpactAnalysisPanel;
