import { Trash2, Edit2, User } from 'lucide-react';
import type { Annotation } from '../types';
import { getAnnotationColor, getAnnotationTypeName } from '../utils/export';

interface AnnotationListProps {
  annotations: Annotation[];
  onEdit: (annotation: Annotation) => void;
  onDelete: (id: string) => void;
  onSelect: (dataPointIndex: number) => void;
}

export const AnnotationList = ({ annotations, onEdit, onDelete, onSelect }: AnnotationListProps) => {
  if (annotations.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <p className="text-sm">暂无标注</p>
        <p className="text-xs mt-1">点击图表上的数据点开始标注</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
      {annotations.map((annotation) => (
        <div
          key={annotation.id}
          className="bg-slate-700/50 rounded-lg p-3 hover:bg-slate-700 transition-colors group"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3 flex-1 min-w-0">
              <div
                className="w-3 h-3 rounded-full mt-1.5 flex-shrink-0"
                style={{ backgroundColor: annotation.color || getAnnotationColor(annotation.type) }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className="text-xs px-2 py-0.5 rounded-full font-medium"
                    style={{
                      backgroundColor: (annotation.color || getAnnotationColor(annotation.type)) + '30',
                      color: annotation.color || getAnnotationColor(annotation.type),
                    }}
                  >
                    {getAnnotationTypeName(annotation.type)}
                  </span>
                  <h4 className="text-white text-sm font-medium truncate">{annotation.label}</h4>
                </div>
                {annotation.description && (
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{annotation.description}</p>
                )}
                <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                  <button
                    onClick={() => onSelect(annotation.dataPointIndex)}
                    className="hover:text-blue-400 transition-colors"
                  >
                    数据点 #{annotation.dataPointIndex}
                  </button>
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {annotation.createdBy}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => onEdit(annotation)}
                className="p-1.5 hover:bg-slate-600 rounded text-slate-400 hover:text-white transition-colors"
              >
                <Edit2 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onDelete(annotation.id)}
                className="p-1.5 hover:bg-red-600/20 rounded text-slate-400 hover:text-red-400 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
