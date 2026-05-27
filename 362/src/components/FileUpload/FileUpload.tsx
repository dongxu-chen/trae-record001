import React, { useCallback, useState, useRef } from 'react';
import { Upload, FileSpreadsheet, Database, AlertCircle } from 'lucide-react';
import { parseFile } from '../../utils/dataProcessor';
import { calculateDatasetStats } from '../../utils/statistics';
import { useDataStore } from '../../store/useDataStore';
import type { UploadedData, FileInfo } from '../../types';

interface FileUploadProps {
  className?: string;
}

export const FileUpload: React.FC<FileUploadProps> = ({ className = '' }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { setUploadedData, setWorker, uploadedData, resetAll } = useDataStore();

  const processFile = useCallback(
    async (file: File) => {
      setIsLoading(true);
      setError(null);

      try {
        const fileName = file.name.toLowerCase();
        if (!fileName.endsWith('.csv') && !fileName.endsWith('.xlsx') && !fileName.endsWith('.xls')) {
          throw new Error('不支持的文件格式，请上传CSV或Excel文件');
        }

        if (file.size > 50 * 1024 * 1024) {
          throw new Error('文件大小超过限制（最大50MB）');
        }

        const { data, columns } = await parseFile(file);

        if (data.length === 0) {
          throw new Error('文件为空或未检测到有效数据');
        }

        const stats = calculateDatasetStats(data, columns);

        const fileInfo: FileInfo = {
          name: file.name,
          size: file.size,
          type: file.type,
          rows: data.length,
          columns: columns.length,
        };

        const uploaded: UploadedData = {
          data,
          columns,
          fileInfo,
          stats,
        };

        setUploadedData(uploaded);

        const worker = new Worker(
          new URL('../../workers/dataCleaner.worker.ts', import.meta.url),
          { type: 'module' }
        );
        setWorker(worker);

        worker.postMessage({
          type: 'INIT',
          payload: { data, columns },
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : '文件处理失败');
      } finally {
        setIsLoading(false);
      }
    },
    [setUploadedData, setWorker]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        processFile(files[0]);
      }
    },
    [processFile]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        processFile(files[0]);
      }
    },
    [processFile]
  );

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const loadSampleData = useCallback(
    async (type: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/data-cleaner/sample-data/${type}`);
        const result = await response.json();
        if (result.success) {
          const { data, columns } = result.data;
          const stats = calculateDatasetStats(data, columns);
          const fileInfo: FileInfo = {
            name: `${type}_sample.csv`,
            size: JSON.stringify(data).length,
            type: 'text/csv',
            rows: data.length,
            columns: columns.length,
          };
          const uploaded: UploadedData = { data, columns, fileInfo, stats };
          setUploadedData(uploaded);

          const worker = new Worker(
            new URL('../../workers/dataCleaner.worker.ts', import.meta.url),
            { type: 'module' }
          );
          setWorker(worker);
          worker.postMessage({ type: 'INIT', payload: { data, columns } });
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载示例数据失败');
      } finally {
        setIsLoading(false);
      }
    },
    [setUploadedData, setWorker]
  );

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  if (uploadedData) {
    return (
      <div className={`card ${className}`}>
        <div className="card-header">
          <h3 className="font-semibold text-bg-100 flex items-center gap-2">
            <Database size={18} className="text-primary-400" />
            数据文件
          </h3>
          <button onClick={resetAll} className="btn btn-ghost text-sm py-1 px-3">
            重新上传
          </button>
        </div>
        <div className="card-body">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-12 h-12 rounded-lg bg-primary-500/20 flex items-center justify-center">
              <FileSpreadsheet size={24} className="text-primary-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-bg-100 truncate">{uploadedData.fileInfo.name}</p>
              <p className="text-sm text-bg-400">
                {formatFileSize(uploadedData.fileInfo.size)} · {uploadedData.fileInfo.rows.toLocaleString()} 行 ·{' '}
                {uploadedData.fileInfo.columns} 列
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="status-dot status-success" />
              <span className="text-sm text-success-400">已加载</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="bg-bg-900 rounded-lg p-3 text-center">
              <p className="text-2xl font-mono font-bold text-primary-400">
                {uploadedData.stats.rowCount.toLocaleString()}
              </p>
              <p className="text-xs text-bg-400">数据行数</p>
            </div>
            <div className="bg-bg-900 rounded-lg p-3 text-center">
              <p className="text-2xl font-mono font-bold text-warning-400">
                {uploadedData.stats.totalMissing.toLocaleString()}
              </p>
              <p className="text-xs text-bg-400">缺失值</p>
            </div>
            <div className="bg-bg-900 rounded-lg p-3 text-center">
              <p className="text-2xl font-mono font-bold text-danger-400">
                {uploadedData.stats.totalDuplicates.toLocaleString()}
              </p>
              <p className="text-xs text-bg-400">重复值</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`card ${className}`}>
      <div className="card-header">
        <h3 className="font-semibold text-bg-100 flex items-center gap-2">
          <Upload size={18} className="text-primary-400" />
          上传数据
        </h3>
      </div>
      <div className="card-body">
        <div
          onClick={handleClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`drop-zone ${isDragging ? 'drag-over' : ''} ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileSelect}
            className="hidden"
          />

          {isLoading ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
              <p className="text-bg-200">正在处理文件...</p>
            </div>
          ) : (
            <>
              <Upload size={48} className="text-bg-500 mb-3" />
              <p className="text-lg font-medium text-bg-200 mb-1">拖拽文件到此处</p>
              <p className="text-sm text-bg-400 mb-3">或点击选择文件</p>
              <p className="text-xs text-bg-500">支持 CSV、Excel (.xlsx, .xls) 格式，最大 50MB</p>
            </>
          )}
        </div>

        {error && (
          <div className="mt-4 p-3 bg-danger-500/10 border border-danger-500/30 rounded-lg flex items-start gap-2">
            <AlertCircle size={18} className="text-danger-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-danger-400">{error}</p>
          </div>
        )}

        <div className="mt-4">
          <p className="text-sm text-bg-400 mb-2">或加载示例数据：</p>
          <div className="flex gap-2">
            <button
              onClick={() => loadSampleData('sales')}
              disabled={isLoading}
              className="btn btn-secondary text-sm flex-1"
            >
              销售数据
            </button>
            <button
              onClick={() => loadSampleData('customers')}
              disabled={isLoading}
              className="btn btn-secondary text-sm flex-1"
            >
              客户数据
            </button>
            <button
              onClick={() => loadSampleData('sensor')}
              disabled={isLoading}
              className="btn btn-secondary text-sm flex-1"
            >
              传感器数据
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
