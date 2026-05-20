import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Tag,
  Progress,
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
} from 'antd'
import {
  ThunderboltOutlined,
  DatabaseOutlined,
  WarningOutlined,
  RocketOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { analysisApi } from '../api/client'

const { Title, Text } = Typography

const complexityColors = {
  low: 'green',
  medium: 'gold',
  high: 'orange',
  critical: 'red',
}

const complexityLabels = {
  low: '低负载',
  medium: '中负载',
  high: '高负载',
  critical: '极高负载',
}

export default function PerformancePage() {
  const [loading, setLoading] = useState(false)
  const [analysisData, setAnalysisData] = useState(null)
  const [detailModal, setDetailModal] = useState(false)
  const [selectedRule, setSelectedRule] = useState(null)
  const [detailAnalysis, setDetailAnalysis] = useState(null)

  const fetchAnalysis = async () => {
    setLoading(true)
    try {
      const res = await analysisApi.analyzeAllRules()
      setAnalysisData(res.data)
    } catch (err) {
      console.error('Failed to fetch analysis:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchRuleDetail = async (ruleId) => {
    try {
      const res = await analysisApi.analyzeRule(ruleId)
      setDetailAnalysis(res.data.analysis)
      setSelectedRule(res.data)
      setDetailModal(true)
    } catch (err) {
      console.error('Failed to fetch rule analysis:', err)
    }
  }

  useEffect(() => {
    fetchAnalysis()
  }, [])

  const columns = [
    {
      title: '规则名称',
      dataIndex: 'rule_name',
      key: 'rule_name',
      render: (text, record) => (
        <Button type="link" onClick={() => fetchRuleDetail(record.rule_id)}>
          {text}
        </Button>
      ),
    },
    {
      title: '复杂度',
      dataIndex: 'complexity',
      key: 'complexity',
      render: (val) => <Tag color={complexityColors[val]}>{complexityLabels[val]}</Tag>,
      filters: [
        { text: '低负载', value: 'low' },
        { text: '中负载', value: 'medium' },
        { text: '高负载', value: 'high' },
        { text: '极高负载', value: 'critical' },
      ],
      onFilter: (value, record) => record.complexity === value,
    },
    {
      title: '复杂度评分',
      dataIndex: 'complexity_score',
      key: 'complexity_score',
      render: (score) => (
        <Progress
          percent={score}
          strokeColor={{
            '0%': '#52c41a',
            '50%': '#faad14',
            '100%': '#f5222d',
          }}
          size="small"
          format={(p) => `${p}/100`}
        />
      ),
      sorter: (a, b) => a.complexity_score - b.complexity_score,
    },
    {
      title: '查询类型',
      dataIndex: 'query_type',
      key: 'query_type',
      render: (val) => <Tag>{val}</Tag>,
    },
    {
      title: '预估时间序列',
      dataIndex: 'total_cardinality',
      key: 'total_cardinality',
      render: (val) => val?.toLocaleString(),
      sorter: (a, b) => a.total_cardinality - b.total_cardinality,
    },
    {
      title: '指标数量',
      dataIndex: 'metrics_count',
      key: 'metrics_count',
      render: (val) => <Tag color="blue">{val} 个</Tag>,
    },
    {
      title: '预估负载',
      dataIndex: 'estimated_load',
      key: 'estimated_load',
      ellipsis: true,
    },
  ]

  const getComplexityStatColor = (count) => {
    if (count === 0) return '#52c41a'
    if (count <= 3) return '#faad14'
    return '#f5222d'
  }

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <RocketOutlined style={{ fontSize: 32, color: '#1890ff' }} />
                <div>
                  <Title level={3} style={{ margin: 0 }}>
                    规则性能分析
                  </Title>
                  <Text type="secondary">
                    分析 PromQL 查询复杂度、预估标签基数和查询负载
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

            {analysisData && (
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic
                    title="总规则数"
                    value={analysisData.total_rules}
                    prefix={<DatabaseOutlined />}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="高负载规则"
                    value={analysisData.high_load_count}
                    valueStyle={{ color: getComplexityStatColor(analysisData.high_load_count) }}
                    prefix={<WarningOutlined />}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="平均复杂度"
                    value={analysisData.avg_complexity}
                    suffix="/100"
                    prefix={<ThunderboltOutlined />}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="预估总时间序列"
                    value={analysisData.total_cardinality}
                    formatter={(val) => val?.toLocaleString()}
                    prefix={<DatabaseOutlined />}
                  />
                </Col>
              </Row>
            )}

            {analysisData?.high_load_count > 0 && (
              <Alert
                message="发现高负载规则"
                description={`有 ${analysisData.high_load_count} 条规则属于高负载或极高负载，建议优化查询表达式或增加评估间隔。`}
                type="warning"
                showIcon
              />
            )}
          </Space>
        </Card>

        <Card title="规则性能详情">
          <Table
            loading={loading}
            columns={columns}
            dataSource={analysisData?.analyses || []}
            rowKey="rule_id"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      </Space>

      <Modal
        title={`${selectedRule?.rule_name} - 性能详情`}
        open={detailModal}
        onCancel={() => setDetailModal(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setDetailModal(false)}>
            关闭
          </Button>,
        ]}
      >
        {detailAnalysis && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Row gutter={16}>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="复杂度"
                    value={complexityLabels[detailAnalysis.complexity]}
                    valueStyle={{ color: complexityColors[detailAnalysis.complexity] }}
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="复杂度评分"
                    value={detailAnalysis.complexity_score}
                    suffix="/100"
                  />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic
                    title="预估时间序列"
                    value={detailAnalysis.total_cardinality}
                    formatter={(v) => v?.toLocaleString()}
                  />
                </Card>
              </Col>
            </Row>

            <Descriptions title="查询信息" bordered column={2}>
              <Descriptions.Item label="查询类型">
                <Tag>{detailAnalysis.query_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="时间范围">
                {detailAnalysis.time_range || '无'}
              </Descriptions.Item>
              <Descriptions.Item label="使用指标" span={2}>
                <Space wrap>
                  {detailAnalysis.metrics_used?.map((m) => (
                    <Tag key={m} color="blue">
                      {m}
                    </Tag>
                  ))}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="使用函数" span={2}>
                <Space wrap>
                  {detailAnalysis.functions_used?.length > 0 ? (
                    detailAnalysis.functions_used?.map((f) => (
                      <Tag key={f} color="cyan">
                        {f}
                      </Tag>
                    ))
                  ) : (
                    <Text type="secondary">无</Text>
                  )}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="标签选择器" span={2}>
                <Space wrap>
                  {detailAnalysis.label_selectors?.map((s) => (
                    <Tag key={s} color="purple">
                      {s}
                    </Tag>
                  ))}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="使用正则">
                <Tag color={detailAnalysis.has_regex ? 'red' : 'green'}>
                  {detailAnalysis.has_regex ? '是' : '否'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="有聚合">
                <Tag color={detailAnalysis.has_aggregation ? 'orange' : 'green'}>
                  {detailAnalysis.has_aggregation ? '是' : '否'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="执行计划" span={2}>
                <Text code style={{ wordBreak: 'break-all' }}>
                  {detailAnalysis.execution_plan}
                </Text>
              </Descriptions.Item>
            </Descriptions>

            {detailAnalysis.estimated_cardinality && Object.keys(detailAnalysis.estimated_cardinality).length > 0 && (
              <Card title="预估标签基数" size="small">
                <List
                  dataSource={Object.entries(detailAnalysis.estimated_cardinality)}
                  renderItem={([metric, count]) => (
                    <List.Item>
                      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                        <Tag color="blue">{metric}</Tag>
                        <Text strong>{count.toLocaleString()} 时间序列</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {detailAnalysis.recommendations?.length > 0 && (
              <Alert
                message="优化建议"
                description={
                  <List
                    dataSource={detailAnalysis.recommendations}
                    renderItem={(item) => (
                      <List.Item>
                        <InfoCircleOutlined style={{ color: '#1890ff', marginRight: 8 }} />
                        {item}
                      </List.Item>
                    )}
                  />
                }
                type="info"
                showIcon
              />
            )}
          </Space>
        )}
      </Modal>
    </div>
  )
}
