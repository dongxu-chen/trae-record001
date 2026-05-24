import React, { useState } from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useDispatch, useSelector } from 'react-redux'
import { removeComponent, updateComponentTitle, updateComponentConfig } from '../store/dashboardSlice'
import ChartWidget from './widgets/ChartWidget'
import MetricWidget from './widgets/MetricWidget'
import TableWidget from './widgets/TableWidget'
import FilterWidget from './widgets/FilterWidget'
import CustomWidget from './widgets/CustomWidget'
import { GRID_CONFIG } from '../utils/gridSystem'

export default function DashboardItem({ component }) {
  const dispatch = useDispatch()
  const alerts = useSelector((state) => state.dashboard.alerts)
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(component.title)
  const [showConfig, setShowConfig] = useState(false)

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: component.id,
    data: {
      type: component.type,
      component,
    },
  })

  const position = component.position || { col: 0, row: 0, width: 6, height: 4 }
  const gridStyle = {
    gridColumn: `${position.col + 1} / span ${position.width}`,
    gridRow: `${position.row + 1} / span ${position.height}`,
  }

  const activeAlert = alerts.find(a =>
    a.enabled && a.isActive && a.metricName === component.title
  )

  const style = {
    ...gridStyle,
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 1000 : 1,
  }

  const renderWidget = () => {
    switch (component.type) {
      case 'chart':
        return <ChartWidget config={component.config} />
      case 'metric':
        return <MetricWidget config={component.config} />
      case 'table':
        return <TableWidget config={component.config} />
      case 'filter':
        return <FilterWidget id={component.id} config={component.config} />
      case 'custom':
        return <CustomWidget config={component.config} title={component.title} />
      default:
        return <div>未知组件类型</div>
    }
  }

  const handleRemove = (e) => {
    e.stopPropagation()
    dispatch(removeComponent(component.id))
  }

  const handleTitleBlur = () => {
    if (editTitle.trim()) {
      dispatch(updateComponentTitle({ id: component.id, title: editTitle }))
    } else {
      setEditTitle(component.title)
    }
    setIsEditing(false)
  }

  const handleChartTypeChange = (e) => {
    dispatch(updateComponentConfig({
      id: component.id,
      config: { chartType: e.target.value }
    }))
  }

  const handleDataKeyChange = (e) => {
    dispatch(updateComponentConfig({
      id: component.id,
      config: { dataKey: e.target.value }
    }))
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`dashboard-item ${isDragging ? 'dragging' : ''} ${activeAlert ? `alert-${activeAlert.severity}` : ''}`}
    >
      {activeAlert && (
        <div className="alert-badge" style={{ backgroundColor: activeAlert.severity === 'danger' ? '#f5222d' : '#faad14' }}>
          ⚠️ 预警
        </div>
      )}
      <div className="item-header" {...attributes} {...listeners}>
        <div className="item-title">
          {isEditing ? (
            <input
              className="title-input"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={handleTitleBlur}
              onKeyDown={(e) => e.key === 'Enter' && handleTitleBlur()}
              autoFocus
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <span onDoubleClick={() => setIsEditing(true)}>{component.title}</span>
          )}
        </div>
        <div className="item-actions">
          {component.type === 'chart' && (
            <button
              className="action-btn"
              onClick={(e) => { e.stopPropagation(); setShowConfig(!showConfig) }}
              title="配置"
            >
              ⚙️
            </button>
          )}
          <button
            className="action-btn remove-btn"
            onClick={handleRemove}
            title="删除"
          >
            ✕
          </button>
        </div>
      </div>

      {showConfig && component.type === 'chart' && (
        <div className="item-config" onClick={(e) => e.stopPropagation()}>
          <div className="config-row">
            <label>图表类型:</label>
            <select value={component.config.chartType} onChange={handleChartTypeChange}>
              <option value="line">折线图</option>
              <option value="bar">柱状图</option>
              <option value="pie">饼图</option>
            </select>
          </div>
          <div className="config-row">
            <label>数据源:</label>
            <select value={component.config.dataKey} onChange={handleDataKeyChange}>
              <option value="sales">销售数据</option>
              <option value="users">用户数据</option>
              <option value="category">类别分布</option>
            </select>
          </div>
        </div>
      )}

      <div className="item-content">
        {renderWidget()}
      </div>
    </div>
  )
}
