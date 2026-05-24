import React, { useMemo, useState, useEffect } from 'react'
import { eventBus, EVENTS } from '../../utils/eventBus'

export default function TableWidget({ config }) {
  const { columns = ['名称', '数值', '状态'], data = [] } = config
  const [localFilters, setLocalFilters] = useState({})

  useEffect(() => {
    const handleFilterChanged = ({ key, value }) => {
      setLocalFilters(prev => ({ ...prev, [key]: value }))
    }

    const handleFilterCleared = () => {
      setLocalFilters({})
    }

    const unsubscribeFilter = eventBus.on(EVENTS.FILTER_CHANGED, handleFilterChanged)
    const unsubscribeClear = eventBus.on(EVENTS.FILTER_CLEARED, handleFilterCleared)

    return () => {
      unsubscribeFilter()
      unsubscribeClear()
    }
  }, [])

  const filteredData = useMemo(() => {
    let result = [...data]
    const categoryFilter = localFilters.category
    if (categoryFilter && categoryFilter !== '全部') {
      result = result.filter((d) => d.category === categoryFilter)
    }
    return result
  }, [data, localFilters])

  const getStatusStyle = (status) => {
    switch (status) {
      case '热销':
        return { background: '#e6f7ff', color: '#1890ff' }
      case '正常':
        return { background: '#f6ffed', color: '#52c41a' }
      case '滞销':
        return { background: '#fff1f0', color: '#f5222d' }
      default:
        return { background: '#fafafa', color: '#666' }
    }
  }

  return (
    <div className="table-widget">
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filteredData.map((row) => (
            <tr key={row.id}>
              <td>{row.name}</td>
              <td>{row.value}</td>
              <td>
                <span className="status-tag" style={getStatusStyle(row.status)}>
                  {row.status}
                </span>
              </td>
            </tr>
          ))}
          {filteredData.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="empty-row">
                暂无数据
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
