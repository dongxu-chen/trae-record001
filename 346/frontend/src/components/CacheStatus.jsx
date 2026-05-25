import { useState, useEffect } from 'react'
import { Card, Button, Space, Statistic, Progress, Tag, message, Tooltip, Typography, Row, Col, Modal } from 'antd'
import { ReloadOutlined, ClearOutlined, DatabaseOutlined, ThunderboltOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { graphApi } from '../services/api'

const { Text, Title } = Typography

const CacheStatus = ({ onDataChange }) => {
  const [cacheStatus, setCacheStatus] = useState(null)
  const [performanceInfo, setPerformanceInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [detailModalVisible, setDetailModalVisible] = useState(false)

  const loadStatus = async () => {
    try {
      const [cache, perf] = await Promise.all([
        graphApi.getCacheStatus(),
        graphApi.getPerformanceInfo()
      ])
      setCacheStatus(cache)
      setPerformanceInfo(perf)
    } catch (error) {
      console.error('加载缓存状态失败', error)
    }
  }

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleRefreshCache = async () => {
    try {
      setLoading(true)
      await graphApi.refreshCache()
      message.success('缓存刷新成功')
      loadStatus()
      onDataChange?.()
    } catch (error) {
      message.error('缓存刷新失败')
    } finally {
      setLoading(false)
    }
  }

  const handleClearCache = async () => {
    Modal.confirm({
      title: '确认清除缓存',
      content: '清除缓存后，下次访问需要重新计算，可能会变慢。确定要清除吗？',
      onOk: async () => {
        try {
          setLoading(true)
          await graphApi.clearCache()
          message.success('缓存已清除')
          loadStatus()
        } catch (error) {
          message.error('清除缓存失败')
        } finally {
          setLoading(false)
        }
      }
    })
  }

  if (!cacheStatus || !performanceInfo) {
    return null
  }

  const hitRatePercent = Math.round(cacheStatus.hit_rate * 100)
  const getHitRateColor = () => {
    if (hitRatePercent >= 80) return '#52c41a'
    if (hitRatePercent >= 50) return '#faad14'
    return '#ff4d4f'
  }

  return (
    <Card
      size="small"
      title={
        <Space>
          <DatabaseOutlined />
          <span>系统状态</span>
          <Tooltip title="查看详细信息">
            <InfoCircleOutlined 
              style={{ color: '#1890ff', cursor: 'pointer' }} 
              onClick={() => setDetailModalVisible(true)}
            />
          </Tooltip>
        </Space>
      }
      extra={
        <Space size="small">
          <Tooltip title="刷新预计算缓存">
            <Button 
              size="small" 
              icon={<ReloadOutlined />} 
              onClick={handleRefreshCache}
              loading={loading}
            >
              刷新缓存
            </Button>
          </Tooltip>
          <Tooltip title="清除所有缓存">
            <Button 
              size="small" 
              icon={<ClearOutlined />} 
              onClick={handleClearCache}
              danger
            >
              清除
            </Button>
          </Tooltip>
        </Space>
      }
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Row gutter={[8, 8]}>
          <Col span={12}>
            <Statistic
              title="缓存命中率"
              value={hitRatePercent}
              suffix="%"
              valueStyle={{ color: getHitRateColor(), fontSize: '18px' }}
              prefix={<ThunderboltOutlined />}
            />
            <Progress 
              percent={hitRatePercent} 
              size="small" 
              strokeColor={getHitRateColor()}
              showInfo={false}
              style={{ marginTop: 4 }}
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="缓存条目"
              value={cacheStatus.total_entries}
              valueStyle={{ fontSize: '18px' }}
              prefix={<DatabaseOutlined />}
            />
            <Text type="secondary" style={{ fontSize: '11px' }}>
              {cacheStatus.total_size_mb.toFixed(2)} MB
            </Text>
          </Col>
        </Row>

        <div style={{ paddingTop: 8, borderTop: '1px solid #f0f0f0' }}>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text type="secondary" style={{ fontSize: '12px' }}>PageRank算法</Text>
              <Tag color={performanceInfo.graph.pagerank_method === 'sparse_matrix' ? 'green' : 'orange'}>
                {performanceInfo.graph.pagerank_method === 'sparse_matrix' ? '稀疏矩阵(低内存)' : 'NetworkX'}
              </Tag>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text type="secondary" style={{ fontSize: '12px' }}>社区算法</Text>
              <Tag color={performanceInfo.graph.community_algorithm === 'leiden' ? 'green' : 'orange'}>
                {performanceInfo.graph.community_algorithm === 'leiden' ? 'Leiden(快10x)' : 'Louvain'}
              </Tag>
            </div>
          </Space>
        </div>
      </Space>

      <Modal
        title="系统详细信息"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={600}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={5}>缓存统计</Title>
            <Row gutter={[16, 16]}>
              <Col span={8}>
                <Statistic title="缓存命中" value={cacheStatus.hits} />
              </Col>
              <Col span={8}>
                <Statistic title="缓存未命中" value={cacheStatus.misses} />
              </Col>
              <Col span={8}>
                <Statistic title="缓存淘汰" value={cacheStatus.evictions} />
              </Col>
            </Row>
          </div>

          <div>
            <Title level={5}>算法配置</Title>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>Scipy可用</Text>
                <Tag color={performanceInfo.graph.scipy_available ? 'green' : 'red'}>
                  {performanceInfo.graph.scipy_available ? '是' : '否'}
                </Tag>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>Leiden算法可用</Text>
                <Tag color={performanceInfo.graph.leiden_available ? 'green' : 'red'}>
                  {performanceInfo.graph.leiden_available ? '是' : '否'}
                </Tag>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>Louvain算法可用</Text>
                <Tag color={performanceInfo.graph.louvain_available ? 'green' : 'red'}>
                  {performanceInfo.graph.louvain_available ? '是' : '否'}
                </Tag>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text>缓存启用</Text>
                <Tag color={performanceInfo.graph.cache_enabled ? 'green' : 'red'}>
                  {performanceInfo.graph.cache_enabled ? '是' : '否'}
                </Tag>
              </div>
            </Space>
          </div>

          <div>
            <Title level={5}>缓存条目详情</Title>
            {cacheStatus.entries && cacheStatus.entries.length > 0 ? (
              <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                {cacheStatus.entries.map((entry, idx) => (
                  <div key={idx} style={{ 
                    padding: '8px', 
                    borderBottom: '1px solid #f0f0f0',
                    fontSize: '12px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Text code>{entry.key.slice(0, 20)}...</Text>
                      <Space>
                        <Tag>{(entry.size / 1024).toFixed(1)} KB</Tag>
                        <Tag color="blue">命中 {entry.hit_count} 次</Tag>
                      </Space>
                    </div>
                    <Text type="secondary">
                      存活 {Math.round(entry.age)}s / TTL {entry.ttl}s
                    </Text>
                  </div>
                ))}
              </div>
            ) : (
              <Text type="secondary">暂无缓存条目</Text>
            )}
          </div>
        </Space>
      </Modal>
    </Card>
  )
}

export default CacheStatus
