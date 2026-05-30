import React from 'react';
import { X, Download } from 'lucide-react';
import { DataRow } from '@/types';
import { exportDrillDownToExcel } from '@/utils/excelExport';
import { formatNumber } from '@/utils/pivotUtils';

interface DrillDownModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: DataRow[];
  rowFilters: { [field: string]: string };
  colFilters: { [field: string]: string };
  valueField: string;
}

export const DrillDownModal: React.FC<DrillDownModalProps> = ({
  isOpen,
  onClose,
  data,
  rowFilters,
  colFilters,
  valueField,
}) => {
  if (!isOpen) return null;

  const allFilters = { ...rowFilters, ...colFilters };
  const columns = data.length > 0 ? Object.keys(data[0]) : [];

  const handleExport = () => {
    exportDrillDownToExcel(data, '明细数据.xlsx');
  };

  const totalValue = data.reduce((sum, row) => {
    const val = Number(row[valueField]) || 0;
    return sum + val;
  }, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      <div className="relative w-full max-w-5xl max-h-[85vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h3 className="text-lg font-semibold text-gray-800">数据明细</h3>
            <div className="flex flex-wrap gap-2 mt-2">
              {Object.entries(allFilters).map(([key, value]) => (
                <span
                  key={key}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-700"
                >
                  {key}: {value}
                </span>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleExport}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-primary-600 
                bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors"
            >
              <Download size={16} />
              导出Excel
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          {data.length > 0 ? (
            <table className="w-full text-sm">
              <thead className="sticky top-0">
                <tr className="bg-gray-50">
                  <th className="px-4 py-3 text-left font-semibold text-gray-600 border-b border-gray-200">
                    #
                  </th>
                  {columns.map(col => (
                    <th
                      key={col}
                      className={`px-4 py-3 text-left font-semibold border-b border-gray-200 ${
                        col === valueField ? 'text-primary-600 bg-primary-50' : 'text-gray-600'
                      }`}
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((row, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 border-b border-gray-100">
                    <td className="px-4 py-3 text-gray-400 font-mono text-xs">
                      {idx + 1}
                    </td>
                    {columns.map(col => (
                      <td
                        key={col}
                        className={`px-4 py-3 ${
                          col === valueField
                            ? 'font-semibold text-primary-600'
                            : 'text-gray-700'
                        }`}
                      >
                        {typeof row[col] === 'number'
                          ? formatNumber(row[col] as number)
                          : row[col]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-400">
              暂无数据
            </div>
          )}
        </div>

        <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
          <span className="text-sm text-gray-500">
            共 <span className="font-semibold text-gray-700">{data.length}</span> 条记录
          </span>
          <span className="text-sm text-gray-500">
            {valueField} 合计:{' '}
            <span className="font-semibold text-primary-600">{formatNumber(totalValue)}</span>
          </span>
        </div>
      </div>
    </div>
  );
};
