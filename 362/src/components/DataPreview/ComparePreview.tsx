import React, { useState, useMemo } from 'react';
import { ArrowRight, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { useDataStore } from '../../store/useDataStore';
import { Badge, TypeBadge } from '../common/Badge';
import type { ColumnStats } from '../../types';

interface ComparePreviewProps {
  className?: string;
}

export const ComparePreview: React.FC<ComparePreviewProps> = ({ className = '' }) => {
  const { uploadedData, cleaningResult } = useDataStore();
  const [currentPage, setCurrentPage] = useState(0);
  const pageSize = 20;

  const originalStats = uploadedData?.stats;
  const cleanedStats = cleaningResult?.stats;

  const displayData = useMemo(() => {
    if (!cleaningResult || !uploadedData) return null;

    const start = currentPage * pageSize;
    const end = start + pageSize;

    const originalRows = uploadedData.data.slice(start, end);
    const cleanedRows = cleaningResult.data.slice(start, end);

    return { originalRows, cleanedRows };
  }, [uploadedData, cleaningResult, currentPage]);

  const totalPages = cleaningResult
    ? Math.ceil(cleaningResult.data.length / pageSize)
    : 0;

  if (!uploadedData || !cleaningResult) {
    return null;
  }

  const renderStatComparison = (
    original: ColumnStats | undefined,
    cleaned: ColumnStats | undefined,
    field: keyof ColumnStats,
    label: string,
    isNumeric: boolean = true
  ) => {
    if (!original || !cleaned) return null;
    const origVal = original[field];
    const cleanedVal = cleaned[field];

    if (origVal === undefined || cleanedVal === undefined) return null;

    let diff = 0;
    let trend: 'up' | 'down' | 'same' = 'same';

    if (isNumeric && typeof origVal === 'number' && typeof cleanedVal === 'number') {
      diff = cleanedVal - origVal;
      trend = diff > 0 ? 'up' : diff < 0 ? 'down' : 'same';
    }

    const formatValue = (val: any) => {
      if (typeof val === 'number') {
        return val.toFixed(2);
      }
      return String(val);
    };

    return (
      <div key={field} className="flex items-center justify-between text-sm">
        <span className="text-bg-400">{label}</span>
        <div className="flex items-center gap-2">
          <span className="font-mono text-bg-300">{formatValue(origVal)}</span>
          <ArrowRight size={12} className="text-bg-500" />
          <span className="font-mono text-bg-100">{formatValue(cleanedVal)}</span>
          {trend !== 'same' && (
            <span
              className={`flex items-center gap-1 text-xs ${
                trend === 'up' ? 'text-success-400' : 'text-warning-400'
              }`}
            >
              {trend === 'up' ? (
                <TrendingUp size={12} />
              ) : (
                <TrendingDown size={12} />
              )}
              {diff > 0 ? '+' : ''}
              {diff.toFixed(2)}
            </span>
          )}
          {trend === 'same' && <Minus size={12} className="text-bg-500" />}
        </div>
      </div>
    );
  };

  const renderRowDiff = (origRow: any[], cleanedRow: any[], index: number) => {
    const rowKey = `${currentPage}-${index}`;

    return (
      <tr key={rowKey} className="border-b border-bg-700 hover:bg-bg-800/50">
        <td className="px-3 py-2 text-xs text-bg-500 font-mono">
          {currentPage * pageSize + index + 1}
        </td>
        {uploadedData.columns.map((col, colIndex) => {
          const origVal = origRow[colIndex];
          const cleanedVal = cleanedRow[colIndex];
          const isChanged = JSON.stringify(origVal) !== JSON.stringify(cleanedVal);
          const isMissing =
            origVal === null || origVal === undefined || origVal === '';
          const wasFilled = isMissing && cleanedVal !== null && cleanedVal !== undefined && cleanedVal !== '';

          return (
            <td
              key={`${rowKey}-${colIndex}`}
              className={`px-3 py-2 text-sm ${
                wasFilled
                  ? 'bg-success-500/10 text-success-300'
                  : isChanged
                  ? 'bg-warning-500/10 text-warning-300'
                  : 'text-bg-200'
              }`}
            >
              {cleanedVal !== undefined && cleanedVal !== null
                ? String(cleanedVal)
                : '-'}
              {wasFilled && (
                <span className="ml-1 text-xs text-success-500">(填充)</span>
              )}
            </td>
          );
        })}
      </tr>
    );
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 统计对比 */}
      {originalStats && cleanedStats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {originalStats.columns.map((origCol, idx) => {
            const cleanedCol = cleanedStats.columns[idx];
            if (!cleanedCol) return null;

            return (
              <div key={origCol.name} className="card">
                <div className="card-header !py-3">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-bg-100 text-sm">
                      {origCol.name}
                    </h4>
                    <TypeBadge type={origCol.type} />
                  </div>
                </div>
                <div className="card-body !py-3 space-y-2">
                  {origCol.type === 'numeric' ? (
                    <>
                      {renderStatComparison(origCol, cleanedCol, 'mean', '均值')}
                      {renderStatComparison(origCol, cleanedCol, 'median', '中位数')}
                      {renderStatComparison(origCol, cleanedCol, 'stdDev', '标准差')}
                      {renderStatComparison(origCol, cleanedCol, 'min', '最小值')}
                      {renderStatComparison(origCol, cleanedCol, 'max', '最大值')}
                      {renderStatComparison(origCol, cleanedCol, 'missingCount', '缺失值', false)}
                      {renderStatComparison(origCol, cleanedCol, 'outlierCount', '异常值', false)}
                    </>
                  ) : (
                    <>
                      {renderStatComparison(origCol, cleanedCol, 'uniqueCount', '唯一值', false)}
                      {renderStatComparison(origCol, cleanedCol, 'missingCount', '缺失值', false)}
                      {renderStatComparison(origCol, cleanedCol, 'mode', '众数', false)}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 数据对比表格 */}
      <div className="card">
        <div className="card-header flex items-center justify-between">
          <h3 className="font-semibold text-bg-100">数据对比预览</h3>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-success-500/30 border border-success-500/50" />
              <span className="text-bg-400">已填充</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-warning-500/30 border border-warning-500/50" />
              <span className="text-bg-400">已修改</span>
            </div>
          </div>
        </div>
        <div className="card-body p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-bg-800 sticky top-0">
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-medium text-bg-400 uppercase tracking-wider w-16">
                    #
                  </th>
                  {uploadedData.columns.map((col) => (
                    <th
                      key={col}
                      className="px-3 py-3 text-left text-xs font-medium text-bg-400 uppercase tracking-wider"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-bg-700">
                {displayData &&
                  displayData.cleanedRows.map((row, idx) =>
                    renderRowDiff(
                      displayData.originalRows[idx] || [],
                      row,
                      idx
                    )
                  )}
              </tbody>
            </table>
          </div>

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-bg-700">
              <div className="text-sm text-bg-400">
                显示 {currentPage * pageSize + 1} -{' '}
                {Math.min((currentPage + 1) * pageSize, cleaningResult.data.length)}{' '}
                行，共 {cleaningResult.data.length} 行
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                  disabled={currentPage === 0}
                  className="btn btn-ghost text-sm !py-1 !px-3"
                >
                  上一页
                </button>
                <span className="text-sm text-bg-400 self-center">
                  {currentPage + 1} / {totalPages}
                </span>
                <button
                  onClick={() =>
                    setCurrentPage(Math.min(totalPages - 1, currentPage + 1))
                  }
                  disabled={currentPage === totalPages - 1}
                  className="btn btn-ghost text-sm !py-1 !px-3"
                >
                  下一页
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
