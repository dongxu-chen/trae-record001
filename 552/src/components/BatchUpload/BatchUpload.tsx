import { useState, useCallback, useRef } from 'react';
import { Upload, X, FileText, CheckCircle, XCircle, Loader2, AlertTriangle } from 'lucide-react';
import { useVerificationStore } from '@/store/verificationStore';
import { verificationApi } from '@/services/api';
import { cn } from '@/lib/utils';
import type { BatchFileStatus, VerifyResponse } from '../../../shared';

const MAX_BATCH_SIZE = 20;
const MAX_FILE_SIZE = 10 * 1024 * 1024;

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

export default function BatchUpload() {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const {
    batchFiles, addBatchFiles, removeBatchFile, clearBatchFiles,
    verifyOptions, setBatchResult, isBatchVerifying, setIsBatchVerifying,
    setError, error
  } = useVerificationStore();

  const [pollTimer, setPollTimer] = useState<NodeJS.Timeout | null>(null);

  const validateFiles = useCallback((files: File[]): File[] => {
    return files.filter(file => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      const validExts = ['.pdf', '.xml', '.p7s', '.p7m', '.pkcs7', '.der', '.pem'];
      return validExts.includes(ext) && file.size <= MAX_FILE_SIZE;
    });
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    const valid = validateFiles(files).slice(0, MAX_BATCH_SIZE - batchFiles.length);
    if (valid.length > 0) addBatchFiles(valid);
  }, [validateFiles, batchFiles.length, addBatchFiles]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const valid = validateFiles(files).slice(0, MAX_BATCH_SIZE - batchFiles.length);
    if (valid.length > 0) addBatchFiles(valid);
    if (inputRef.current) inputRef.current.value = '';
  }, [validateFiles, batchFiles.length, addBatchFiles]);

  const handleBatchVerify = useCallback(async () => {
    if (batchFiles.length === 0) return;
    setIsBatchVerifying(true);
    setError(null);

    try {
      const result = await verificationApi.batchVerify(batchFiles, verifyOptions);
      setBatchResult(result);

      if (result.status === 'processing' && result.batchId) {
        const timer = setInterval(async () => {
          try {
            const status = await verificationApi.getBatchStatus(result.batchId);
            setBatchResult(status);
            if (status.status !== 'processing') {
              clearInterval(timer);
              setPollTimer(null);
              setIsBatchVerifying(false);
            }
          } catch {
            clearInterval(timer);
            setPollTimer(null);
            setIsBatchVerifying(false);
          }
        }, 2000);
        setPollTimer(timer);
      } else {
        setIsBatchVerifying(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '批量验证失败');
      setIsBatchVerifying(false);
    }
  }, [batchFiles, verifyOptions, setIsBatchVerifying, setError, setBatchResult]);

  const { batchResult } = useVerificationStore();

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      case 'failed': return <XCircle className="w-5 h-5 text-red-500" />;
      case 'processing': return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      default: return <div className="w-5 h-5 rounded-full border-2 border-gray-300" />;
    }
  };

  const getResultColor = (result?: string) => {
    switch (result) {
      case 'valid': return 'text-emerald-600';
      case 'invalid': return 'text-red-600';
      case 'warning': return 'text-amber-600';
      default: return 'text-gray-500';
    }
  };

  return (
    <div className="space-y-6">
      <div
        className={cn(
          'relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 transition-all cursor-pointer min-h-[140px]',
          isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50',
          batchFiles.length > 0 && 'border-solid border-gray-200 bg-gray-50'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.xml,.p7s,.p7m,.pkcs7,.der,.pem"
          onChange={handleInputChange}
          className="hidden"
        />
        <Upload className={cn('w-8 h-8 mb-2', isDragging ? 'text-blue-500' : 'text-gray-400')} />
        <p className="text-sm font-medium text-gray-700">
          {isDragging ? '释放以添加文件' : '拖拽或点击添加文件'}
        </p>
        <p className="text-xs text-gray-400 mt-1">
          最多 {MAX_BATCH_SIZE} 个文件，单个文件最大 10MB
        </p>
      </div>

      {batchFiles.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">
              已选择 {batchFiles.length} 个文件
            </span>
            <div className="flex gap-2">
              <button
                onClick={clearBatchFiles}
                className="text-xs text-gray-500 hover:text-red-500 transition-colors"
                disabled={isBatchVerifying}
              >
                清空
              </button>
            </div>
          </div>

          <div className="space-y-2 max-h-[300px] overflow-y-auto">
            {batchFiles.map((file, idx) => {
              const batchFile = batchResult?.files.find(f => f.fileName === file.name);
              return (
                <div key={idx} className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg">
                  <FileText className="w-5 h-5 text-blue-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                    <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                  </div>
                  {batchFile && getStatusIcon(batchFile.status)}
                  {batchFile?.result && (
                    <span className={cn('text-xs font-medium', getResultColor(batchFile.result.overallResult))}>
                      {batchFile.result.score}分
                    </span>
                  )}
                  {!isBatchVerifying && (
                    <button
                      onClick={(e) => { e.stopPropagation(); removeBatchFile(idx); }}
                      className="p-1 hover:bg-gray-100 rounded"
                    >
                      <X className="w-4 h-4 text-gray-400 hover:text-red-500" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          {!batchResult && (
            <button
              onClick={handleBatchVerify}
              disabled={isBatchVerifying || batchFiles.length === 0}
              className={cn(
                'w-full py-3 rounded-lg font-medium text-white transition-colors',
                isBatchVerifying ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
              )}
            >
              {isBatchVerifying ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  验证中...
                </span>
              ) : (
                `开始批量验证 (${batchFiles.length} 个文件)`
              )}
            </button>
          )}
        </div>
      )}

      {batchResult && (
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-3">批量验证结果</h4>
            <div className="grid grid-cols-3 gap-4 text-center mb-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="text-2xl font-bold text-gray-900">{batchResult.totalFiles}</div>
                <div className="text-xs text-gray-500">总计</div>
              </div>
              <div className="p-3 bg-emerald-50 rounded-lg">
                <div className="text-2xl font-bold text-emerald-600">{batchResult.completedFiles}</div>
                <div className="text-xs text-gray-500">通过</div>
              </div>
              <div className="p-3 bg-red-50 rounded-lg">
                <div className="text-2xl font-bold text-red-600">{batchResult.failedFiles}</div>
                <div className="text-xs text-gray-500">失败</div>
              </div>
            </div>

            {batchResult.status === 'processing' && (
              <div className="flex items-center gap-2 text-blue-600 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                正在验证中，已完成 {batchResult.completedFiles + batchResult.failedFiles}/{batchResult.totalFiles}...
              </div>
            )}
          </div>

          {batchResult.status === 'completed' && (
            <button
              onClick={clearBatchFiles}
              className="w-full py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors text-sm"
            >
              开始新的批量验证
            </button>
          )}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}
