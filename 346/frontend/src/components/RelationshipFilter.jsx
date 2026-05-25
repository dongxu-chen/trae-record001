import { useState, useEffect, useMemo } from 'react'
import { Checkbox, Space, Typography, Tag, Spin, Empty, Alert, Button } from 'antd'
import { FilterOutlined, ReloadOutlined } from '@ant-design/icons'
import { graphApi } from '../services/api'

const { Text } = Typography
const { Group: CheckboxGroup } = Checkbox

const RELATIONSHIP_TYPES = [
  { value: 'FOLLOW', label: '关注', color: '#1890ff' },
  { value: 'LIKE', label: '点赞', color: '#52c41a' },
  { value: 'COMMENT', label: '评论', color: '#faad14' },
  { value: 'FRIEND', label: '好友', color: '#722ed1' },
  { value: 'COLLEAGUE', label: '同事', color: '#eb2f96' },
]

const RelationshipFilter = ({ value = [], onChange, disabled = false }) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [typeStats, setTypeStats] = useState({})

  useEffect(() => {
    loadRelationshipStats()
  }, [])

  const loadRelationshipStats = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await graphApi.getRelationshipTypes()
      if (data?.stats) {
        setTypeStats(data.stats)
      }
    } catch (err) {
      setError('加载关系类型统计失败')
      console.error('Relationship types error:', err)
    } finally {
      setLoading(false)
    }
  }

  const allTypes = useMemo(() => {
    return RELATIONSHIP_TYPES.map((type) => type.value)
  }, [])

  const handleChange = (checkedValues) => {
    onChange?.(checkedValues)
  }

  const handleSelectAll = () => {
    onChange?.(allTypes)
  }

  const handleClear = () => {
    onChange?.([])
  }

  const getTypeColor = (typeValue) => {
    const type = RELATIONSHIP_TYPES.find((t) => t.value === typeValue)
    return type?.color || '#999'
  }

  const getTypeLabel = (typeValue) => {
    const type = RELATIONSHIP_TYPES.find((t) => t.value === typeValue)
    return type?.label || typeValue
  }

  const totalEdges = useMemo(() => {
    return Object.values(typeStats).reduce((sum, count) => sum + count, 0)
  }, [typeStats])

  const selectedCount = useMemo(() => {
    return value.reduce((sum, type) => sum + (typeStats[type] || 0), 0)
  }, [value, typeStats])

  if (loading) {
    return (
      <div className="loading-container">
        <Spin size="small" tip="加载中..." />
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <Alert type="error" message={error} showIcon />
        <Button
          type="link"
          icon={<ReloadOutlined />}
          onClick={loadRelationshipStats}
          style={{ padding: 0, marginTop: 8 }}
        >
          重试
        </Button>
      </div>
    )
  }

  return (
    <div className="relationship-filter">
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <FilterOutlined style={{ color: '#1890ff' }} />
            <Text strong>关系类型过滤</Text>
          </Space>
          <Space>
            <Button type="link" size="small" onClick={handleSelectAll} disabled={disabled}>
              全选
            </Button>
            <Button type="link" size="small" onClick={handleClear} disabled={disabled}>
              清空
            </Button>
          </Space>
        </div>

        {totalEdges > 0 && (
          <div className="filter-summary">
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  总边数: <Text strong>{totalEdges}</Text>
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  已选: <Text strong style={{ color: '#1890ff' }}>{selectedCount}</Text>
                  <Text type="secondary"> ({value.length}/{RELATIONSHIP_TYPES.length} 类型)</Text>
                </Text>
              </div>
            </Space>
          </div>
        )}

        <CheckboxGroup
          value={value}
          onChange={handleChange}
          disabled={disabled}
          style={{ width: '100%' }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            {RELATIONSHIP_TYPES.map((type) => {
              const count = typeStats[type.value] || 0
              const isSelected = value.includes(type.value)
              return (
                <div
                  key={type.value}
                  className={`filter-item ${isSelected ? 'selected' : ''}`}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 12px',
                    borderRadius: 4,
                    background: isSelected ? `${type.color}10` : 'transparent',
                    transition: 'all 0.3s',
                  }}
                >
                  <Space>
                    <Checkbox value={type.value} disabled={disabled}>
                      <Space>
                        <span
                          style={{
                            display: 'inline-block',
                            width: 10,
                            height: 10,
                            borderRadius: '50%',
                            background: type.color,
                          }}
                        />
                        <Text>{type.label}</Text>
                      </Space>
                    </Checkbox>
                  </Space>
                  <Tag
                    color={isSelected ? type.color : 'default'}
                    style={{ margin: 0 }}
                  >
                    {count} 条
                  </Tag>
                </div>
              )
            })}
          </Space>
        </CheckboxGroup>

        {value.length === 0 && (
          <Empty
            description={
              <Text type="secondary" style={{ fontSize: 12 }}>
                未选择任何类型，图表将不显示边
              </Text>
            }
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ padding: '12px 0', margin: 0 }}
          />
        )}
      </Space>
    </div>
  )
}

export { RELATIONSHIP_TYPES }
export default RelationshipFilter
