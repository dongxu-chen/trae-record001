import { useState, useMemo } from 'react';
import { Download, FileJson, FileSpreadsheet, FileText, Check } from 'lucide-react';
import { useAppStore } from '@/store';
import { applyTransforms } from '@/utils/transforms';
import { exportData } from '@/utils/exporter';
import type { DataRow, ExportConfig } from '@/types';

export default function ExportPanel() {
  const { sourceData, sourceFields, targetFields, mappings } = useAppStore();
  const [config, setConfig] = useState<ExportConfig>({
    format: 'xlsx',
    filename: 'mapped_data',
    includeHeaders: true,
  });
  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);

  const mappedData = useMemo(() => {
    if (sourceData.length === 0 || mappings.length === 0) return [];

    return sourceData.map((row) => {
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
  }, [sourceData, sourceFields, targetFields, mappings]);

  const handleExport = async () => {
    setExporting(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 500));
      exportData(mappedData, config);
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 2000);
    } finally {
      setExporting(false);
    }
  };

  const formatOptions = [
    { value: 'xlsx', label: 'Excel (.xlsx)', icon: FileSpreadsheet },
    { value: 'csv', label: 'CSV (.csv)', icon: FileText },
    { value: 'json', label: 'JSON (.json)', icon: FileJson },
  ];

  const hasData = mappedData.length > 0;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
            <Download className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800">导出数据</h2>
            <p className="text-sm text-slate-500">
              将映射后的数据导出为文件
            </p>
          </div>
        </div>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              导出格式
            </label>
            <div className="space-y-2">
              {formatOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setConfig({ ...config, format: option.value as ExportConfig['format'] })}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
                    config.format === option.value
                      ? 'border-emerald-500 bg-emerald-50'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <span className={`p-2 rounded-lg ${
                    config.format === option.value ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-600'
                  }`}>
                    <option.icon className="w-5 h-5" />
                  </span>
                  <span className="font-medium text-slate-700">{option.label}</span>
                  {config.format === option.value && (
                    <Check className="w-5 h-5 text-emerald-500 ml-auto" />
                  )}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              文件名称
            </label>
            <div className="flex items-center">
              <input
                type="text"
                value={config.filename}
                onChange={(e) => setConfig({ ...config, filename: e.target.value })}
                className="flex-1 px-4 py-2.5 border border-slate-200 rounded-l-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                placeholder="输入文件名"
              />
              <span className="px-4 py-2.5 bg-slate-100 border border-l-0 border-slate-200 rounded-r-lg text-slate-500 font-mono text-sm">
                .{config.format}
              </span>
            </div>

            <div className="mt-6">
              <label className="inline-flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.includeHeaders}
                  onChange={(e) => setConfig({ ...config, includeHeaders: e.target.checked })}
                  className="w-5 h-5 rounded border-slate-300 text-emerald-500 focus:ring-emerald-500"
                />
                <span className="text-sm text-slate-700">包含表头</span>
              </label>
            </div>
          </div>

          <div className="bg-slate-50 rounded-xl p-4">
            <div className="text-sm text-slate-500 mb-3">导出预览</div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">记录数</span>
                <span className="font-medium text-slate-800">{mappedData.length} 条</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">字段数</span>
                <span className="font-medium text-slate-800">{targetFields.length} 个</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">已映射</span>
                <span className="font-medium text-emerald-600">{mappings.filter(m => m.sourceFieldId).length} 个</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">格式</span>
                <span className="font-medium text-slate-800 uppercase">{config.format}</span>
              </div>
            </div>

            <button
              onClick={handleExport}
              disabled={exporting || !hasData}
              className="w-full mt-6 flex items-center justify-center gap-2 px-4 py-3 bg-emerald-500 text-white font-medium rounded-xl hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-emerald-500/30"
            >
              {exporting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  导出中...
                </>
              ) : exportSuccess ? (
                <>
                  <Check className="w-5 h-5" />
                  导出成功
                </>
              ) : (
                <>
                  <Download className="w-5 h-5" />
                  导出文件
                </>
              )}
            </button>

            {!hasData && (
              <p className="mt-2 text-xs text-center text-amber-600">
                请先配置字段映射后再导出
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
