import React from 'react';
import { useDrop } from 'react-dnd';

interface DropZoneProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  onDrop: (item: { name: string; type: string }) => void;
  acceptType?: string;
  className?: string;
}

export const DropZone: React.FC<DropZoneProps> = ({
  title,
  icon,
  children,
  onDrop,
  className = '',
}) => {
  const [{ isOver }, drop] = useDrop(() => ({
    accept: 'FIELD',
    drop: (item: { name: string; type: string }) => onDrop(item),
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  }));

  return (
    <div className={`mb-4 ${className}`}>
      <div className="flex items-center mb-2 text-sm font-medium text-gray-600">
        {icon}
        <span className="ml-1">{title}</span>
      </div>
      <div
        ref={drop}
        className={`
          min-h-[60px] p-3 rounded-lg border-2 border-dashed
          transition-all duration-200
          ${isOver
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-200 bg-gray-50 hover:border-gray-300'
          }
        `}
      >
        {children || (
          <div className="text-xs text-gray-400 text-center py-2">
            拖拽字段到此处
          </div>
        )}
      </div>
    </div>
  );
};
