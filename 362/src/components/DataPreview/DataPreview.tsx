import React, { useState, useMemo } from 'react';
import { Table2, ChevronLeft, ChevronRight, Hash } from 'lucide-react';
import { useDataStore } from '../../store/useDataStore';
import { TypeBadge } from '../common/Badge';
import { formatNumber, formatPercent } from '../../utils/statistics';

interface DataPreviewProps {
  className?: string;
  data?: any[][];
  columns?: string[];
  title?: string;
  showStats?: boolean;
}

export const DataPreview: React.FC<DataPreviewProps> = ({
  className = '',
  data: propData,
  columns: propColumns,
  title = '数据预览',
  showStats = true,
}) => {
  const { uploadedData, cleaningResult, activeTab, setActiveTab } = useDataStore();
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(50);

  const displayData = propData || cleaningResult?.data || uploadedData?.data || [];
  const displayColumns = propColumns || cleaningResult?.columns || uploadedData?.columns || [];
  const stats = cleaningResult?.stats || uploadedData?.stats;

  const totalPages = Math.ceil(displayData.length / rowsPerPage);
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return displayData.slice(start, start + rowsPerPage);
  }, [displayData, currentPage, rowsPerPage]);

  const getCellValue = (value: any): string => {
    if (value === null || value === undefined || value === '') return '-';
    if (typeof value === 'number') {
      return Number.isInteger(value) ? value.toString() : value.toFixed(4);
    }
    return String(value);
  };

  const isMissingValue = (value: any): boolean => {
    return value === null || value === undefined || value === '';
  };

  if (displayData.length === 0) {
    return (
      <div className={`card ${className}`}>
        <div className="card-header">
          <h3 className="font-semibold text-bg-100 flex items-center gap-2">
            <Table2 size={18} className="text-primary-400" />
            {title}
          </h3>
        </div>
        <div className="card-body flex items-center justify-center h-64">
          <p className="text-bg-500">请先上传数据文件</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`card flex flex-col ${className}`}>
      <div className="card-header">
        <h3 className="font-semibold text-bg-100 flex items-center gap-2">
          <Table2 size={18} className="text-primary-400" />
          {title}
          <span className="text-sm font-normal text-bg-400">
            ({displayData.length.toLocaleString()} 行 × {displayColumns.length} 列)
          </span>
        </h3>

        {showStats && (
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('data')}
              data-state={activeTab === 'data' ? 'active' : 'inactive'}
              className="tab-trigger"
            >
              数据
            </button>
            <button
              onClick={() => setActiveTab('stats')}
              data-state={activeTab === 'stats' ? 'active' : 'inactive'}
              className="tab-trigger"
            >
              统计
            </button>
            <button
              onClick={() => setActiveTab('charts')}
              data-state={activeTab === 'charts' ? 'active' : 'inactive'}
              className="tab-trigger"
            >
              图表
            </button>
          </div>
        )}
      </div>

      {activeTab === 'data' ? (
        <>
          <div className="flex-1 overflow-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="w-16 text-center sticky left-0 bg-bg-800 z-20">
                    <Hash size={14} className="inline" />
                  </th>
                  {displayColumns.map((col, idx) => (
                    <th key={idx} className="whitespace-nowrap">
                      {col}
                      {stats && stats.columns[idx] && (
                        <div className="mt-1">
                          <TypeBadge type={stats.columns[idx].type} />
                        </div>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {paginatedData.map((row, rowIdx) => (
                  <tr key={rowIdx}>
                    <td className="text-center text-bg-500 font-mono text-xs sticky left-0 bg-bg-800/80 backdrop-blur-sm">
                      {(currentPage - 1) * rowsPerPage + rowIdx + 1}
                    </td>
                    {row.map((cell, cellIdx) => (
                      <td
                        key={cellIdx}
                        className={`font-mono text-xs ${
                          isMissingValue(cell) ? 'text-danger-400 italic' : ''
                        }`}
                      >
                        {getCellValue(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-bg-700 flex items-center justify-between">
              <p className="text-sm text-bg-400">
                显示 {(currentPage - 1) * rowsPerPage + 1} -{' '}
                {Math.min(currentPage * rowsPerPage, displayData.length)} 行，共{' '}
                {displayData.length.toLocaleString()} 行
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="btn btn-ghost p-1.5"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="text-sm text-bg-300 font-mono min-w-[60px] text-center">
                  {currentPage} / {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="btn btn-ghost p-1.5"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </>
      ) : activeTab === 'stats' && stats ? (
        <div className="flex-1 overflow-auto p-4">
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-bg-900 rounded-lg p-4">
              <p className="text-sm text-bg-400 mb-1">数据行数</p>
              <p className="text-2xl font-mono font-bold text-primary-400">
                {stats.rowCount.toLocaleString()}
              </p>
            </div>
            <div className="bg-bg-900 rounded-lg p-4">
              <p className="text-sm text-bg-400 mb-1">数据列数</p>
              <p className="text-2xl font-mono font-bold text-primary-400">{stats.columnCount}</p>
            </div>
            <div className="bg-bg-900 rounded-lg p-4">
              <p className="text-sm text-bg-400 mb-1">缺失值总数</p>
              <p className="text-2xl font-mono font-bold text-warning-400">
                {stats.totalMissing.toLocaleString()}
              </p>
            </div>
            <div className="bg-bg-900 rounded-lg p-4">
              <p className="text-sm text-bg-400 mb-1">内存占用</p>
              <p className="text-2xl font-mono font-bold text-accent-500">{stats.memorySize}</p>
            </div>
          </div>

          <div className="space-y-3">
            {stats.columns.map((col, idx) => (
              <div key={idx} className="bg-bg-900 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-bg-100">{col.name}</span>
                    <TypeBadge type={col.type} />
                  </div>
                  <span className="text-sm text-bg-400">
                    缺失: {formatNumber(col.missingCount)} ({formatPercent(col.missingPercent)})
                  </span>
                </div>

                {col.missingPercent > 0 && (
                  <div className="mb-3">
                    <div className="h-2 bg-bg-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-warning-500 rounded-full"
                        style={{ width: `${col.missingPercent}%` }}
                      />
                    </div>
                  </div>
                )}

                {col.type === 'numeric' && (
                  <div className="grid grid-cols-6 gap-2 text-xs">
                    <div>
                      <p className="text-bg-500">最小值</p>
                      <p className="font-mono text-bg-200">{formatNumber(col.min)}</p>
                    </div>
                    <div>
                      <p className="text-bg-500">最大值</p>
                      <p className="font-mono text-bg-200">{formatNumber(col.max)}</p>
                    </div>
                    <div>
                      <p className="text-bg-500">均值</p>
                      <p className="font-mono text-bg-200">{formatNumber(col.mean)}</p>
                    </div>
                    <div>
                      <p className="text-bg-500">中位数</p>
                      <p className="font-mono text-bg-200">{formatNumber(col.median)}</p>
                    </div>
                    <div>
                      <p className="text-bg-500">标准差</p>
                      <p className="font-mono text-bg-200">{formatNumber(col.std)}</p>
                    </div>
                    <div>
                      <p className="text-bg-500">唯一值</p>
                      <p className="font-mono text-bg-200">{formatNumber(col.uniqueCount, 0)}</p>
                    </div>
                  </div>
                )}

                {col.type !== 'numeric' && (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-bg-500">唯一值</p>
                      <p className="font-mono text-bg-200">{formatNumber(col.uniqueCount, 0)}</p>
                    </div>
                    <div>
                      <p className="text-bg-500">众数</p>
                      <p className="font-mono text-bg-200 truncate">{String(col.mode ?? '-')}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
};
