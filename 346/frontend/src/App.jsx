import { useState, useEffect } from 'react'
import { Layout, Typography, Space, Card, Row, Col, Statistic, message, Collapse, Tabs } from 'antd'
import { DatabaseOutlined, TeamOutlined, LineChartOutlined, ThunderboltOutlined, ClockCircleOutlined, BarChartOutlined, FilterOutlined, StarOutlined, VirusOutlined, RocketOutlined } from '@ant-design/icons'
import GraphVisualization from './components/GraphVisualization'
import DataUpload from './components/DataUpload'
import TimeSlider from './components/TimeSlider'
import CommunityPanel from './components/CommunityPanel'
import InfluencePanel from './components/InfluencePanel'
import TemporalAnalysis from './components/TemporalAnalysis'
import RelationshipFilter from './components/RelationshipFilter'
import InfluenceComparison from './components/InfluenceComparison'
import CacheStatus from './components/CacheStatus'
import KeyNodesPanel from './components/KeyNodesPanel'
import DiffusionSimulation from './components/DiffusionSimulation'
import CommunityEvolution from './components/CommunityEvolution'
import { graphApi } from './services/api'

const { Header, Content, Sider } = Layout
const { Title } = Typography
const { Panel } = Collapse

const DEFAULT_RELATIONSHIP_TYPES = ['FOLLOW', 'LIKE', 'COMMENT', 'FRIEND', 'COLLEAGUE']

