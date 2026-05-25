import { useState, useMemo } from 'react'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
  horizontalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { X, GripVertical, Plus, ChevronDown } from 'lucide-react'
import type { DataRow, PivotConfig, PivotValue } from '@/types/table'
import { generatePivotTable, getAvailableFields, getAggregatorLabel } from '@/utils/pivotTable'

interface SortableItemProps {
  id: string
  label: string
  onRemove?: () => void
}

function SortableItem({ id, label, onRemove }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm cursor-move select-none"
    >
      <GripVertical size={14} className="text-blue-400" {...attributes} {...listeners} />
      <span>{label}</span>
      {onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onRemove()
          }}
          className="ml-1 hover:bg-blue-200 rounded p-0.5"
        >
          <X size={12} />
        </button>
      )}
    </div>
  )
}

interface SortableValueItemProps {
  id: string
  value: PivotValue
  onRemove: () => void
  onAggregatorChange: (aggregator: PivotValue['aggregator']) => void
}

function SortableValueItem({ id, value, onRemove, onAggregatorChange }: SortableValueItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  const [isOpen, setIsOpen] = useState(false)

  const fieldLabel = getAvailableFields().find(f => f.key === value.field)?.label || value.field

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  const aggregators: PivotValue['aggregator'][] = ['sum', 'avg', 'count', 'min', 'max']

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 rounded text-sm cursor-move select-none"
    >
      <GripVertical size={14} className="text-green-400" {...attributes} {...listeners} />
      <span>{fieldLabel}</span>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-0.5 px-1 hover:bg-green-200 rounded"
        >
          <span className="text-xs">{getAggregatorLabel(value.aggregator)}</span>
          <ChevronDown size={12} />
        </button>
        {isOpen && (
          <div className="absolute top-full left-0 mt-1 bg-white border rounded shadow-lg z-10 min-w-20">
            {aggregators.map(agg => (
              <button
                key={agg}
                onClick={() => {
                  onAggregatorChange(agg)
                  setIsOpen(false)
                }}
                className={`block w-full text-left px-2 py-1 text-xs hover:bg-gray-100 ${
                  value.aggregator === agg ? 'bg-green-50 text-green-700' : ''
                }`}
              >
                {getAggregatorLabel(agg)}
              </button>
            ))}
          </div>
        )}
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation()
          onRemove()
        }}
        className="ml-1 hover:bg-green-200 rounded p-0.5"
      >
        <X size={12} />
      </button>
    </div>
  )
}

interface FieldSelectorProps {
  availableFields: ReturnType<typeof getAvailableFields>
  selectedKeys: string[]
  onAdd: (key: string) => void
  color: 'blue' | 'purple' | 'green'
}

