import { useState, useCallback, useMemo } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  SortingState,
  ColumnFiltersState,
  ColumnOrderState,
  RowSelectionState,
} from '@tanstack/react-table'
import type { DataRow, CellPosition, EditState, TableColumnDef } from '@/types/table'

interface UseDataTableProps {
  data: DataRow[]
  columns: TableColumnDef<DataRow>[]
  onDataChange?: (data: DataRow[]) => void
}

export function useDataTable({ data, columns, onDataChange }: UseDataTableProps) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnOrder, setColumnOrder] = useState<ColumnOrderState>([])
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [globalFilter, setGlobalFilter] = useState('')
  const [selectedCell, setSelectedCell] = useState<CellPosition | null>(null)
  const [editingCell, setEditingCell] = useState<EditState | null>(null)
  const [tableData, setTableData] = useState<DataRow[]>(data)

  const handleCellClick = useCallback((rowIndex: number, columnId: string) => {
    setSelectedCell({ rowIndex, columnId })
    setEditingCell(null)
  }, [])

  const handleStartEdit = useCallback((pos: CellPosition) => {
    const value = tableData[pos.rowIndex]?.[pos.columnId as keyof DataRow]
    setEditingCell({
      rowIndex: pos.rowIndex,
      columnId: pos.columnId,
      value,
      originalValue: value,
      error: undefined,
    })
  }, [tableData])

  const handleSaveEdit = useCallback(() => {
    if (!editingCell || editingCell.error) return

    const newData = [...tableData]
    newData[editingCell.rowIndex] = {
      ...newData[editingCell.rowIndex],
      [editingCell.columnId]: editingCell.value,
    }

    setTableData(newData)
    onDataChange?.(newData)
    setEditingCell(null)
  }, [editingCell, tableData, onDataChange])

  const handleCancelEdit = useCallback(() => {
    setEditingCell(null)
  }, [])

  const handleRestoreOriginal = useCallback(() => {
    if (!editingCell) return
    setEditingCell(prev => prev ? {
      ...prev,
      value: prev.originalValue,
      error: undefined,
    } : null)
  }, [editingCell])

  const handleUpdateCellValue = useCallback((value: unknown) => {
    setEditingCell(prev => prev ? { ...prev, value } : null)
  }, [])

  const handleValidateError = useCallback((error: string) => {
    setEditingCell(prev => prev ? { ...prev, error: error || undefined } : null)
  }, [])

  const handleUpdateCell = useCallback((rowIndex: number, columnId: string, value: unknown) => {
    const newData = [...tableData]
    newData[rowIndex] = {
      ...newData[rowIndex],
      [columnId]: value,
    }
    setTableData(newData)
    onDataChange?.(newData)
  }, [tableData, onDataChange])

  const handleDeleteCell = useCallback(() => {
    if (!selectedCell) return
    handleUpdateCell(selectedCell.rowIndex, selectedCell.columnId, '')
  }, [selectedCell, handleUpdateCell])

  const handleSelectAll = useCallback(() => {
    const allSelected: RowSelectionState = {}
    tableData.forEach((_, index) => {
      allSelected[index] = true
    })
    setRowSelection(allSelected)
  }, [tableData.length])

  const table = useReactTable({
    data: tableData,
    columns,
    state: {
      sorting,
      columnFilters,
      columnOrder,
      rowSelection,
      globalFilter,
    },
    enableRowSelection: true,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnOrderChange: setColumnOrder,
    onRowSelectionChange: setRowSelection,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  const columnIds = useMemo(() =>
    table.getAllLeafColumns().map(col => col.id),
    [table]
  )

  const visibleColumns = useMemo(() =>
    table.getVisibleLeafColumns(),
    [table]
  )

  const filteredRowCount = useMemo(() =>
    table.getFilteredRowModel().rows.length,
    [table]
  )

  const handleColumnReorder = useCallback((activeId: string, overId: string) => {
    const oldIndex = columnOrder.indexOf(activeId)
    const newIndex = columnOrder.indexOf(overId)

    if (oldIndex === -1 || newIndex === -1) return

    const newColumnOrder = [...columnOrder]
    newColumnOrder.splice(oldIndex, 1)
    newColumnOrder.splice(newIndex, 0, activeId)

    setColumnOrder(newColumnOrder)
  }, [columnOrder])

  return {
    table,
    tableData,
    sorting,
    columnFilters,
    columnOrder,
    rowSelection,
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
  }
}
