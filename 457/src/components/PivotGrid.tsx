import React from 'react';
import { PivotResult, PivotCell } from '@/types';
import { formatNumber } from '@/utils/pivotUtils';
import { getLevelBgColor, getLevelBorderColor } from '@/utils/alertRules';

interface PivotGridProps {
  pivotResult: PivotResult;
  rowFields: string[];
  colFields: string[];
  onCellClick: (cell: PivotCell) => void;
}

export const PivotGrid: React.FC<PivotGridProps> = ({
  pivotResult,
  rowFields,
  colFields,
  onCellClick,
}) => {
  const { rowHeaders, colHeaders, data, rowTotals, colTotals, grandTotal } = pivotResult;

  const getCellClass = (cell: PivotCell | null, baseClass: string = ''): string => {
    if (!cell?.alertLevel) return baseClass;
    const bgClass = getLevelBgColor(cell.alertLevel);
    const borderClass = getLevelBorderColor(cell.alertLevel);
    return `${baseClass} ${bgClass} ${borderClass}`;
  };

  if (rowFields.length === 0 && colFields.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50 rounded-xl">
        <div className="text-center">
          <div className="text-6xl mb-4">📊</div>
          <p className="text-gray-500 text-lg">请拖拽字段到行、列或值区域</p>
          <p className="text-gray-400 text-sm mt-2">开始创建您的数据透视表</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <table className="pivot-table w-full border-collapse text-sm">
        <thead>
          {colFields.length > 0 && colFields.map((_, fieldIdx) => (
            <tr key={`col-header-${fieldIdx}`}>
              {fieldIdx === 0 && rowFields.map((rf, idx) => (
                <th
                  key={`row-field-${idx}`}
                  rowSpan={colFields.length}
                  className="bg-gray-100 text-gray-700"
                >
                  {rf}
                </th>
              ))}
              {colHeaders.map((colVals, colIdx) => (
                <th
                  key={`col-${fieldIdx}-${colIdx}`}
                  className="bg-gray-100 text-gray-700"
                >
                  {colVals[fieldIdx]}
                </th>
              ))}
              <th
                rowSpan={colFields.length}
                className="bg-primary-50 text-primary-700 total-col"
              >
                总计
              </th>
            </tr>
          ))}
          {colFields.length === 0 && rowFields.length > 0 && (
            <tr>
              {rowFields.map((rf, idx) => (
                <th key={`row-field-${idx}`} className="bg-gray-100 text-gray-700">
                  {rf}
                </th>
              ))}
              <th className="bg-primary-50 text-primary-700">值</th>
            </tr>
          )}
        </thead>
        <tbody>
          {rowHeaders.map((rowVals, rowIdx) => (
            <tr key={`row-${rowIdx}`} className="hover:bg-gray-50">
              {rowVals.map((val, idx) => (
                <td key={`row-val-${idx}`} className="font-medium text-gray-700">
                  {val}
                </td>
              ))}
              {colFields.length === 0 ? (
                <td
                  className={getCellClass(rowTotals[rowIdx], 'cell-value text-right')}
                  onClick={() => rowTotals[rowIdx] && onCellClick(rowTotals[rowIdx]!)}
                >
                  {rowTotals[rowIdx] ? formatNumber(rowTotals[rowIdx]!.value) : '-'}
                </td>
              ) : (
                <>
                  {colHeaders.map((_, colIdx) => (
                    <td
                      key={`cell-${rowIdx}-${colIdx}`}
                      className={getCellClass(data[rowIdx]?.[colIdx], 'cell-value text-right')}
                      onClick={() => data[rowIdx]?.[colIdx] && onCellClick(data[rowIdx][colIdx]!)}
                    >
                      {data[rowIdx]?.[colIdx]
                        ? formatNumber(data[rowIdx][colIdx]!.value)
                        : '-'}
                    </td>
                  ))}
                  <td
                    className={getCellClass(rowTotals[rowIdx], 'total-col text-right')}
                    onClick={() => rowTotals[rowIdx] && onCellClick(rowTotals[rowIdx]!)}
                  >
                    {rowTotals[rowIdx] ? formatNumber(rowTotals[rowIdx]!.value) : '-'}
                  </td>
                </>
              )}
            </tr>
          ))}
          {colFields.length > 0 && (
            <tr className="total-row">
              <td colSpan={rowFields.length} className="text-center text-gray-700">
                总计
              </td>
              {colHeaders.map((_, colIdx) => (
                <td
                  key={`total-col-${colIdx}`}
                  className={getCellClass(colTotals[colIdx], 'text-right')}
                  onClick={() => colTotals[colIdx] && onCellClick(colTotals[colIdx]!)}
                >
                  {colTotals[colIdx] ? formatNumber(colTotals[colIdx]!.value) : '-'}
                </td>
              ))}
              <td
                className={getCellClass(grandTotal, 'text-right font-bold text-primary-600')}
                onClick={() => grandTotal && onCellClick(grandTotal)}
              >
                {grandTotal ? formatNumber(grandTotal.value) : '-'}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};