function App() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], metrics: {} })
  const [communities, setCommunities] = useState([])
  const [influences, setInfluences] = useState([])
  const [loading, setLoading] = useState(false)
  const [timeRange, setTimeRange] = useState(null)
  const [relationshipTypes, setRelationshipTypes] = useState(DEFAULT_RELATIONSHIP_TYPES)
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const [activeTab, setActiveTab] = useState('graph')
  const [highlightedNodes, setHighlightedNodes] = useState({})
  const [diffusionStep, setDiffusionStep] = useState(null)

  useEffect(() => {
    loadGraphData()
    loadCommunities()
    loadInfluences()
  }, [])

  const loadGraphData = async () => {
    try {
      setLoading(true)
      const data = await graphApi.getGraph()
      setGraphData(data)
    } catch (error) {
      message.error('加载图数据失败')
    } finally {
      setLoading(false)
    }
  }

  const loadCommunities = async () => {
    try {
      const data = await graphApi.getCommunities()
      setCommunities(data)
    } catch (error) {
      console.error('加载社区数据失败', error)
    }
  }

  const loadInfluences = async (method = 'degree') => {
    try {
      const data = await graphApi.getInfluence(method)
      setInfluences(data)
    } catch (error) {
      console.error('加载影响力数据失败', error)
    }
  }

  const handleDataImported = () => {
    message.success('数据导入成功')
    loadGraphData()
    loadCommunities()
    loadInfluences()
  }

  const handleTimeChange = (range) => {
    setTimeRange(range)
  }

  const handleRelationshipTypesChange = (types) => {
    setRelationshipTypes(types)
  }

  const handleNodeClick = (nodeId) => {
    setSelectedNodeId(nodeId)
  }

  const handleKeyNodeClick = (nodeId) => {
    setSelectedNodeId(nodeId)
    if (nodeId) {
      setHighlightedNodes(prev => ({ ...prev, [nodeId]: 'key' }))
    }
  }

  const handleDiffusionStepChange = (stepData) => {
    setDiffusionStep(stepData)
    if (stepData) {
      const highlighted = {}
      stepData.infected?.forEach(n => highlighted[n] = 'infected')
      stepData.recovered?.forEach(n => highlighted[n] = 'recovered')
      stepData.new_infections?.forEach(n => highlighted[n] = 'new_infection')
      setHighlightedNodes(highlighted)
    } else {
      setHighlightedNodes({})
    }
  }

  const handleTabChange = (key) => {
    setActiveTab(key)
    if (key !== 'diffusion') {
      setDiffusionStep(null)
      setHighlightedNodes({})
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', padding: '0 24px' }}>
        <Space>
          <DatabaseOutlined style={{ color: '#fff', fontSize: '24px' }} />
          <Title level={3} style={{ color: '#fff', margin: 0, lineHeight: '64px' }}>
            社交关系图分析平台
          </Title>
        </Space>
      </Header>
      <Layout>
        <Sider width={360} style={{ background: '#fff', padding: '16px', overflowY: 'auto' }}>
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Card title="数据导入" size="small">
              <DataUpload onSuccess={handleDataImported} />
            </Card>
            <CacheStatus onDataChange={loadGraphData} />
            <Card title="图指标" size="small">
              <Row gutter={[8, 8]}>
                <Col span={12}>
                  <Statistic
                    title="节点数"
                    value={graphData.metrics?.node_count || 0}
                    prefix={<TeamOutlined />}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="边数"
                    value={graphData.metrics?.edge_count || 0}
                    prefix={<LineChartOutlined />}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="图密度"
                    value={graphData.metrics?.density || 0}
                    precision={4}
                    prefix={<ThunderboltOutlined />}
                  />
                </Col>
                <Col span={12}>
                  <Statistic
                    title="平均度数"
                    value={graphData.metrics?.average_degree || 0}
                    precision={2}
                  />
                </Col>
              </Row>
            </Card>
            <Card 
              title={
                <Space>
                  <FilterOutlined />
                  <span>关系类型过滤</span>
                </Space>
              } 
              size="small"
            >
              <RelationshipFilter
                value={relationshipTypes}
                onChange={handleRelationshipTypesChange}
                disabled={loading}
              />
            </Card>
            <Collapse 
              defaultActiveKey={['keyNodes']} 
              ghost
              size="small"
            >
              <Panel
                header={
                  <Space>
                    <StarOutlined style={{ color: '#faad14' }} />
                    <span>关键节点识别</span>
                  </Space>
                }
                key="keyNodes"
              >
                <KeyNodesPanel
                  onNodeClick={handleKeyNodeClick}
                  selectedNodeId={selectedNodeId}
                />
              </Panel>
              <Panel
                header={
                  <Space>
                    <ClockCircleOutlined style={{ color: '#1890ff' }} />
                    <span>时间演化分析</span>
                  </Space>
                }
                key="temporal"
              >
                <TemporalAnalysis nodes={graphData.nodes} />
              </Panel>
              <Panel
                header={
                  <Space>
                    <BarChartOutlined style={{ color: '#722ed1' }} />
                    <span>中心性算法对比</span>
                  </Space>
                }
                key="comparison"
              >
                <InfluenceComparison nodes={graphData.nodes} />
              </Panel>
            </Collapse>
            <Card title="社区检测" size="small">
              <CommunityPanel communities={communities} />
            </Card>
            <Card title="影响力分析" size="small">
              <InfluencePanel
                influences={influences}
                nodes={graphData.nodes}
                onMethodChange={loadInfluences}
              />
            </Card>
          </Space>
        </Sider>
        <Layout style={{ padding: '16px' }}>
          <Content style={{ background: '#fff', padding: '16px', borderRadius: '8px' }}>
            <Tabs
              activeKey={activeTab}
              onChange={handleTabChange}
              items={[
                {
                  key: 'graph',
                  label: (
                    <Space>
                      <DatabaseOutlined />
                      <span>关系图可视化</span>
                    </Space>
                  ),
                  children: (
                    <Card
                      size="small"
                      extra={
                        <Space>
                          <TimeSlider onChange={handleTimeChange} />
                        </Space>
                      }
                    >
                      <GraphVisualization
                        data={graphData}
                        loading={loading}
                        communities={communities}
                        timeRange={timeRange}
                        relationshipTypes={relationshipTypes}
                        selectedNodeId={selectedNodeId}
                        onNodeClick={handleNodeClick}
                        highlightedNodes={highlightedNodes}
                      />
                    </Card>
                  )
                },
                {
                  key: 'diffusion',
                  label: (
                    <Space>
                      <VirusOutlined />
                      <span>扩散模拟</span>
                    </Space>
                  ),
                  children: (
                    <DiffusionSimulation
                      onNodeClick={handleNodeClick}
                      onStepChange={handleDiffusionStepChange}
                      nodeList={graphData.nodes?.map(n => n.id) || []}
                    />
                  )
                },
                {
                  key: 'evolution',
                  label: (
                    <Space>
                      <RocketOutlined />
                      <span>社群演化动图</span>
                    </Space>
                  ),
                  children: (
                    <CommunityEvolution
                      onNodeClick={handleNodeClick}
                    />
                  )
                }
              ]}
            />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  )
}

export default App
