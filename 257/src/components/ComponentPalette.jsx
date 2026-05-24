import React from 'react'
import { useDraggable } from '@dnd-kit/core'

const componentTypes = [
  { type: 'chart', label: '图表', icon: '📊', description: '折线图、柱状图、饼图等' },
  { type: 'metric', label: '指标卡', icon: '📈', description: '显示关键指标和趋势' },
  { type: 'table', label: '表格', icon: '📋', description: '展示详细数据列表' },
  { type: 'filter', label: '筛选器', icon: '🔍', description: '联动筛选其他组件' },
]

function DraggableItem({ type, label, icon, description }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `palette-${type}`,
    data: {
      type,
      fromPalette: true,
    },
  })

  const style = {
    transform: transform ? `translate3d(${transform.x}px, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="palette-item"
    >
      <span className="palette-icon">{icon}</span>
      <div className="palette-info">
        <div className="palette-label">{label}</div>
        <div className="palette-desc">{description}</div>
      </div>
    </div>
  )
}

export default function ComponentPalette({ onOpenMarket }) {
  return (
    <div className="component-palette">
      <h3 className="palette-title">组件库</h3>
      <p className="palette-hint">拖拽组件到右侧画布</p>
      <div className="palette-list">
        {componentTypes.map((item) => (
          <DraggableItem key={item.type} {...item} />
        ))}
      </div>
      <div className="palette-footer">
        <button className="market-entry-btn" onClick={onOpenMarket}>
          🏪 浏览更多组件
        </button>
      </div>
    </div>
  )
}
