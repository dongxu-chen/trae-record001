import { memo } from 'react'
import { GripVertical } from 'lucide-react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { cn } from '@/utils/cn'

interface ColumnDragHandleProps {
  id: string
  children: React.ReactNode
}

export const ColumnDragHandle = memo(function ColumnDragHandle({
  id,
  children,
}: ColumnDragHandleProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-1',
        isDragging && 'z-50'
      )}
    >
      <button
        {...attributes}
        {...listeners}
        className="p-1 text-dark-500 hover:text-dark-300 cursor-grab active:cursor-grabbing transition-colors"
      >
        <GripVertical className="w-3 h-3" />
      </button>
      {children}
    </div>
  )
})
