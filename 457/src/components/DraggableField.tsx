import React from 'react';
import { useDrag } from 'react-dnd';
import { X } from 'lucide-react';

interface DraggableFieldProps {
  name: string;
  type: 'dimension' | 'measure';
  onRemove?: () => void;
  showRemove?: boolean;
  onDoubleClick?: () => void;
}

export const DraggableField: React.FC<DraggableFieldProps> = ({
  name,
  type,
  onRemove,
  showRemove = false,
  onDoubleClick,
}) => {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'FIELD',
    item: { name, type },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }));

  return (
    <div
      ref={drag}
      onDoubleClick={onDoubleClick}
      className={`
        flex items-center justify-between
        px-3 py-2 mb-2 rounded-lg
        bg-white border border-gray-200
        shadow-sm cursor-grab active:cursor-grabbing
        hover:border-primary-400 hover:shadow-md
        transition-all duration-200
        ${isDragging ? 'opacity-50 scale-95' : ''}
        ${type === 'measure' ? 'border-l-4 border-l-emerald-500' : 'border-l-4 border-l-blue-500'}
        ${onDoubleClick ? 'hover:bg-gray-50' : ''}
      `}
    >
      <span className="text-sm text-gray-700 font-medium truncate flex-1">
        {name}
      </span>
      <span className={`
        text-xs px-2 py-0.5 rounded-full ml-2
        ${type === 'measure' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}
      `}>
        {type === 'measure' ? '度量' : '维度'}
      </span>
      {showRemove && onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-2 p-0.5 rounded-full hover:bg-gray-100 text-gray-400 hover:text-red-500 transition-colors"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
};
