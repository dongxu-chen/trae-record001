import { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Upload, FileSpreadsheet, Download, Trash2, Play, Check, AlertCircle, X } from 'lucide-react';
import Papa from 'papaparse';
import { toast } from '@/components/ui/toast';
import StylePanel from '@/components/StylePanel';
import { useAppStore } from '@/store';
import { batchGenerateAndDownload } from '@/utils/exportUtils';
import type { QRCodeType } from '@/types';

interface PreviewRow {
  type: QRCodeType;
  content: string;
  name?: string;
  _valid: boolean;
  _error?: string;
}

interface WorkerResult {
  name: string;
  dataUrl: string;
}

export default function BatchGenerate() {
  const { style, setStyle, resetStyle } = useAppStore();
  const [previewData, setPreviewData] = useState<PreviewRow[]>([]);
  const [fileName, setFileName] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentItem, setCurrentItem] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const workerRef = useRef<Worker | null>(null);

  const typeOptions: Array<{ value: QRCodeType; label: string }> = [
    { value: 'text', label: '文本' },
    { value: 'url', label: '网址' },
    { value: 'vcard', label: '名片' },
    { value: 'wifi', label: 'WiFi' },
    { value: 'email', label: '邮件' },
  ];

  const validateRow = (row: any, index: number): PreviewRow => {
    const content = (row.content || row.Content || row.data || '').toString().trim();
    const type = (row.type || row.Type || 'url').toString().trim().toLowerCase() as QRCodeType;
    
    let _valid = true;
    let _error: string | undefined;

    if (!content) {
      _valid = false;
      _error = '内容为空';
    }

    if (!['text', 'url', 'vcard', 'wifi', 'email'].includes(type)) {
      _valid = false;
      _error = '无效的类型';
    }

    return {
      type,
      content,
      name: (row.name || row.Name || `qrcode_${index + 1}`).toString(),
      _valid,
      _error,
    };
  };

  const handleFile = (file: File) => {
    if (!file.name.endsWith('.csv')) {
      toast.error('请上传CSV格式的文件');
      return;
    }

    setFileName(file.name);
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const validated = results.data.map((row: any, index: number) =>
          validateRow(row, index)
        );
        setPreviewData(validated);
        toast.success(`已加载 ${validated.length} 条数据`);
      },
      error: (error) => {
        toast.error('解析CSV文件失败: ' + error.message);
      },
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const cleanupWorker = useCallback(() => {
    if (workerRef.current) {
      workerRef.current.terminate();
      workerRef.current = null;
    }
  }, []);

  const handleCancel = () => {
    if (workerRef.current) {
      workerRef.current.postMessage({ type: 'cancel' });
      cleanupWorker();
      setIsProcessing(false);
      setProgress(0);
      setCurrentItem(0);
      toast.info('已取消生成');
    }
  };

  const handleGenerate = useCallback(async () => {
    const validRows = previewData.filter((r) => r._valid);
    if (validRows.length === 0) {
      toast.error('没有有效的数据行');
      return;
    }

    setIsProcessing(true);
    setProgress(0);
    setCurrentItem(0);
    setTotalItems(validRows.length);

    const batchRows = validRows.map((r) => ({
      content: r.content,
      name: r.name,
    }));

    try {
      const results = await new Promise<WorkerResult[]>((resolve, reject) => {
        cleanupWorker();
        
        const worker = new Worker(
          new URL('@/workers/batchGenerator.worker.ts', import.meta.url),
          { type: 'module' }
        );
        workerRef.current = worker;

        worker.onmessage = (event) => {
          const { type, progress: workerProgress, current, total, results: workerResults, error } = event.data;

          if (type === 'progress') {
            setProgress(workerProgress);
            setCurrentItem(current);
            setTotalItems(total);
          } else if (type === 'complete') {
            cleanupWorker();
            resolve(workerResults);
          } else if (type === 'error') {
            cleanupWorker();
            if (error === '已取消') {
              reject(new Error('cancelled'));
            } else {
              reject(new Error(error || '生成失败'));
            }
          }
        };

        worker.onerror = (error) => {
          cleanupWorker();
          reject(new Error(error.message));
        };

        worker.postMessage({
          type: 'start',
          rows: batchRows,
          style: {
            foregroundColor: style.foregroundColor,
            backgroundColor: style.backgroundColor,
            size: style.size,
            errorCorrectionLevel: style.errorCorrectionLevel,
            dotStyle: style.dotStyle,
            cornerRadius: style.cornerRadius,
          },
        });
      });

      await batchGenerateAndDownload(validRows, style, results);
      toast.success(`成功生成 ${results.length} 个二维码`);
    } catch (error) {
      if ((error as Error).message !== 'cancelled') {
        toast.error('批量生成失败: ' + (error as Error).message);
      }
    } finally {
      setIsProcessing(false);
      setProgress(0);
      setCurrentItem(0);
      cleanupWorker();
    }
  }, [previewData, style, cleanupWorker]);

  const clearData = () => {
    setPreviewData([]);
    setFileName('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const validCount = previewData.filter((r) => r._valid).length;
  const invalidCount = previewData.length - validCount;

  const downloadTemplate = () => {
    const template = 'type,content,name\nurl,https://example.com,示例二维码\ntext,Hello World,文本示例\n';
    const blob = new Blob([template], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'qr_template.csv';
    a.click();
    URL.revokeObjectURL(url);
    toast.success('模板已下载');
  };

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent mb-3">
            批量生成二维码
          </h1>
          <p className="text-slate-400">
            上传CSV文件，批量生成多个二维码（Web Worker多线程处理，不阻塞UI）
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
                  <FileSpreadsheet size={20} className="text-cyan-400" />
                  上传CSV文件
                </h2>
                <button
                  onClick={downloadTemplate}
                  className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                >
                  下载模板
                </button>
              </div>

              <div
                onDrop={handleDrop}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onClick={() => fileInputRef.current?.click()}
                className={`relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                  isDragging
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-slate-700 hover:border-slate-600 bg-slate-800/30'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                  className="hidden"
                />
                <Upload className="mx-auto h-12 w-12 text-slate-500 mb-4" />
                <p className="text-slate-300 mb-2">
                  {fileName ? fileName : '拖拽CSV文件到此处，或点击上传'}
                </p>
                <p className="text-sm text-slate-500">
                  文件需包含 type、content、name（可选）列
                </p>
              </div>
            </motion.div>

            {previewData.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-4">
                    <h3 className="font-semibold text-slate-200">
                      数据预览
                    </h3>
                    <span className="flex items-center gap-1 text-sm text-green-400">
                      <Check size={14} />
                      {validCount} 条有效
                    </span>
                    {invalidCount > 0 && (
                      <span className="flex items-center gap-1 text-sm text-red-400">
                        <AlertCircle size={14} />
                        {invalidCount} 条无效
                      </span>
                    )}
                  </div>
                  <button
                    onClick={clearData}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={14} />
                    清空
                  </button>
                </div>

                <div className="overflow-x-auto max-h-96 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-slate-900">
                      <tr>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">#</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">名称</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">类型</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">内容</th>
                        <th className="px-4 py-3 text-left text-slate-400 font-medium">状态</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {previewData.slice(0, 50).map((row, index) => (
                        <tr key={index} className={!row._valid ? 'bg-red-900/20' : ''}>
                          <td className="px-4 py-3 text-slate-500">{index + 1}</td>
                          <td className="px-4 py-3 text-slate-300">{row.name}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-1 rounded-full text-xs bg-slate-800 text-slate-400">
                              {typeOptions.find((t) => t.value === row.type)?.label || row.type}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-400 font-mono text-xs max-w-xs truncate">
                            {row.content}
                          </td>
                          <td className="px-4 py-3">
                            {row._valid ? (
                              <Check size={16} className="text-green-400" />
                            ) : (
                              <span className="text-xs text-red-400">{row._error}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {previewData.length > 50 && (
                    <p className="text-center text-slate-500 text-sm mt-4">
                      仅显示前50条，共 {previewData.length} 条数据
                    </p>
                  )}
                </div>

                <div className="mt-6 flex flex-col items-end gap-4">
                  {isProcessing && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="w-full max-w-md"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-slate-400">
                          生成进度 ({currentItem}/{totalItems})
                        </span>
                        <span className="text-sm text-cyan-400 font-medium">
                          {Math.round(progress)}%
                        </span>
                      </div>
                      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full bg-gradient-to-r from-blue-500 to-cyan-400"
                          initial={{ width: 0 }}
                          animate={{ width: `${progress}%` }}
                          transition={{ duration: 0.3 }}
                        />
                      </div>
                    </motion.div>
                  )}

                  <div className="flex gap-3">
                    {isProcessing ? (
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={handleCancel}
                        className="flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-800 text-slate-300 font-medium hover:bg-slate-700"
                      >
                        <X size={18} />
                        取消生成
                      </motion.button>
                    ) : (
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={handleGenerate}
                        disabled={validCount === 0}
                        className="flex items-center gap-2 px-8 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-medium shadow-lg shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Play size={18} />
                        开始生成 ({validCount})
                      </motion.button>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
          >
            <StylePanel style={style} onChange={setStyle} onReset={resetStyle} />
          </motion.div>
        </div>
      </div>
    </div>
  );
}
