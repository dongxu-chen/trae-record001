import { useMemo } from 'react'
import { List, Tag, Empty, Typography, Progress, Tooltip, Space } from 'antd'
import * as d3 from 'd3'

const { Text } = Typography

const CommunityPanel = ({ communities = [] }) => {
  const colorScale = d3.scaleOrdinal(d3.schemeCategory10)

  const sortedCommunities = useMemo(() => {
    return [...communities].sort((a, b) => b.size - a.size)
  }, [communities])

  const totalNodes = useMemo(() => {
    return communities.reduce((sum, c) => sum + c.size, 0)
  }, [communities])

  if (communities.length === 0) {
    return <Empty description="暂无社区数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <div>
      {communities[0]?.modularity !== undefined && (
        <div style={{ marginBottom: 12, padding: '8px 12px', background: '#f0f5ff', borderRadius: 4 }}>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>模块度</Text>
              <Text strong>{communities[0].modularity.toFixed(4)}</Text>
            </div>
            <Progress
              percent={Math.abs(communities[0].modularity) * 100}
              size="small"
              showInfo={false}
              strokeColor={communities[0].modularity > 0.3 ? '#52c41a' : '#faad14'}
            />
          </Space>
        </div>
      )}

      <div style={{ marginBottom: 12, fontSize: 12, color: '#666' }}>
        共检测到 <Text strong>{communities.length}</Text> 个社区，
        <Text strong>{totalNodes}</Text> 个节点
      </div>

      <List
        size="small"
        dataSource={sortedCommunities}
        renderItem={(community, index) => {
          const percentage = totalNodes > 0 ? (community.size / totalNodes) * 100 : 0
          return (
            <List.Item
              style={{
                padding: '10px 0',
                borderBottom: '1px solid #f0f0f0',
              }}
            >
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <Space>
                    <span
                      style={{
                        display: 'inline-block',
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        background: colorScale(index),
                      }}
                    />
                    <Text strong>社区 {community.id + 1}</Text>
                  </Space>
                  <Space>
                    <Tag color="blue">{community.size} 节点</Tag>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {percentage.toFixed(1)}%
                    </Text>
                  </Space>
                </div>
                <Progress
                  percent={percentage}
                  size="small"
                  showInfo={false}
                  strokeColor={colorScale(index)}
                  trailColor="#f0f0f0"
                />
                <Tooltip title={community.nodes.join(', ')}>
                  <Text
                    type="secondary"
                    style={{
                      fontSize: 11,
                      display: 'block',
                      marginTop: 4,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    节点: {community.nodes.slice(0, 5).join(', ')}
                    {community.nodes.length > 5 ? ` 等${community.nodes.length}个` : ''}
                  </Text>
                </Tooltip>
              </div>
            </List.Item>
          )
        }}
      />
    </div>
  )
}

export default CommunityPanel
