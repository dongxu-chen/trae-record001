import { useMemo } from 'react';
import { Table, ChevronLeft, ChevronRight, Eye, Type, Hash, Calendar, CheckSquare, Loader } from 'lucide-react';
import { useAppStore } from '@/store';
import { applyTransforms, convertToType } from '@/utils/transforms';
import type { DataRow, FieldType } from '@/types';

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

export default function DataPreview() {
  const { 
    sourceData, 
    sourceFields, 
    targetFields, 
    mappings, 
    dataPreviewPage, 
    dataPageSize, 
    setDataPreviewPage,
    isLoading
  } = useAppStore();

  const currentPageData = useMemo(() => {
    if (sourceData.length === 0 || mappings.length === 0) return [];

    const startIndex = (dataPreviewPage - 1) * dataPageSize;
    const endIndex = Math.min(startIndex + dataPageSize, sourceData.length);
    const pageData = sourceData.slice(startIndex, endIndex);

    return pageData.map((row) => {
      const result: DataRow = {};

      targetFields.forEach((targetField) => {
        const mapping = mappings.find((m) => m.targetFieldId === targetField.id);
        
        if (mapping && mapping.sourceFieldId) {
          const sourceField = sourceFields.find((f) => f.id === mapping.sourceFieldId);
          if (sourceField) {
            const value = row[sourceField.name];
            let transformedValue = applyTransforms(value, mapping.transforms, row);
            
            if (mapping.outputType) {
              transformedValue = convertToType(transformedValue, mapping.outputType);
            }
            
            result[targetField.name] = transformedValue;
          }
        } else {
          result[targetField.name] = '';
        }
      });

      return result;
    });
  }, [sourceData, sourceFields, targetFields, mappings, dataPreviewPage, dataPageSize]);

  const totalPages = Math.ceil(sourceData.length / dataPageSize);
  const startIndex = (dataPreviewPage - 1) * dataPageSize;
  const endIndex = Math.min(startIndex + dataPageSize, sourceData.length);

  const mappedTargetFields = targetFields.filter((field) =>
    mappings.some((m) => m.targetFieldId === field.id)
  );

  const getFieldOutputType = (targetFieldId: string): FieldType | null => {
    const mapping = mappings.find((m) => m.targetFieldId === targetFieldId);
    return mapping?.outputType || null;
  };

  const formatValue = (value: any, type: FieldType | null): string => {
    if (value === null || value === undefined) return '';
    
    if (type === 'date' && value instanceof Date) {
      return value.toLocaleDateString('zh-CN');
    }
    if (type === 'boolean') {
      return value ? '是' : '否';
    }
    if (type === 'number') {
      return Number(value).toLocaleString('zh-CN');
    }
    
    return String(value);
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-12 flex flex-col items-center justify-center text-slate-400">
          <Loader className="w-12 h-12 animate-spin mb-3" />
          <p>加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
            <Eye className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800">数据预览</h2>
            <p className="text-sm text-slate-500">
              共 {sourceData.length.toLocaleString()} 条记录 · 每页 {dataPageSize} 条
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-500">
            第 {startIndex + 1} - {endIndex} 条
          </span>
          <div className="flex items-center gap-1 border border-slate-200 rounded-lg">
            <button
              onClick={() => setDataPreviewPage(Math.max(1, dataPreviewPage - 1))}
              disabled={dataPreviewPage === 1}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-3 text-sm font-medium text-slate-700 min-w-[80px] text-center">
              {dataPreviewPage} / {totalPages || 1}
            </span>
            <button
              onClick={() => setDataPreviewPage(Math.min(totalPages, dataPreviewPage + 1))}
              disabled={dataPreviewPage >= totalPages || totalPages === 0}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {mappedTargetFields.length === 0 ? (
        <div className="p-12 text-center text-slate-400">
          <Table className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>请先配置字段映射</p>
        </div>
      ) : (
        <div className="overflow-auto max-h-[400px]">
          <table className="w-full">
            <thead className="bg-slate-50 sticky top-0">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider border-b border-slate-200 w-16">
                  #
                </th>
                {mappedTargetFields.map((field) => {
                  const outputType = getFieldOutputType(field.id);
                  return (
                    <th
                      key={field.id}
                      className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider border-b border-slate-200"
                    >
                      <div className="flex items-center gap-2">
                        {field.name}
                        {outputType && (
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium ${typeColors[outputType]}`}>
                            {typeIcons[outputType]}
                          </span>
                        )}
                        {field.required && (
                          <span className="text-red-500">*</span>
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {currentPageData.map((row, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-500 font-mono">
                    {startIndex + rowIndex + 1}
                  </td>
                  {mappedTargetFields.map((field) => {
                    const outputType = getFieldOutputType(field.id);
                    const value = row[field.name];
                    return (
                      <td key={field.id} className="px-4 py-3 text-sm text-slate-700">
                        <div className="max-w-xs truncate" title={String(value ?? '')}>
                          {formatValue(value, outputType)}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
