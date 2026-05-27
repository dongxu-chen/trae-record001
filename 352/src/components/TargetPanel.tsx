import { useState } from 'react';
import { Search, Type, Hash, Calendar, CheckSquare, Asterisk } from 'lucide-react';
import { useAppStore } from '@/store';
import type { FieldType } from '@/types';

const typeIcons: Record<FieldType, React.ReactNode> = {
  string: <Type className="w-3 h-3" />,
  number: <Hash className="w-3 h-3" />,
  date: <Calendar className="w-3 h-3" />,
  boolean: <CheckSquare className="w-3 h-3" />,
};

const typeColors: Record<FieldType, string> = {
  string: 'bg-blue-100 text-blue-600',
  number: 'bg-emerald-100 text-emerald-600',
  date: 'bg-amber-100 text-amber-600',
  boolean: 'bg-purple-100 text-purple-600',
};

export default function TargetPanel() {
  const [search, setSearch] = useState('');
  const { targetFields, mappings } = useAppStore();

  const mappedTargetIds = mappings.map((m) => m.targetFieldId);

  const filteredFields = targetFields.filter((field) =>
    field.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-3 space-y-3">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索字段..."
          className="w-full pl-10 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
        />
      </div>

      <div className="space-y-1">
        {filteredFields.map((field) => {
          const isMapped = mappedTargetIds.includes(field.id);
          return (
            <div
              key={field.id}
              className={`p-3 rounded-lg border transition-all ${
                isMapped
                  ? 'bg-emerald-50 border-emerald-200'
                  : field.required
                  ? 'bg-red-50 border-red-200'
                  : 'bg-white border-slate-200'
              }`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const sourceFieldId = e.dataTransfer.getData('sourceFieldId');
                if (sourceFieldId) {
                  const event = new CustomEvent('fieldDropped', {
                    detail: { sourceFieldId, targetFieldId: field.id },
                  });
                  window.dispatchEvent(event);
                }
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-800 truncate">
                    {field.name}
                  </span>
                  {field.required && (
                    <Asterisk className="w-3 h-3 text-red-500 flex-shrink-0" />
                  )}
                </div>
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${typeColors[field.type]}`}>
                  {typeIcons[field.type]}
                  {field.type}
                </span>
              </div>
              {field.description && (
                <div className="text-xs text-slate-500 truncate">
                  {field.description}
                </div>
              )}
              {isMapped ? (
                <div className="mt-2 text-xs text-emerald-600 font-medium">
                  ✓ 已映射
                </div>
              ) : field.required ? (
                <div className="mt-2 text-xs text-red-600 font-medium">
                  ⚠ 待映射（必填）
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {filteredFields.length === 0 && search && (
        <div className="text-center py-8 text-slate-400 text-sm">
          未找到匹配的字段
        </div>
      )}
    </div>
  );
}
