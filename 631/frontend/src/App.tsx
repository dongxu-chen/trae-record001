import React, { useState, useEffect } from 'react';
import { Layout, Typography, Space, Button, message, Statistic, Row, Col, Card, Tag, Switch, Tooltip } from 'antd';
import {
  ReloadOutlined, DashboardOutlined, ClearOutlined, CloudServerOutlined,
  AppstoreOutlined, ApiOutlined, TeamOutlined, RocketOutlined, LineChartOutlined
} from '@ant-design/icons';
import TopologyGraph from './components/TopologyGraph';
import ServiceDetailModal from './components/ServiceDetailModal';
import GroupPanel from './components/GroupPanel';
import ImpactAnalysisPanel from './components/ImpactAnalysisPanel';
import { topologyApi } from './services/api';
import type {
  TopologyData, TopologyStats, ServiceNodeDetail,
  GroupedTopologyData, TopologyGroup, ConsumerGroupNode,
  ImpactAnalysisResult
} from './types';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;

const App: React.FC = () => {
  const [groupedData, setGroupedData] = useState<GroupedTopologyData | null>(null);
  const [topologyData, setTopologyData] = useState<TopologyData>({ nodes: [], edges: [] });
  const [stats, setStats] = useState<TopologyStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [selectedServiceName, setSelectedServiceName] = useState<string | null>(null);
  const [serviceDetail, setServiceDetail] = useState<ServiceNodeDetail | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [groupMode, setGroupMode] = useState(true);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [showConsumerGroups, setShowConsumerGroups] = useState(true);
  const [showQps, setShowQps] = useState(true);
  const [showImpactPanel, setShowImpactPanel] = useState(false);
  const [impactAnalysis, setImpactAnalysis] = useState<ImpactAnalysisResult | null>(null);

  const fetchTopology = async () => {
    setLoading(true);
    try {
      const [groupedRes, statsRes] = await Promise.all([
        topologyApi.getGroupedTopology(),
        topologyApi.getTopologyStats()
      ]);
      setGroupedData(groupedRes);
      setTopologyData({ nodes: groupedRes.nodes, edges: groupedRes.edges });
      setStats(statsRes);

      const initialCollapsed = new Set<string>();
      groupedRes.groups.forEach(g => {
        if (g.collapsed) initialCollapsed.add(g.id);
      });
      setCollapsedGroups(initialCollapsed);
    } catch (error) {
      message.error('加载拓扑数据失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTopology();
    const interval = setInterval(fetchTopology, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleNodeClick = async (nodeId: string) => {
    try {
      const [detail, impact] = await Promise.all([
        topologyApi.getServiceDetail(nodeId),
        topologyApi.getImpactAnalysis(nodeId)
      ]);
      setServiceDetail(detail);
      setSelectedService(nodeId);
      setSelectedServiceName(detail.name || nodeId);
      setImpactAnalysis(impact);
      setModalVisible(true);
      setShowImpactPanel(true);
    } catch (error) {
      message.error('加载服务详情失败');
    }
  };

  const handleGroupClick = async (groupId: string) => {
    const newCollapsed = new Set(collapsedGroups);
    if (newCollapsed.has(groupId)) {
      newCollapsed.delete(groupId);
    } else {
      newCollapsed.add(groupId);
    }
    setCollapsedGroups(newCollapsed);

    try {
      await topologyApi.updateGroupCollapsed(groupId, newCollapsed.has(groupId));
    } catch (error) {
      console.error('更新分组折叠状态失败', error);
    }
  };

  const handleTriggerDiscovery = async () => {
    try {
      await topologyApi.triggerDiscovery();
      message.success('服务发现已触发');
      setTimeout(fetchTopology, 2000);
    } catch (error) {
      message.error('触发服务发现失败');
    }
  };

  const handleClearData = async () => {
    try {
      await topologyApi.clearAllData();
      message.success('数据已清除');
      fetchTopology();
    } catch (error) {
      message.error('清除数据失败');
    }
  };

  const handleGroupCreated = () => {
    fetchTopology();
  };

  const getLanguageColor = (lang: string): string => {
    const colors: Record<string, string> = {
      'Java': '#b07219',
      'Python': '#3572A5',
      'Go': '#00ADD8',
      'Node.js': '#339933',
      'Rust': '#dea584',
      'C#': '#178600',
      'Ruby': '#701516',
      'PHP': '#4F5D95'
    };
    return colors[lang] || '#999';
  };

  const getCallTypeColor = (type: string): string => {
    const colors: Record<string, string> = {
      'SYNC_HTTP': '#1890ff',
      'ASYNC_HTTP': '#fa8c16',
      'MESSAGE_QUEUE': '#722ed1',
      'DATABASE': '#13c2c2',
      'GRPC': '#52c41a'
    };
    return colors[type] || '#8c8c8c';
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Space>
          <CloudServerOutlined style={{ color: '#fff', fontSize: 24 }} />
          <Title level={3} style={{ color: '#fff', margin: 0 }}>服务拓扑发现系统</Title>
        </Space>
        <Space>
          <Space>
            <Text style={{ color: '#fff' }}>分组模式</Text>
            <Switch
              checked={groupMode}
              onChange={setGroupMode}
              checkedChildren="开"
              unCheckedChildren="关"
            />
          </Space>
          <Space>
            <Text style={{ color: '#fff' }}>显示消费组</Text>
            <Switch
              checked={showConsumerGroups}
              onChange={setShowConsumerGroups}
              checkedChildren="开"
              unCheckedChildren="关"
            />
          </Space>
          <Space>
            <Text style={{ color: '#fff' }}>显示QPS</Text>
            <Switch
              checked={showQps}
              onChange={setShowQps}
              checkedChildren="开"
              unCheckedChildren="关"
            />
          </Space>
          <Button
            type={showImpactPanel ? 'primary' : 'default'}
            icon={<RocketOutlined />}
            onClick={() => setShowImpactPanel(!showImpactPanel)}
          >
            影响分析
          </Button>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={handleTriggerDiscovery}
          >
            触发发现
          </Button>
          <Button
            icon={<DashboardOutlined />}
            onClick={fetchTopology}
            loading={loading}
          >
            刷新数据
          </Button>
          <Button
            danger
            icon={<ClearOutlined />}
            onClick={handleClearData}
          >
            清除数据
          </Button>
        </Space>
      </Header>
      <Layout>
        {groupMode && groupedData && (
          <Sider width={320} style={{ background: '#fff', borderRight: '1px solid #e8e8e8' }}>
            <GroupPanel
              groups={groupedData.groups}
              consumerGroups={showConsumerGroups ? groupedData.consumerGroups : []}
              collapsedGroups={collapsedGroups}
              onGroupClick={handleGroupClick}
              onGroupCreated={handleGroupCreated}
              services={groupedData.nodes}
            />
          </Sider>
        )}
        <Content style={{ padding: '20px' }}>
          <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="服务总数"
                  value={stats?.totalServices || 0}
                  prefix={<CloudServerOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="调用关系"
                  value={stats?.totalCallRelationships || 0}
                  valueStyle={{ color: '#3f8600' }}
                  prefix={<ApiOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="服务分组"
                  value={groupedData?.groups?.length || 0}
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<AppstoreOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="平均延迟"
                  value={stats?.averageLatencyMs || 0}
                  suffix="ms"
                  valueStyle={{ color: '#cf1322' }}
                />
              </Card>
            </Col>
          </Row>

          {stats && stats.languages.length > 0 && (
            <Card style={{ marginBottom: 20 }} title="支持的编程语言">
              <Space wrap>
                {stats.languages.filter(l => l).map((lang, idx) => (
                  <Tag key={idx} color={getLanguageColor(lang)}>
                    {lang}
                  </Tag>
                ))}
              </Space>
            </Card>
          )}

          {groupedData && groupedData.consumerGroups.length > 0 && showConsumerGroups && (
            <Card style={{ marginBottom: 20 }} title="消费组信息" extra={<TeamOutlined />}>
              <Row gutter={[16, 16]}>
                {groupedData.consumerGroups.map((cg: ConsumerGroupNode) => (
                  <Col span={8} key={cg.id}>
                    <Card size="small" type="inner">
                      <Card.Meta
                        title={
                          <Space>
                            <Tag color="purple">{cg.messageQueue}</Tag>
                            <Text strong>{cg.name}</Text>
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size="small" style={{ width: '100%' }}>
                            <Text type="secondary">Topic: {cg.topic}</Text>
                            <div>
                              <Text type="secondary">生产者: </Text>
                              <Tag color="green">{cg.producerIds.length}个</Tag>
                            </div>
                            <div>
                              <Text type="secondary">消费者: </Text>
                              <Tag color="blue">{cg.consumerCount}个</Tag>
                            </div>
                            <div>
                              <Text type="secondary">状态: </Text>
                              <Tag color={cg.status === 'ACTIVE' ? 'success' : 'default'}>{cg.status}</Tag>
                            </div>
                          </Space>
                        }
                      />
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          )}

          <Card title="服务拓扑图" extra={
            <Space>
              <Tooltip title="蓝色=同步调用，橙色=异步调用，紫色=消息队列">
                <Text type="secondary">图例:</Text>
                <Tag color={getCallTypeColor('SYNC_HTTP')}>同步HTTP</Tag>
                <Tag color={getCallTypeColor('ASYNC_HTTP')}>异步HTTP</Tag>
                <Tag color={getCallTypeColor('MESSAGE_QUEUE')}>消息队列</Tag>
                <Tag color={getCallTypeColor('DATABASE')}>数据库</Tag>
                <Tag color={getCallTypeColor('GRPC')}>gRPC</Tag>
              </Tooltip>
            </Space>
          }>
            <div className="topology-container">
              <TopologyGraph
                data={topologyData}
                groups={groupMode ? groupedData?.groups : []}
                consumerGroups={showConsumerGroups ? groupedData?.consumerGroups : []}
                collapsedGroups={collapsedGroups}
                onNodeClick={handleNodeClick}
                onGroupClick={handleGroupClick}
                selectedNode={selectedService}
                groupMode={groupMode}
                impactAnalysis={showImpactPanel ? impactAnalysis : null}
                showQps={showQps}
              />
            </div>
          </Card>

          <ServiceDetailModal
            visible={modalVisible}
            service={serviceDetail}
            onClose={() => {
              setModalVisible(false);
              setSelectedService(null);
              setServiceDetail(null);
            }}
          />
        </Content>
        {showImpactPanel && (
          <Sider width={400} style={{ background: '#fff', borderLeft: '1px solid #e8e8e8', padding: '10px' }}>
            <ImpactAnalysisPanel
              serviceId={selectedService}
              serviceName={selectedServiceName}
              onClose={() => setShowImpactPanel(false)}
            />
          </Sider>
        )}
      </Layout>
    </Layout>
  );
};

export default App;
