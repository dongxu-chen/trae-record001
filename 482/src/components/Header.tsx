import { Database, Settings, Download, GitBranch } from 'lucide-react';
import { useLineageStore } from '@/stores/useLineageStore';

interface HeaderProps {
  onExport: (format: 'json' | 'excel') => void;
}

export const Header = ({ onExport }: HeaderProps) => {
  const { setShowDataSourceModal, analysisResult } = useLineageStore();

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center">
          <GitBranch className="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-gray-900">数据血缘影响分析</h1>
          <p className="text-xs text-gray-500">Data Lineage Impact Analyzer</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowDataSourceModal(true)}
          className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <Database className="w-4 h-4" />
          <span className="text-sm font-medium">数据源管理</span>
        </button>

        <div className="relative group">
          <button
            disabled={!analysisResult}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" />
            <span className="text-sm font-medium">导出报告</span>
          </button>
          {analysisResult && (
            <div className="absolute right-0 top-full mt-2 bg-white rounded-lg shadow-lg border border-gray-100 py-1 min-w-40 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <button
                onClick={() => onExport('json')}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
              >
                导出 JSON 格式
              </button>
              <button
                onClick={() => onExport('excel')}
                className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
              >
                导出 Excel 格式
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
