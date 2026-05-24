import React, { useRef, useState, useMemo } from 'react'
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
  useDroppable,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
} from '@dnd-kit/sortable'
import { useSelector, useDispatch } from 'react-redux'
import { addComponent, updateComponentPosition } from '../store/dashboardSlice'
import DashboardItem from './DashboardItem'
import { GRID_CONFIG, findDropZone, findNextAvailablePosition } from '../utils/gridSystem'

function GridCanvas({ children, isDragActive, dropPreview }) {
  const { setNodeRef } = useDroppable({
    id: 'dashboard-canvas',
  })

  const gridLines = useMemo(() => {
    const lines = []
    for (let i = 0; i <= GRID_CONFIG.COLUMNS; i++) {
      lines.push({ type: 'vertical', index: i })
    }
    return lines
  }, [])

  return (
    <div
      ref={setNodeRef}
      className={`dashboard-canvas ${isDragActive ? 'drag-active' : ''}`}
    >
      {isDragActive && (
        <div className="grid-overlay">
          {gridLines.map((line) => (
            <div
              key={`${line.type}-${line.index}`}
              className="grid-line vertical"
              style={{ left: `${(line.index / GRID_CONFIG.COLUMNS) * 100}%` }}
            />
          ))}
          {dropPreview && (
            <div
              className="drop-preview"
              style={{
                left: `${(dropPreview.col / GRID_CONFIG.COLUMNS) * 100}%`,
                top: `${dropPreview.row * (GRID_CONFIG.ROW_HEIGHT + GRID_CONFIG.GAP)}px`,
                width: `${(dropPreview.width / GRID_CONFIG.COLUMNS) * 100}%`,
                height: `${dropPreview.height * GRID_CONFIG.ROW_HEIGHT + (dropPreview.height - 1) * GRID_CONFIG.GAP}px`,
              }}
            />
          )}
        </div>
      )}
      {children}
    </div>
  )
}

export default function DashboardCanvas() {
  const dispatch = useDispatch()
  const components = useSelector((state) => state.dashboard.components)
  const [activeId, setActiveId] = useState(null)
  const [activeData, setActiveData] = useState(null)
  const [dropPreview, setDropPreview] = useState(null)
  const canvasRef = useRef(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragStart = (event) => {
    const { active } = event
    setActiveId(active.id)
    setActiveData(active.data.current)
  }

  const handleDragMove = (event) => {
    const { active, delta } = event

    if (!canvasRef.current) return

    const canvasRect = canvasRef.current.getBoundingClientRect()
    const pointerX = event.activatorEvent.clientX
    const pointerY = event.activatorEvent.clientY

    if (
      pointerX >= canvasRect.left &&
      pointerX <= canvasRect.right &&
      pointerY >= canvasRect.top &&
      pointerY <= canvasRect.bottom
    ) {
      const preview = findDropZone(
        pointerX,
        pointerY,
        canvasRect,
        components,
        active.id
      )
      setDropPreview(preview)
    } else {
      setDropPreview(null)
    }
  }

  const handleDragEnd = (event) => {
    const { active, over } = event

    if (active.data.current?.fromPalette && over && dropPreview) {
      const type = active.data.current.type
      const position = {
        col: dropPreview.col,
        row: dropPreview.row,
        width: dropPreview.width,
        height: dropPreview.height,
      }
      dispatch(addComponent({ type, position }))
    } else if (activeId && !active.data.current?.fromPalette && dropPreview) {
      dispatch(updateComponentPosition({
        id: activeId,
        position: {
          col: dropPreview.col,
          row: dropPreview.row,
          width: dropPreview.width,
          height: dropPreview.height,
        }
      }))
    }

    setActiveId(null)
    setActiveData(null)
    setDropPreview(null)
  }

  const getItemById = (id) => {
    return components.find((c) => c.id === id)
  }

  const isDragActive = activeId !== null

  return (
    <div className="dashboard-canvas-wrapper" ref={canvasRef}>
      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragMove={handleDragMove}
        onDragEnd={handleDragEnd}
      >
        <GridCanvas isDragActive={isDragActive} dropPreview={dropPreview}>
          {components.length === 0 ? (
            <div className="empty-canvas">
              <div className="empty-icon">📊</div>
              <h3>仪表板画布</h3>
              <p>从左侧拖拽组件到此处开始构建</p>
              <p className="empty-hint">拖拽时会显示栅格线，释放后自动吸附</p>
            </div>
          ) : (
            <SortableContext items={components.map((c) => c.id)} strategy={rectSortingStrategy}>
              <div className="components-grid">
                {components.map((component) => (
                  <DashboardItem key={component.id} component={component} />
                ))}
              </div>
            </SortableContext>
          )}
        </GridCanvas>

        <DragOverlay>
          {activeId && activeData?.fromPalette && (
            <div className="drag-overlay-item">
              <span className="overlay-icon">
                {activeData.type === 'chart' && '📊'}
                {activeData.type === 'metric' && '📈'}
                {activeData.type === 'table' && '📋'}
                {activeData.type === 'filter' && '🔍'}
              </span>
              <span className="overlay-label">
                {activeData.type === 'chart' && '图表'}
                {activeData.type === 'metric' && '指标卡'}
                {activeData.type === 'table' && '表格'}
                {activeData.type === 'filter' && '筛选器'}
              </span>
            </div>
          )}
          {activeId && !activeData?.fromPalette && getItemById(activeId) && (
            <div className="drag-overlay-item dragging-item">
              <span>{getItemById(activeId).title}</span>
            </div>
          )}
        </DragOverlay>
      </DndContext>
    </div>
  )
}
