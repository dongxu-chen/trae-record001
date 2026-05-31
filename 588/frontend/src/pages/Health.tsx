import { useEffect, useState } from 'react'
import { Card, Progress, Row, Col, List, Tag, Spin, Typography } from 'antd'
import { HeartOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons'
import { getHealthScore, type HealthScore } from '../services/api'

const { Title, Text } = Typography

const getGradeColor = (grade: string) => {
  const colors: Record<string, string> = {
    A: '#52c41a',
    B: '#1890ff',
    C: '#faad14',
    D: '#fa8c16',
    F: '#f5222d',
  }
  return colors[grade] || '#666'
}

const getCategoryLabel = (category: string) => {
  const labels: Record<string, string> = {
    node_count: '节点数量',
    data_size: '数据大小',
    path_depth: '路径深度',
    alerts: '预警数量',
    distribution: '节点分布',
    growth: '增长趋势',
  }
  return labels[category] || category
}

const Health = () => {
  const [loading, setLoading] = useState(true)
  const [healthScore, setHealthScore] = useState<HealthScore | null>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await getHealthScore()
      setHealthScore(data)
    } catch (error) {
      console.error('Failed to load health score:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 60000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!healthScore) {
    return <div>暂无数据</div>
  }

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>集群健康评分</h2>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={8}>
          <Card style={{ textAlign: 'center' }}>
            <div style={{ position: 'relative', display: 'inline-block' }}>
              <Progress
                type="circle"
                percent={healthScore.overall_score}
                size={180}
                strokeColor={getGradeColor(healthScore.grade)}
                format={() => (
                  <div>
                    <HeartOutlined style={{ fontSize: 24, color: getGradeColor(healthScore.grade) }} />
                    <Title level={2} style={{ margin: 0, color: getGradeColor(healthScore.grade) }}>
                      {healthScore.grade}
                    </Title>
                  </div>
                )}
              />
            </div>
            <div style={{ marginTop: 16 }}>
              <Title level={4} style={{ marginBottom: 8 }}>综合健康评分</Title>
              <Text type="secondary">{healthScore.overall_score.toFixed(1)} 分</Text>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          <Card title="分项评分">
            <Row gutter={[16, 16]}>
              {Object.entries(healthScore.category_scores).map(([category, score]) => (
                <Col xs={24} md={12} key={category}>
                  <Card size="small" style={{ background: '#fafafa' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text strong>{getCategoryLabel(category)}</Text>
                      <Tag color={score >= 80 ? 'green' : score >= 60 ? 'orange' : 'red'}>
                        {score.toFixed(1)} 分
                      </Tag>
                    </div>
                    <Progress
                      percent={score}
                      showInfo={false}
                      strokeColor={score >= 80 ? '#52c41a' : score >= 60 ? '#faad14' : '#f5222d'}
                      style={{ marginTop: 8 }}
                    />
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <span>
                <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
                风险预警
              </span>
            }
          >
            {healthScore.warnings.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '20px', color: '#52c41a' }}>
                <CheckCircleOutlined style={{ fontSize: 32, marginBottom: 8 }} />
                <p>当前无风险预警</p>
              </div>
            ) : (
              <List
                dataSource={healthScore.warnings}
                renderItem={(warning) => (
                  <List.Item>
                    <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
                    <span>{warning}</span>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title={
              <span>
                <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                运维建议
              </span>
            }
          >
            <List
              dataSource={healthScore.recommendations}
              renderItem={(rec) => (
                <List.Item>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  <span>{rec}</span>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Health
