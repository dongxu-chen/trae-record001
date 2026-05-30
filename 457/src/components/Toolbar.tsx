import React, { useRef } from 'react';
import { FileSpreadsheet, Download, Upload, Database, Settings } from 'lucide-react';
import { PivotResult } from '@/types';
import { exportToExcel, parseExcelFile } from '@/utils/excelExport';

interface ToolbarProps {
  pivotResult: PivotResult;
  rowFields: string[];
  colFields: string[];
  onDataUpload: (data: any[]) => void;
  onUseSampleData: () => void;
  onOpenSettings: () => void;
}

export const Toolbar: React.FC<ToolbarProps> = ({
  pivotResult,
  rowFields,
  colFields,
  onDataUpload,
  onUseSampleData,
  onOpenSettings,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExport = () => {
    exportToExcel(pivotResult, rowFields, colFields, '透视表.xlsx');
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      try {
        const data = await parseExcelFile(file);
        onDataUpload(data);
      } catch (error) {
        console.error('解析Excel失败:', error);
        alert('文件解析失败，请检查文件格式');
      }
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <FileSpreadsheet className="text-primary-500" size={28} />
          <div>
            <h1 className="text-xl font-bold text-gray-800">数据透视表</h1>
            <p className="text-xs text-gray-500">多维数据分析工具</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          onChange={handleFileChange}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 
            bg-white border border-gray-200 rounded-lg hover:bg-gray-50 
            hover:border-gray-300 transition-all shadow-sm"
        >
          <Upload size={16} />
          上传数据
        </button>
        <button
          onClick={onUseSampleData}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 
            bg-white border border-gray-200 rounded-lg hover:bg-gray-50 
            hover:border-gray-300 transition-all shadow-sm"
        >
          <Database size={16} />
          示例数据
        </button>
        <button
          onClick={handleExport}
          disabled={rowFields.length === 0 && colFields.length === 0}
          className={`
            flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg
            transition-all shadow-sm
            ${rowFields.length === 0 && colFields.length === 0
              ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
              : 'bg-primary-500 text-white hover:bg-primary-600 hover:shadow-md'
            }
          `}
        >
          <Download size={16} />
          导出Excel
        </button>
        <button
          onClick={onOpenSettings}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 
            bg-white border border-gray-200 rounded-lg hover:bg-gray-50 
            hover:border-gray-300 transition-all shadow-sm"
        >
          <Settings size={16} />
          设置
        </button>
      </div>
    </div>
  );
};
