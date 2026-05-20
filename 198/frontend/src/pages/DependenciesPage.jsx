import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Tag,
  Space,
  Typography,
  Statistic,
  Row,
  Col,
  Alert,
  Button,
  Modal,
  Descriptions,
  List,
  Tooltip,
  Timeline,
  Divider,
  Breadcrumb,
} from 'antd'
import {
  LinkOutlined,
  WarningOutlined,
  FireOutlined,
  SafetyOutlined,
  RocketOutlined,
  ReloadOutlined,
  ArrowRightOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { analysisApi } from '../api/client'

const { Title, Text } = Typography

const likelihoodColors = {
  high: 'red',
  medium: 'orange',
  low: 'green',
}

const likelihoodLabels = {
  high: '高概率',
  medium: '中概率',
  low: '低概率',
}

const cardinalityColors = {
  'High (10k+)': 'red',
  'Medium (1k-10k)': 'orange',
  'Low (<1k)': 'green',
}

export default function DependenciesPage() {
  const [loading, setLoading] = useState(false)
  const [analysisData, setAnalysisData] = useState(null)
  const [detailModal, setDetailModal] = useState(false)
  const [selectedRule, setSelectedRule] = useState(null)
  const [chainData, setChainData] = useState(null)
  const [selectedChain, setSelectedChain] = useState(null)
  const [chainModal, setChainModal] = useState(false)

  const fetchAnalysis = async () => {
    setLoading(true)
    try {
      const res = await analysisApi.analyzeDependencies()
      setAnalysisData(res.data)
    } catch (err) {
      console.error('Failed to fetch dependencies:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchRuleChain = async (ruleId) => {
    try {
      const res = await analysisApi.getRuleChain(ruleId)
      setChainData(res.data)
      setSelectedRule(res.data.rule)
      setDetailModal(true)
    } catch (err) {
      console.error('Failed to fetch rule chain:', err)
    }
  }

  useEffect(() => {
    fetchAnalysis()
  }, [])

  const getRuleName = (ruleId) => {
    const rule = analysisData?.rules?.find((r) => r.rule_id === ruleId)
    return rule?.rule_name || ruleId
  }

  const columns = [
    {
      title: '规则名称',
      dataIndex: 'rule_name',
      key: 'rule_name',
      render: (text, record) => (
        <Button type="link" onClick={() => fetchRuleChain(record.rule_id)}>
          {text}
        </Button>
      ),
    },
    {
      title: '触发顺序',
      dataIndex: 'trigger_order',
      key: 'trigger_order',
      render: (val) => (
        <Tag color={val === 1 ? 'green' : val === 2 ? 'gold' : 'red'}>
          第 {val} 层
        </Tag>
      ),
      sorter: (a, b) => a.trigger_order - b.trigger_order,
    },
    {
      title: '连锁概率',
      dataIndex: 'chain_likelihood',
      key: 'chain_likelihood',
      render: (val) => <Tag color={likelihoodColors[val]}>{likelihoodLabels[val]}</Tag>,
      filters: [
        { text: '高概率', value: 'high' },
        { text: '中概率', value: 'medium' },
        { text: '低概率', value: 'low' },
      ],
      onFilter: (value, record) => record.chain_likelihood === value,
    },
    {
      title: '依赖规则',
      dataIndex: 'depends_on',
      key: 'depends_on',
      render: (deps) => (
        <Space wrap>
          {deps?.length > 0 ? (
            deps.map((id) => (
              <Tag key={id} color="blue">
                {getRuleName(id)}
              </Tag>
            ))
          ) : (
            <Text type="secondary">无</Text>
          )}
        </Space>
      ),
    },
    {
      title: '被依赖',
      dataIndex: 'depended_by',
      key: 'depended_by',
      render: (deps) => (
        <Space wrap>
          {deps?.length > 0 ? (
            deps.map((id) => (
              <Tag key={id} color="orange">
                {getRuleName(id)}
              </Tag>
            ))
          ) : (
            <Text type="secondary">无</Text>
          )}
        </Space>
      ),
    },
    {
      title: '共享指标',
      dataIndex: 'shared_metrics',
      key: 'shared_metrics',
      render: (metrics) => (
        <Space wrap>
          {metrics?.length > 0 ? (
            metrics.map((m) => (
              <Tag key={m} color="purple">
                {m}
              </Tag>
            ))
          ) : (
            <Text type="secondary">无</Text>
          )}
        </Space>
      ),
    },
    {
      title: '影响范围',
      key: 'impact',
      render: (_, record) => {
        const impact = (record.depended_by?.length || 0)
        if (impact === 0) return <Text type="secondary">无下游影响</Text>
        if (impact <= 2) return <Tag color="gold">影响 {impact} 条规则</Tag>
        return <Tag color="red">影响 {impact} 条规则</Tag>
      },
    },
  ]

  const renderChain = (chain, isCritical = false) => (
    <Card
      size="small"
      style={{ marginBottom: 12, borderColor: isCritical ? '#ff4d4f' : undefined }}
      actions={[
        <Button
          type="link"
          size="small"
          onClick={() => {
            setSelectedChain({ chain, isCritical })
            setChainModal(true)
          }}
        >
          查看详情
        </Button>,
      ]}
    >
      <Space wrap>
        {chain.map((item, idx) => (
          <Space key={item.id}>
            <Tag color={idx === 0 ? 'green' : idx === chain.length - 1 ? 'red' : 'blue'}>
              {item.name}
            </Tag>
            {idx < chain.length - 1 && <ArrowRightOutlined />}
          </Space>
        ))}
      </Space>
      {isCritical && (
        <Tag color="red" style={{ marginTop: 8 }}>
          <FireOutlined /> 关键告警链
        </Tag>
      )}
    </Card>
  )

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <LinkOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                <div>
                  <Title level={3} style={{ margin: 0 }}>
                    告警依赖分析
                  </Title>
                  <Text type="secondary">
                    分析规则之间的关联关系，预测告警连锁反应
                  </Text>
                </div>
              </Space>
              <Button
                type="primary"
                icon={<ReloadOutlined />}
                onClick={fetchAnalysis}
                loading={loading}
              >
                刷新分析
              </Button>
            </Space>

            {analysisData?.summary && (
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic
                    title="总规则数"
                    value={analysisData.summary.total_rules}
                    prefix={<SafetyOutlined />}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="告警链数量"
                    value={analysisData.summary.total_chains}
                    valueStyle={{ color: '#faad14' }}
                    prefix={<LinkOutlined />}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="关键告警链"
                    value={analysisData.summary.critical_chains}
                    valueStyle={{ color: '#f5222d' }}
                    prefix={<FireOutlined />}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="独立规则"
                    value={analysisData.summary.independent_rules}
                    valueStyle={{ color: '#52c41a' }}
                    prefix={<SafetyOutlined />}
                  />
                </Col>
              </Row>
            )}

            {analysisData?.critical_chains?.length > 0 && (
              <Alert
                message="检测到关键告警链"
                description={`发现 ${analysisData.critical_chains.length} 条关键告警链，单个事件可能引发连锁告警。建议优化告警规则或添加抑制规则。`}
                type="error"
                showIcon
              />
            )}
          </Space>
        </Card>

        {analysisData?.hot_metrics?.length > 0 && (
          <Card
            title={
              <Space>
                <FireOutlined style={{ color: '#faad14' }} />
                热点指标
              </Space>
            }
            extra={<Text type="secondary">被多个规则使用的指标</Text>}
          >
            <Row gutter={16}>
              {analysisData.hot_metrics.map((metric) => (
                <Col span={8} key={metric.metric_name}>
                  <Card size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                        <Tag color="blue" style={{ fontSize: 14 }}>
                          {metric.metric_name}
                        </Tag>
                        <Tag color={cardinalityColors[metric.cardinality_est]}>
                          {metric.cardinality_est}
                        </Tag>
                      </Space>
                      <Text type="secondary">被 {metric.rule_count} 条规则使用</Text>
                      <Space wrap>
                        {metric.related_rules?.map((id) => (
                          <Tag key={id} color="purple">
                            {getRuleName(id)}
                          </Tag>
                        ))}
                      </Space>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        )}

        {analysisData?.critical_chains?.length > 0 && (
          <Card
            title={
              <Space>
                <WarningOutlined style={{ color: '#f5222d' }} />
                关键告警链
              </Space>
            }
            extra={<Text type="secondary">高风险的告警连锁路径</Text>}
          >
            {analysisData.critical_chains.map((chain, idx) => renderChain(chain, true))}
          </Card>
        )}

        {analysisData?.chains?.length > 0 && (
          <Card
            title={
              <Space>
                <LinkOutlined style={{ color: '#1890ff' }} />
                所有告警链
              </Space>
            }
          >
            {analysisData.chains.map((chain, idx) => renderChain(chain, false))}
          </Card>
        )}

        <Card title="规则依赖详情">
          <Table
            loading={loading}
            columns={columns}
            dataSource={analysisData?.rules || []}
            rowKey="rule_id"
            pagination={{ pageSize: 10 }}
            expandable={{
              expandedRowRender: (record) => (
                <Text type="secondary">{record.chain_description || '无描述'}</Text>
              ),
            }}
          />
        </Card>
      </Space>

      <Modal
        title={`${selectedRule?.rule_name} - 依赖分析`}
        open={detailModal}
        onCancel={() => setDetailModal(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModal(false)}>
            关闭
          </Button>,
        ]}
      >
        {chainData && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Row gutter={16}>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="上游依赖"
                    value={chainData.upstream_dependencies}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="下游影响"
                    value={chainData.downstream_impact}
                    valueStyle={{ color: chainData.downstream_impact > 0 ? '#faad14' : '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="相关告警链"
                    value={chainData.related_chains?.length}
                    valueStyle={{ color: '#722ed1' }}
                  />
                </Card>
              </Col>
            </Row>

            <Descriptions title="依赖信息" bordered column={2}>
              <Descriptions.Item label="连锁概率">
                <Tag color={likelihoodColors[selectedRule?.chain_likelihood]}>
                  {likelihoodLabels[selectedRule?.chain_likelihood]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="触发顺序">
                第 {selectedRule?.trigger_order} 层
              </Descriptions.Item>
              <Descriptions.Item label="依赖规则" span={2}>
                <Space wrap>
                  {selectedRule?.depends_on?.length > 0 ? (
                    selectedRule.depends_on.map((id) => (
                      <Tag key={id} color="blue">
                        {getRuleName(id)}
                      </Tag>
                    ))
                  ) : (
                    <Text type="secondary">无上游依赖</Text>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="被依赖规则" span={2}>
                <Space wrap>
                  {selectedRule?.depended_by?.length > 0 ? (
                    selectedRule.depended_by.map((id) => (
                      <Tag key={id} color="orange">
                        {getRuleName(id)}
                      </Tag>
                    ))
                  ) : (
                    <Text type="secondary">无下游依赖</Text>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="共享指标" span={2}>
                <Space wrap>
                  {selectedRule?.shared_metrics?.length > 0 ? (
                    selectedRule.shared_metrics.map((m) => (
                      <Tag key={m} color="purple">
                        {m}
                      </Tag>
                    ))
                  ) : (
                    <Text type="secondary">无共享指标</Text>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedRule?.chain_description || '无'}
              </Descriptions.Item>
            </Descriptions>

            {chainData.related_chains?.length > 0 && (
              <Card title="相关告警链" size="small">
                {chainData.related_chains.map((chain, idx) => (
                  <div key={idx} style={{ marginBottom: 8 }}>
                    <Space wrap>
                      {chain.map((id, i) => (
                        <Space key={id}>
                          <Tag color={i === 0 ? 'green' : i === chain.length - 1 ? 'red' : 'blue'}>
                            {getRuleName(id)}
                          </Tag>
                          {i < chain.length - 1 && <ArrowRightOutlined />}
                        </Space>
                      ))}
                    </Space>
                  </div>
                ))}
              </Card>
            )}

            {chainData.downstream_impact > 0 && (
              <Alert
                message="下游影响警告"
                description={`此规则触发后可能导致 ${chainData.downstream_impact} 条关联规则触发，建议考虑添加抑制规则或优化阈值。`}
                type="warning"
                showIcon
              />
            )}
          </Space>
        )}
      </Modal>

      <Modal
        title={
          <Breadcrumb>
            <Breadcrumb.Item>告警链详情</Breadcrumb.Item>
            <Breadcrumb.Item>
              {selectedChain?.isCritical && <Tag color="red">关键链</Tag>}
            </Breadcrumb.Item>
          </Breadcrumb>
        }
        open={chainModal}
        onCancel={() => setChainModal(false)}
        width={600}
        footer={[
          <Button key="close" onClick={() => setChainModal(false)}>
            关闭
          </Button>,
        ]}
      >
        {selectedChain && (
          <Timeline
            mode="left"
            items={selectedChain.chain.map((item, idx) => ({
              color: idx === 0 ? 'green' : idx === selectedChain.chain.length - 1 ? 'red' : 'blue',
              label: `第 ${idx + 1} 层`,
              children: (
                <Card size="small">
                  <Space direction="vertical">
                    <Text strong>{item.name}</Text>
                    {idx === 0 && (
                      <Text type="secondary">
                        <InfoCircleOutlined /> 初始触发点
                      </Text>
                    )}
                    {idx === selectedChain.chain.length - 1 && (
                      <Text type="danger">
                        <WarningOutlined /> 告警链末端（高影响）
                      </Text>
                    )}
                    {idx > 0 && idx < selectedChain.chain.length - 1 && (
                      <Text type="secondary">
                        <LinkOutlined /> 中间传递节点
                      </Text>
                    )}
                  </Space>
                </Card>
              ),
            }))}
          />
        )}
      </Modal>
    </div>
  )
}
