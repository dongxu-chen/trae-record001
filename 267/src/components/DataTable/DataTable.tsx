import { useMemo, useCallback, useState } from 'react'
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
  horizontalListSortingStrategy,
} from '@dnd-kit/sortable'
import { Table, BarChart3, Table2, Sparkles, LayoutGrid } from 'lucide-react'
import { cn } from '@/utils/cn'
import { TableToolbar } from './TableToolbar'
import { TableHeader } from './TableHeader'
import { TableBody } from './TableBody'
import { PivotTablePanel } from './PivotTablePanel'
import { ChartPanel } from './ChartPanel'
import { AIAnalysisPanel } from './AIAnalysisPanel'
import { useDataTable } from '@/hooks/useDataTable'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'
import { useClipboard } from '@/hooks/useClipboard'
import { generateData } from '@/utils/dataGenerator'
import type { DataRow, TableColumnDef } from '@/types/table'

type ViewMode = 'table' | 'pivot' | 'chart' | 'ai'

interface DataTableProps {
  className?: string
}

export function DataTable({ className }: DataTableProps) {
  const initialData = useMemo(() => generateData(1000), [])
  const [viewMode, setViewMode] = useState<ViewMode>('table')

  const columns: TableColumnDef<DataRow>[] = useMemo(
    () => [
      {
        header: '基本信息',
        columns: [
          {
            accessorKey: 'id',
            header: 'ID',
            enableSorting: true,
            enableColumnFilter: true,
            meta: { renderer: 'number', width: 80, minWidth: 60 },
          },
          {
            accessorKey: 'name',
            header: '姓名',
            enableSorting: true,
            enableColumnFilter: true,
            meta: {
              renderer: 'text',
              width: 120,
              minWidth: 100,
              editable: true,
              validation: {
                required: true,
                minLength: 2,
                maxLength: 20,
              },
            },
          },
          {
            accessorKey: 'email',
            header: '邮箱',
            enableSorting: true,
            enableColumnFilter: true,
            meta: {
              renderer: 'text',
              width: 220,
              minWidth: 180,
              editable: true,
              validation: {
                required: true,
                pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                custom: (val) => {
                  const email = String(val ?? '')
                  if (!email.includes('@')) return '请输入有效的邮箱地址'
                  return true
                },
              },
            },
          },
        ],
      },
      {
        header: '职位信息',
        columns: [
          {
            accessorKey: 'department',
            header: '部门',
            enableSorting: true,
            enableColumnFilter: true,
            meta: {
              renderer: 'text',
              width: 120,
              minWidth: 100,
              editable: true,
              validation: {
                required: true,
                minLength: 2,
              },
            },
          },
          {
            accessorKey: 'position',
            header: '职位',
            enableSorting: true,
            enableColumnFilter: true,
            meta: {
              renderer: 'text',
              width: 140,
              minWidth: 100,
              editable: true,
              validation: {
                required: true,
                minLength: 2,
              },
            },
          },
          {
            accessorKey: 'region',
            header: '地区',
            enableSorting: true,
            enableColumnFilter: true,
            meta: { renderer: 'text', width: 100, minWidth: 80 },
          },
          {
            accessorKey: 'team',
            header: '团队',
            enableSorting: true,
            enableColumnFilter: true,
            meta: { renderer: 'text', width: 80, minWidth: 60 },
          },
        ],
      },
      {
        header: '薪资与绩效',
        columns: [
          {
            accessorKey: 'salary',
            header: '薪资',
            enableSorting: true,
            enableColumnFilter: true,
            meta: {
              renderer: 'currency',
              width: 130,
              minWidth: 100,
              editable: true,
              validation: {
                required: true,
                min: 0,
                max: 1000000,
                custom: (val) => {
                  const num = Number(val)
                  if (isNaN(num)) return '请输入有效的数字'
                  if (num < 0) return '薪资不能为负数'
                  if (num > 1000000) return '薪资不能超过 1,000,000'
                  return true
                },
              },
            },
          },
          {
            accessorKey: 'hireDate',
            header: '入职日期',
            enableSorting: true,
            enableColumnFilter: true,
            meta: {
              renderer: 'date',
              width: 130,
              minWidth: 110,
              editable: true,
              validation: {
                required: true,
                custom: (val) => {
                  const date = new Date(String(val))
                  if (isNaN(date.getTime())) return '请输入有效的日期'
                  if (date < new Date('2000-01-01')) return '日期不能早于 2000-01-01'
                  if (date > new Date()) return '日期不能晚于今天'
                  return true
                },
              },
            },
          },
          {
            accessorKey: 'status',
            header: '状态',
            enableSorting: true,
            enableColumnFilter: true,
            meta: { renderer: 'status', width: 100, minWidth: 80 },
          },
          {
            accessorKey: 'performance',
            header: '绩效',
            enableSorting: true,
            enableColumnFilter: true,
            meta: {
              renderer: 'progress',
              width: 150,
              minWidth: 120,
              validation: {
                min: 0,
                max: 100,
              },
            },
          },
          {
            accessorKey: 'projects',
            header: '项目数',
            enableSorting: true,
            enableColumnFilter: true,
            meta: {
              renderer: 'number',
              width: 100,
              minWidth: 80,
              validation: {
                min: 0,
                max: 100,
              },
            },
          },
        ],
      },
    ],
    []
  )

  const {
    table,
    tableData,
    globalFilter,
    selectedCell,
    editingCell,
    columnIds,
    visibleColumns,
    filteredRowCount,
    setGlobalFilter,
    setTableData,
    handleCellClick,
    handleStartEdit,
    handleSaveEdit,
    handleCancelEdit,
    handleRestoreOriginal,
    handleUpdateCellValue,
    handleValidateError,
    handleUpdateCell,
    handleDeleteCell,
    handleSelectAll,
    handleColumnReorder,
  } = useDataTable({ data: initialData, columns })

  const { handleCopy, handlePaste } = useClipboard({
    data: tableData,
    columnIds,
    selectedCell,
    onUpdateCell: handleUpdateCell,
  })

  useKeyboardShortcuts({
    selectedCell,
    editingCell,
    columnIds,
    rowCount: tableData.length,
    onSelectCell: handleCellClick,
    onStartEdit: handleStartEdit,
    onSaveEdit: handleSaveEdit,
    onCancelEdit: handleCancelEdit,
    onCopy: handleCopy,
    onPaste: handlePaste,
    onSelectAll: handleSelectAll,
    onDelete: handleDeleteCell,
  })

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

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event
      if (active.id !== over?.id) {
        handleColumnReorder(String(active.id), String(over?.id ?? ''))
      }
    },
    [handleColumnReorder]
  )

  const exportColumns = useMemo(
    () =>
      visibleColumns.map((col) => ({
        id: col.id,
        header: col.columnDef.header as string,
      })),
    [visibleColumns]
  )

  const handleRefresh = useCallback(() => {
    setTableData(generateData(100000))
  }, [setTableData])

  const selectedCount = useMemo(
    () => table.getSelectedRowModel().rows.length,
    [table]
  )

  const headerGroups = table.getHeaderGroups()
  const rows = table.getRowModel().rows

  const getTotalHeaderWidth = () => {
    return visibleColumns.reduce((acc, col) => {
      const meta = col.columnDef.meta as { width?: number } | undefined
      return acc + (meta?.width || 150)
    }, 0)
  }

  const viewModes: { key: ViewMode; label: string; icon: typeof Table }[] = [
    { key: 'table', label: '数据表格', icon: Table2 },
    { key: 'pivot', label: '透视表', icon: LayoutGrid },
    { key: 'chart', label: '图表分析', icon: BarChart3 },
    { key: 'ai', label: 'AI分析', icon: Sparkles },
  ]

  return (
    <div
      className={cn(
        'flex flex-col h-full bg-gray-50 border border-gray-200 rounded-xl overflow-hidden shadow-xl',
        className
      )}
    >
      <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 border-b">
        <div>
          <h1 className="text-xl font-semibold text-white">智能数据分析平台</h1>
          <p className="text-sm text-blue-100 mt-0.5">
            透视表 · 图表联动 · AI自然语言查询
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-2xl font-bold text-white font-mono">
              {filteredRowCount.toLocaleString()}
            </div>
            <div className="text-xs text-blue-100">数据行数</div>
          </div>
        </div>
      </div>

      <div className="flex gap-1 px-4 py-2 bg-white border-b">
        {viewModes.map((mode) => {
          const Icon = mode.icon
          return (
            <button
              key={mode.key}
              onClick={() => setViewMode(mode.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                viewMode === mode.key
                  ? 'bg-blue-500 text-white shadow-md'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Icon size={16} />
              <span>{mode.label}</span>
            </button>
          )
        })}
      </div>

      {viewMode === 'table' && (
        <>
          <TableToolbar
            globalFilter={globalFilter}
            onGlobalFilterChange={setGlobalFilter}
            data={tableData}
            columns={exportColumns}
            selectedCount={selectedCount}
            onRefresh={handleRefresh}
          />

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <div className="flex flex-col flex-1 overflow-hidden">
              {headerGroups.map((headerGroup) => (
                <div key={headerGroup.id} className="flex">
                  <SortableContext
                    items={headerGroup.headers.map((h) => h.id)}
                    strategy={horizontalListSortingStrategy}
                  >
                    <div
                      className="flex sticky top-0 z-20"
                      style={{ width: getTotalHeaderWidth() }}
                    >
                      {headerGroup.headers.map((header) => (
                        <TableHeader
                          key={header.id}
                          column={header.column}
                        />
                      ))}
                    </div>
                  </SortableContext>
                </div>
              ))}

              <TableBody
                rows={rows}
                columns={visibleColumns}
                selectedCell={selectedCell}
                editingCell={editingCell}
                onCellClick={handleCellClick}
                onStartEdit={handleStartEdit}
                onUpdateEditValue={handleUpdateCellValue}
                onSaveEdit={handleSaveEdit}
                onCancelEdit={handleCancelEdit}
                onValidateError={handleValidateError}
                onRestoreOriginal={handleRestoreOriginal}
                bufferSize={50}
              />
            </div>
          </DndContext>

          <div className="flex items-center justify-between px-4 py-3 bg-gray-100 border-t text-xs text-gray-500">
            <div className="flex items-center gap-4">
              <span>快捷键: F2 编辑 | Enter 确认 | Esc 取消 | Ctrl+C 复制 | Ctrl+V 粘贴</span>
            </div>
            <div className="flex items-center gap-4">
              <span>总行数: {tableData.length.toLocaleString()}</span>
              <span>显示: {filteredRowCount.toLocaleString()}</span>
              <span>列数: {visibleColumns.length}</span>
            </div>
          </div>
        </>
      )}

      {viewMode === 'pivot' && (
        <div className="flex-1 overflow-auto p-4">
          <PivotTablePanel data={tableData} />
        </div>
      )}

      {viewMode === 'chart' && (
        <div className="flex-1 overflow-auto p-4">
          <ChartPanel data={tableData} />
        </div>
      )}

      {viewMode === 'ai' && (
        <div className="flex-1 overflow-auto p-4">
          <AIAnalysisPanel data={tableData} />
        </div>
      )}
    </div>
  )
}
