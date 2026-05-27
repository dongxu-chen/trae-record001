import React from 'react';
import { Play, Square, RotateCcw, Download, FileCode, FileSpreadsheet, FileText } from 'lucide-react';
import { useDataStore } from '../../store/useDataStore';
import { ProgressBar } from '../common/ProgressBar';
import { Badge } from '../common/Badge';
import { exportToCSV, exportToExcel } from '../../utils/dataProcessor';
import { downloadScript, copyToClipboard, downloadRequirements } from '../../utils/scriptGenerator';

interface CleaningControlProps {
  className?: string;
}

export const CleaningControl: React.FC<CleaningControlProps> = ({ className = '' }) => {
  const {
    uploadedData,
    cleaningResult,
    isCleaning,
    cleaningProgress,
    currentStep,
    error,
    startCleaning,
    cancelCleaning,
    resetAll,
  } = useDataStore();

  const handleExportCSV = () => {
    if (cleaningResult) {
      exportToCSV(cleaningResult.data, cleaningResult.columns, 'cleaned_data.csv');
    } else if (uploadedData) {
      exportToCSV(uploadedData.data, uploadedData.columns, 'original_data.csv');
    }
  };

  const handleExportExcel = () => {
    if (cleaningResult) {
      exportToExcel(cleaningResult.data, cleaningResult.columns, 'cleaned_data.xlsx');
    } else if (uploadedData) {
      exportToExcel(uploadedData.data, uploadedData.columns, 'original_data.xlsx');
    }
  };

  const handleExportScript = () => {
    if (cleaningResult?.script) {
      downloadScript(cleaningResult.script, 'cleaning_script.py');
    }
  };

  const handleCopyScript = async () => {
    if (cleaningResult?.script) {
      await copyToClipboard(cleaningResult.script);
    }
  };

  if (!uploadedData) {
    return null;
  }

  return (
    <div className={`card ${className}`}>
      <div className="card-header">
        <h3 className="font-semibold text-bg-100 flex items-center gap-2">
          <Play size={18} className="text-primary-400" />
          清洗控制
        </h3>
      </div>
      <div className="card-body space-y-4">
        {isCleaning && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-bg-300">{currentStep}</span>
              <span className="status-dot status-processing" />
            </div>
            <ProgressBar progress={cleaningProgress} />
          </div>
        )}

        {cleaningResult && !isCleaning && (
          <div className="bg-bg-900 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-bg-300">清洗状态</span>
              <Badge type={cleaningResult.success ? 'success' : 'danger'}>
                {cleaningResult.success ? '成功' : '失败'}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="flex justify-between">
                <span className="text-bg-400">耗时</span>
                <span className="font-mono text-bg-200">{cleaningResult.duration.toFixed(2)}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-bg-400">删除行</span>
                <span className="font-mono text-danger-400">-{cleaningResult.changes.rowsRemoved}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-bg-400">填充值</span>
                <span className="font-mono text-success-400">+{cleaningResult.changes.valuesFilled}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-bg-400">处理异常值</span>
                <span className="font-mono text-warning-400">{cleaningResult.changes.outliersHandled}</span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 bg-danger-500/10 border border-danger-500/30 rounded-lg text-sm text-danger-400">
            {error}
          </div>
        )}

        <div className="flex gap-2">
          {!isCleaning ? (
            <>
              <button
                onClick={startCleaning}
                disabled={!uploadedData}
                className="btn btn-primary flex-1"
              >
                <Play size={16} />
                开始清洗
              </button>
              <button onClick={resetAll} className="btn btn-ghost">
                <RotateCcw size={16} />
              </button>
            </>
          ) : (
            <button onClick={cancelCleaning} className="btn btn-danger flex-1">
              <Square size={16} />
              取消清洗
            </button>
          )}
        </div>

        {cleaningResult && (
          <>
            <div className="pt-4 border-t border-bg-700">
              <p className="text-sm text-bg-400 mb-3">导出数据</p>
              <div className="flex gap-2">
                <button onClick={handleExportCSV} className="btn btn-secondary flex-1 text-sm">
                  <FileSpreadsheet size={16} />
                  CSV
                </button>
                <button onClick={handleExportExcel} className="btn btn-secondary flex-1 text-sm">
                  <FileSpreadsheet size={16} />
                  Excel
                </button>
              </div>
            </div>
            <div className="pt-4 border-t border-bg-700">
              <p className="text-sm text-bg-400 mb-3">导出脚本</p>
              <div className="flex gap-2">
                <button onClick={handleCopyScript} className="btn btn-secondary flex-1 text-sm">
                  <FileCode size={16} />
                  复制
                </button>
                <button onClick={downloadRequirements} className="btn btn-secondary text-sm" title="下载 requirements.txt">
                  <FileText size={16} />
                </button>
                <button onClick={handleExportScript} className="btn btn-success flex-1 text-sm">
                  <Download size={16} />
                  下载 .py
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
