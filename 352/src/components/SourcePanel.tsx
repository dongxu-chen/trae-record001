import { useState } from 'react';
import { Search, Type, Hash, Calendar, CheckSquare } from 'lucide-react';
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

export default function SourcePanel() {
  const [search, setSearch] = useState('');
  const { sourceFields, mappings } = useAppStore();

  const mappedFieldIds = mappings
    .filter((m) => m.sourceFieldId)
    .map((m) => m.sourceFieldId);

  const filteredFields = sourceFields.filter((field) =>
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
          className="w-full pl-10 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <div className="space-y-1">
        {filteredFields.map((field) => {
          const isMapped = mappedFieldIds.includes(field.id);
          return (
            <div
              key={field.id}
              className={`p-3 rounded-lg border transition-all cursor-grab active:cursor-grabbing ${
                isMapped
                  ? 'bg-blue-50 border-blue-200'
                  : 'bg-white border-slate-200 hover:border-blue-300 hover:shadow-sm'
              }`}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData('sourceFieldId', field.id);
                e.dataTransfer.setData('sourceFieldName', field.name);
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-800 truncate">
                  {field.name}
                </span>
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${typeColors[field.type]}`}>
                  {typeIcons[field.type]}
                  {field.type}
                </span>
              </div>
              {field.sampleValues.length > 0 && (
                <div className="text-xs text-slate-500 truncate">
                  示例: {field.sampleValues.join(', ')}
                </div>
              )}
              {isMapped && (
                <div className="mt-2 text-xs text-blue-600 font-medium">
                  ✓ 已映射
                </div>
              )}
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
