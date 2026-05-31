import { useEffect, useState } from 'react'
import { Card, List, Tag, Button, Spin, Collapse, Typography, Alert } from 'antd'
import {
  BulbOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  RocketOutlined,
  DatabaseOutlined,
  NodeIndexOutlined,
  BranchesOutlined,
  FileTextOutlined,
  ToolOutlined,
  FolderOpenOutlined,
} from '@ant-design/icons'
import { getRecommendations, type Recommendation } from '../services/api'

const { Panel } = Collapse
const { Text, Paragraph } = Typography

const Recommendations = () => {
  const [loading, setLoading] = useState(true)
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])

  const loadData = async () => {
    try {
      setLoading(true)
      const data = await getRecommendations()
      setRecommendations(data || [])
    } catch (error) {
      console.error('Failed to load recommendations:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return <ExclamationCircleOutlined style={{ color: '#f5222d', fontSize: 24 }} />
      case 'medium':
        return <WarningOutlined style={{ color: '#faad14', fontSize: 24 }} />
      case 'low':
        return <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 24 }} />
      default:
        return <BulbOutlined style={{ color: '#52c41a', fontSize: 24 }} />
    }
  }

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      high: 'red',
      medium: 'orange',
      low: 'blue',
    }
    return colors[severity] || 'default'
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'data_size':
        return <DatabaseOutlined />
      case 'node_count':
        return <NodeIndexOutlined />
      case 'path_depth':
        return <BranchesOutlined />
      case 'ephemeral':
        return <RocketOutlined />
      case 'large_nodes':
        return <FileTextOutlined />
      case 'many_children':
        return <FolderOpenOutlined />
      default:
        return <BulbOutlined />
    }
  }

  const getCategoryLabel = (category: string) => {
    const labels: Record<string, string> = {
      data_size: '数据大小',
      node_count: '节点数量',
      path_depth: '路径深度',
      ephemeral: '临时节点',
      large_nodes: '大节点',
      many_children: '子节点过多',
    }
    return labels[category] || category
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  const bestPractices = [
    {
      title: '节点数据大小',
      content: '建议单个ZNode数据大小不超过1MB。大数据应存储在外部数据库，ZooKeeper仅存储元数据和引用。',
    },
    {
      title: '子节点数量',
      content: '单个节点的子节点数量建议不超过1000个。过多子节点会影响watch机制和序列化性能。',
    },
    {
      title: '路径深度',
      content: '建议ZNode路径深度不超过10层。深层路径会增加网络开销和查询时间。',
    },
    {
      title: '临时节点管理',
      content: '及时清理不再需要的临时节点，避免会话过期前占用内存。合理设置会话超时时间。',
    },
    {
      title: 'Watch使用',
      content: '避免在大量节点上设置watch，这会增加服务端内存压力。使用一次性watch后及时重新设置。',
    },
    {
      title: '事务批量操作',
      content: '使用multi()进行批量操作，减少网络往返。但注意事务大小也应控制。',
    },
  ]

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>优化建议</h2>

      <Card title="当前优化建议" style={{ marginBottom: 24 }}>
        {recommendations.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#52c41a' }}>
            <BulbOutlined style={{ fontSize: 48, marginBottom: 16 }} />
            <p>系统运行良好，暂无优化建议</p>
          </div>
        ) : (
          <List
            dataSource={recommendations}
            renderItem={(item) => (
              <List.Item
                style={{ alignItems: 'flex-start' }}
                actions={[
                  <Tag key="category" icon={getCategoryIcon(item.category)}>
                    {getCategoryLabel(item.category)}
                  </Tag>,
                  <Tag key="severity" color={getSeverityColor(item.severity)}>
                    {item.severity === 'high' ? '高优先级' : item.severity === 'medium' ? '中优先级' : '低优先级'}
                  </Tag>,
                ]}
              >
                <List.Item.Meta
                  avatar={getSeverityIcon(item.severity)}
                  title={<strong style={{ fontSize: 16 }}>{item.title}</strong>}
                  description={
                    <div style={{ width: '100%' }}>
                      <Paragraph style={{ marginBottom: 12 }}>
                        <Text strong>问题描述：</Text>
                        {item.message}
                      </Paragraph>

                      <Alert
                        message={<Text strong>建议行动：{item.action}</Text>}
                        type="info"
                        showIcon
                        style={{ marginBottom: 12 }}
                      />

                      {item.solutions && item.solutions.length > 0 && (
                        <div style={{ marginBottom: 12 }}>
                          <Text strong style={{ display: 'block', marginBottom: 8 }}>
                            <BulbOutlined /> 解决方案：
                          </Text>
                          <ul style={{ paddingLeft: 20, marginBottom: 0 }}>
                            {item.solutions.map((sol, idx) => (
                              <li key={idx} style={{ marginBottom: 4 }}>
                                <Text>{sol}</Text>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {item.scripts && item.scripts.length > 0 && (
                        <div style={{ marginBottom: 12 }}>
                          <Text strong style={{ display: 'block', marginBottom: 8 }}>
                            <ToolOutlined /> 工具与脚本：
                          </Text>
                          <ul style={{ paddingLeft: 20, marginBottom: 0 }}>
                            {item.scripts.map((script, idx) => (
                              <li key={idx} style={{ marginBottom: 4 }}>
                                <Text type="secondary">{script}</Text>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {(item.affected_paths || item.affected_nodes) && (
                        <div style={{ marginTop: 8 }}>
                          <Text type="warning" strong>
                            受影响的{
                              item.affected_paths && item.affected_paths.length > 0 ? '路径' : '节点'
                            }：
                          </Text>
                          <div style={{ marginTop: 4 }}>
                            {(item.affected_paths || item.affected_nodes || []).slice(0, 3).map((path, idx) => (
                              <Tag key={idx} style={{ marginBottom: 4 }}>
                                <code>{path}</code>
                              </Tag>
                            ))}
                            {(item.affected_paths?.length || item.affected_nodes?.length || 0) > 3 && (
                              <Tag>等 {(item.affected_paths?.length || item.affected_nodes?.length || 0) - 3} 个</Tag>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>

      <Card title="ZooKeeper 最佳实践">
        <Collapse accordion>
          {bestPractices.map((practice, index) => (
            <Panel header={practice.title} key={index}>
              <p style={{ margin: 0 }}>{practice.content}</p>
            </Panel>
          ))}
        </Collapse>
      </Card>

      <Card
        title="外部资源"
        style={{ marginTop: 24 }}
      >
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <Button type="primary" href="https://zookeeper.apache.org/doc/current/zookeeperAdmin.html" target="_blank">
            官方管理员指南
          </Button>
          <Button href="https://cwiki.apache.org/confluence/display/ZOOKEEPER/FAQ" target="_blank">
            常见问题 FAQ
          </Button>
          <Button href="https://zookeeper.apache.org/doc/current/zookeeperProgrammers.html" target="_blank">
            程序员指南
          </Button>
          <Button href="https://www.youtube.com/watch?v=Kwwt512K6Kc" target="_blank">
            Netflix 运维经验分享
          </Button>
        </div>
      </Card>
    </div>
  )
}

export default Recommendations
