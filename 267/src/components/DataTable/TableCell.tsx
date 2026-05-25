import { memo, useRef, useEffect, useState, useCallback } from 'react'
import { AlertCircle, RotateCcw } from 'lucide-react'
import { cn } from '@/utils/cn'
import { validateValue } from '@/utils/validation'
import { TextRenderer } from '@/components/renderers/TextRenderer'
import { NumberRenderer } from '@/components/renderers/NumberRenderer'
import { DateRenderer } from '@/components/renderers/DateRenderer'
import { StatusRenderer } from '@/components/renderers/StatusRenderer'
import { ProgressRenderer } from '@/components/renderers/ProgressRenderer'
import type { DataRow, RendererType, ValidationRule } from '@/types/table'

interface TableCellProps {
  value: unknown
  rowIndex: number
  columnId: string
  renderer?: RendererType
  validation?: ValidationRule
  isSelected: boolean
  isEditing: boolean
  editValue: unknown
  editError?: string
  onClick: () => void
  onDoubleClick: () => void
  onEditChange: (value: unknown) => void
  onEditSave: () => void
  onEditCancel: () => void
  onValidateError?: (error: string) => void
  onRestoreOriginal?: () => void
}

export const TableCell = memo(function TableCell({
  value,
  columnId,
  renderer = 'text',
  validation,
  isSelected,
  isEditing,
  editValue,
  editError,
  onClick,
  onDoubleClick,
  onEditChange,
  onEditSave,
  onEditCancel,
  onValidateError,
  onRestoreOriginal,
}: TableCellProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [localError, setLocalError] = useState<string | undefined>(undefined)
  const [showErrorTooltip, setShowErrorTooltip] = useState(false)

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  useEffect(() => {
    setLocalError(editError)
  }, [editError])

  const validateInput = useCallback((val: unknown) => {
    const result = validateValue(val, validation)
    if (!result.isValid) {
      setLocalError(result.error)
      onValidateError?.(result.error || '验证失败')
    } else {
      setLocalError(undefined)
      onValidateError?.('')
    }
    return result.isValid
  }, [validation, onValidateError])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    onEditChange(newValue)

    if (validation) {
      validateInput(newValue)
    }
  }

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      if (validation && !validateInput(editValue)) {
        return
      }
      onEditSave()
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setLocalError(undefined)
      onEditCancel()
    } else if (e.key === 'z' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      onRestoreOriginal?.()
    }
  }

  const handleBlur = () => {
    if (validation && !validateInput(editValue)) {
      return
    }
    onEditSave()
  }

  const handleRestore = (e: React.MouseEvent) => {
    e.stopPropagation()
    onRestoreOriginal?.()
    setLocalError(undefined)
  }

  const renderContent = () => {
    if (isEditing) {
      const inputType =
        columnId === 'salary' || columnId === 'performance' || columnId === 'projects'
          ? 'number'
          : columnId === 'hireDate'
          ? 'date'
          : 'text'

      const hasError = !!localError

      return (
        <div className="relative w-full h-full flex items-center">
          <input
            ref={inputRef}
            type={inputType}
            value={String(editValue ?? '')}
            onChange={handleInputChange}
            onKeyDown={handleInputKeyDown}
            onBlur={handleBlur}
            onMouseEnter={() => hasError && setShowErrorTooltip(true)}
            onMouseLeave={() => setShowErrorTooltip(false)}
            className={cn(
              'w-full h-full px-2 pr-8 bg-dark-900 border-2 rounded text-sm text-dark-100 focus:outline-none transition-colors',
              hasError
                ? 'border-red-500 focus:border-red-400'
                : 'border-accent-500 focus:border-accent-400'
            )}
          />
          {hasError && (
            <>
              <button
                onClick={handleRestore}
                className="absolute right-6 top-1/2 -translate-y-1/2 p-1 text-amber-400 hover:text-amber-300 transition-colors"
                title="恢复原值"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <div
                className={cn(
                  'absolute right-1 top-1/2 -translate-y-1/2',
                  showErrorTooltip && 'cursor-help'
                )}
                onMouseEnter={() => setShowErrorTooltip(true)}
                onMouseLeave={() => setShowErrorTooltip(false)}
              >
                <AlertCircle className="w-4 h-4 text-red-400" />
              </div>

              {showErrorTooltip && (
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-red-500 text-white text-xs rounded shadow-lg whitespace-nowrap z-50">
                  <div className="flex items-center gap-1.5">
                    <AlertCircle className="w-3 h-3" />
                    {localError}
                  </div>
                  <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-red-500" />
                </div>
              )}
            </>
          )}
        </div>
      )
    }

    switch (renderer) {
      case 'number':
        return <NumberRenderer value={value as number} />
      case 'currency':
        return <NumberRenderer value={value as number} format="currency" />
      case 'date':
        return <DateRenderer value={value as string} />
      case 'status':
        return <StatusRenderer value={value as DataRow['status']} />
      case 'progress':
        return <ProgressRenderer value={value as number} />
      default:
        return <TextRenderer value={String(value ?? '')} />
    }
  }

  return (
    <div
      className={cn(
        'flex items-center h-full px-3 py-2 border-r border-b border-dark-700 cursor-pointer transition-colors relative',
        isSelected && 'bg-primary-500/20 border-primary-500/50',
        !isEditing && !isSelected && 'hover:bg-dark-700/50'
      )}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
    >
      {renderContent()}
    </div>
  )
})