function FieldSelector({ availableFields, selectedKeys, onAdd, color }: FieldSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const colorClasses = {
    blue: 'bg-blue-500 hover:bg-blue-600',
    purple: 'bg-purple-500 hover:bg-purple-600',
    green: 'bg-green-500 hover:bg-green-600',
  }

  const unselected = availableFields.filter(f => !selectedKeys.includes(f.key))

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1 px-2 py-1 ${colorClasses[color]} text-white rounded text-sm`}
      >
        <Plus size={14} />
        <span>添加</span>
      </button>
      {isOpen && unselected.length > 0 && (
        <div className="absolute top-full left-0 mt-1 bg-white border rounded shadow-lg z-10 min-w-24">
          {unselected.map(field => (
            <button
              key={field.key}
              onClick={() => {
                onAdd(field.key)
                setIsOpen(false)
              }}
              className="block w-full text-left px-2 py-1 text-sm hover:bg-gray-100"
            >
              {field.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

interface PivotTablePanelProps {
  data: DataRow[]
}

export function PivotTablePanel({ data }: PivotTablePanelProps) {
  const [config, setConfig] = useState<PivotConfig>({
    rows: ['department'],
    columns: [],
    values: [{ field: 'salary', aggregator: 'sum' }],
    filters: {},
  })

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const availableFields = getAvailableFields()

  const pivotData = useMemo(() => {
    return generatePivotTable(data, config)
  }, [data, config])

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const activeId = String(active.id)
    const overId = String(over.id)

    if (activeId.startsWith('row-') && overId.startsWith('row-')) {
      const oldIndex = config.rows.indexOf(activeId.replace('row-', ''))
      const newIndex = config.rows.indexOf(overId.replace('row-', ''))
      if (oldIndex !== -1 && newIndex !== -1) {
        setConfig(prev => ({
          ...prev,
          rows: arrayMove(prev.rows, oldIndex, newIndex),
        }))
      }
    }

    if (activeId.startsWith('col-') && overId.startsWith('col-')) {
      const oldIndex = config.columns.indexOf(activeId.replace('col-', ''))
      const newIndex = config.columns.indexOf(overId.replace('col-', ''))
      if (oldIndex !== -1 && newIndex !== -1) {
        setConfig(prev => ({
          ...prev,
          columns: arrayMove(prev.columns, oldIndex, newIndex),
        }))
      }
    }

    if (activeId.startsWith('val-') && overId.startsWith('val-')) {
      const oldIndex = config.values.findIndex(v => `val-${v.field}` === activeId)
      const newIndex = config.values.findIndex(v => `val-${v.field}` === overId)
      if (oldIndex !== -1 && newIndex !== -1) {
        setConfig(prev => ({
          ...prev,
          values: arrayMove(prev.values, oldIndex, newIndex),
        }))
      }
    }
  }

  const addRow = (key: string) => {
    setConfig(prev => ({ ...prev, rows: [...prev.rows, key] }))
  }

  const removeRow = (key: string) => {
    setConfig(prev => ({ ...prev, rows: prev.rows.filter(r => r !== key) }))
  }

  const addColumn = (key: string) => {
    setConfig(prev => ({ ...prev, columns: [...prev.columns, key] }))
  }

  const removeColumn = (key: string) => {
    setConfig(prev => ({ ...prev, columns: prev.columns.filter(c => c !== key) }))
  }

  const addValue = (key: string) => {
    if (!config.values.find(v => v.field === key)) {
      setConfig(prev => ({
        ...prev,
        values: [...prev.values, { field: key, aggregator: 'sum' }],
      }))
    }
  }

  const removeValue = (field: string) => {
    setConfig(prev => ({
      ...prev,
      values: prev.values.filter(v => v.field !== field),
    }))
  }

  const changeAggregator = (field: string, aggregator: PivotValue['aggregator']) => {
    setConfig(prev => ({
      ...prev,
      values: prev.values.map(v =>
        v.field === field ? { ...v, aggregator } : v
      ),
    }))
  }

  const rowIds = config.rows.map(r => `row-${r}`)
  const colIds = config.columns.map(c => `col-${c}`)
  const valIds = config.values.map(v => `val-${v.field}`)

  return (
    <div className="bg-white border rounded-lg p-4">
      <h3 className="text-lg font-semibold mb-4">数据透视表</h3>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="border rounded p-3">
            <div className="text-sm font-medium text-gray-600 mb-2">行</div>
            <SortableContext items={rowIds} strategy={verticalListSortingStrategy}>
              <div className="flex flex-wrap gap-2 min-h-8 mb-2">
                {config.rows.map(key => (
                  <SortableItem
                    key={`row-${key}`}
                    id={`row-${key}`}
                    label={availableFields.find(f => f.key === key)?.label || key}
                    onRemove={() => removeRow(key)}
                  />
                ))}
              </div>
            </SortableContext>
            <FieldSelector
              availableFields={availableFields.filter(f => f.type === 'string')}
              selectedKeys={config.rows}
              onAdd={addRow}
              color="blue"
            />
          </div>

          <div className="border rounded p-3">
            <div className="text-sm font-medium text-gray-600 mb-2">列</div>
            <SortableContext items={colIds} strategy={verticalListSortingStrategy}>
              <div className="flex flex-wrap gap-2 min-h-8 mb-2">
                {config.columns.map(key => (
                  <SortableItem
                    key={`col-${key}`}
                    id={`col-${key}`}
                    label={availableFields.find(f => f.key === key)?.label || key}
                    onRemove={() => removeColumn(key)}
                  />
                ))}
              </div>
            </SortableContext>
            <FieldSelector
              availableFields={availableFields.filter(f => f.type === 'string')}
              selectedKeys={config.columns}
              onAdd={addColumn}
              color="purple"
            />
          </div>

          <div className="border rounded p-3">
            <div className="text-sm font-medium text-gray-600 mb-2">值</div>
            <SortableContext items={valIds} strategy={verticalListSortingStrategy}>
              <div className="flex flex-wrap gap-2 min-h-8 mb-2">
                {config.values.map(value => (
                  <SortableValueItem
                    key={`val-${value.field}`}
                    id={`val-${value.field}`}
                    value={value}
                    onRemove={() => removeValue(value.field)}
                    onAggregatorChange={(agg) => changeAggregator(value.field, agg)}
                  />
                ))}
              </div>
            </SortableContext>
            <FieldSelector
              availableFields={availableFields.filter(f => f.type === 'number')}
              selectedKeys={config.values.map(v => v.field)}
              onAdd={addValue}
              color="green"
            />
          </div>
        </div>
      </DndContext>

      {pivotData.rowHeaders.length > 0 ? (
        <div className="overflow-auto max-h-96 border rounded">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-3 py-2 text-left border-b sticky left-0 bg-gray-50 z-10 min-w-32">
                  行标签
                </th>
                {pivotData.colHeaders.map(header =>
                  config.values.map((val, vi) => (
                    <th
                      key={`${header}-${vi}`}
                      className="px-3 py-2 text-right border-b min-w-28 whitespace-nowrap"
                    >
                      {header}
                      {config.values.length > 1 && (
                        <div className="text-xs text-gray-500">
                          {getAggregatorLabel(val.aggregator)}
                        </div>
                      )}
                    </th>
                  ))
                )}
                <th className="px-3 py-2 text-right border-b font-bold min-w-28">
                  总计
                </th>
              </tr>
            </thead>
            <tbody>
              {pivotData.rowHeaders.map((rowHeader, ri) => (
                <tr key={ri} className="hover:bg-gray-50">
                  <td className="px-3 py-2 border-b sticky left-0 bg-white z-10">
                    {rowHeader}
                  </td>
                  {pivotData.values[ri]?.map((val, vi) => (
                    <td key={vi} className="px-3 py-2 text-right border-b">
                      {Number(val).toLocaleString()}
                    </td>
                  ))}
                  <td className="px-3 py-2 text-right border-b font-semibold">
                    {Number(pivotData.grandTotalCol[ri]).toLocaleString()}
                  </td>
                </tr>
              ))}
              <tr className="bg-gray-50 font-semibold">
                <td className="px-3 py-2 sticky left-0 bg-gray-50 z-10">总计</td>
                {pivotData.grandTotalRow.map((val, vi) => (
                  <td key={vi} className="px-3 py-2 text-right">
                    {Number(val).toLocaleString()}
                  </td>
                ))}
                <td className="px-3 py-2 text-right">
                  {pivotData.grandTotalCol.reduce((a, b) => Number(a) + Number(b), 0).toLocaleString()}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          请配置行和值字段以生成透视表
        </div>
      )}
    </div>
  )
}
