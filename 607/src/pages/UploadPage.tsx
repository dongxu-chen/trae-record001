import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Papa from 'papaparse';
import { Upload, FileText, AlertCircle, CheckCircle, Database, Table, ArrowRight } from 'lucide-react';
import { useDataStore } from '../store/useDataStore';
import { previewData } from '../services/api';

export default function UploadPage() {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  const { data, columns, stats, columnInfo, setData, setColumns, setStats, setColumnInfo } = useDataStore();

  const handleFileUpload = useCallback(async (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setUploadError('请上传CSV格式的文件');
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: async (results) => {
        try {
          const parsedData = results.data as Record<string, any>[];
          const preview = await previewData(parsedData);
          
          setData(parsedData);
          setColumns(preview.columns);
          setStats(preview.stats);
          setColumnInfo(preview.columnInfo.map(c => ({
            ...c,
            type: c.type as 'numeric' | 'categorical' | 'binary'
          })));
          
          setIsUploading(false);
        } catch (error) {
          setUploadError(error instanceof Error ? error.message : '数据解析失败');
          setIsUploading(false);
        }
      },
      error: (error) => {
        setUploadError(`CSV解析失败: ${error.message}`);
        setIsUploading(false);
      }
    });
  }, [setData, setColumns, setStats, setColumnInfo]);

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
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  }, [handleFileUpload]);

  const loadSampleData = useCallback(async () => {
    setIsUploading(true);
    setUploadError(null);
    
    const sampleData = [];
    for (let i = 0; i < 200; i++) {
      const age = Math.floor(Math.random() * 40) + 25;
      const education = Math.floor(Math.random() * 4) + 1;
      const experience = Math.floor(Math.random() * 20) + 1;
      const treatment = Math.random() > 0.5 ? 1 : 0;
      const baseIncome = 30000 + age * 500 + education * 2000 + experience * 1000;
      const income = baseIncome + treatment * 5000 + Math.random() * 5000;
      
      sampleData.push({
        id: i + 1,
        age,
        education,
        experience,
        gender: Math.random() > 0.5 ? 1 : 0,
        treatment,
        income: Math.round(income),
      });
    }

    try {
      const preview = await previewData(sampleData);
      setData(sampleData);
      setColumns(preview.columns);
      setStats(preview.stats);
      setColumnInfo(preview.columnInfo.map(c => ({
        ...c,
        type: c.type as 'numeric' | 'categorical' | 'binary'
      })));
      setIsUploading(false);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : '加载示例数据失败');
      setIsUploading(false);
    }
  }, [setData, setColumns, setStats, setColumnInfo]);

  return (
    <div className="min-h-screen bg-grid-pattern">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8 animate-slide-up">
            <h2 className="font-display text-4xl font-semibold text-primary-800 mb-3">
              上传观测数据
            </h2>
            <p className="text-gray-600 max-w-lg mx-auto">
              上传您的CSV格式观测数据，或使用示例数据开始探索因果推断分析
            </p>
          </div>

          <div
            className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 ${
              isDragging
                ? 'border-primary-500 bg-primary-50 scale-[1.02]'
                : 'border-gray-200 bg-white hover:border-primary-300'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              type="file"
              accept=".csv"
              onChange={handleFileInput}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              disabled={isUploading}
            />
            
            {isUploading ? (
              <div className="flex flex-col items-center">
                <div className="w-16 h-16 border-4 border-primary-200 border-t-primary-500 rounded-full animate-spin mb-4" />
                <p className="text-primary-600 font-medium">正在处理数据...</p>
              </div>
            ) : data.length > 0 ? (
              <div className="flex flex-col items-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                  <CheckCircle className="w-8 h-8 text-green-600" />
                </div>
                <p className="text-green-600 font-semibold text-lg mb-1">数据上传成功</p>
                <p className="text-gray-500">
                  {stats?.rowCount} 行 × {stats?.columnCount} 列
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 transition-colors ${
                  isDragging ? 'bg-primary-100' : 'bg-gray-100'
                }`}>
                  <Upload className={`w-8 h-8 transition-colors ${
                    isDragging ? 'text-primary-600' : 'text-gray-400'
                  }`} />
                </div>
                <p className="text-gray-700 font-medium mb-1">
                  拖拽CSV文件到此处
                </p>
                <p className="text-gray-400 text-sm mb-4">
                  或点击选择文件
                </p>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <FileText className="w-4 h-4" />
                  <span>支持 .csv 格式，最大 50MB</span>
                </div>
              </div>
            )}
          </div>

          {uploadError && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 animate-slide-up">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-700 font-medium">上传失败</p>
                <p className="text-red-600 text-sm">{uploadError}</p>
              </div>
            </div>
          )}

          <div className="mt-6 text-center">
            <button
              onClick={loadSampleData}
              disabled={isUploading}
              className="text-primary-600 hover:text-primary-700 font-medium text-sm underline disabled:opacity-50 disabled:no-underline"
            >
              没有数据？使用示例数据体验
            </button>
          </div>

          {data.length > 0 && (
            <div className="mt-8 animate-fade-in">
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="stat-card">
                  <div className="flex items-center gap-2 mb-2">
                    <Database className="w-5 h-5 opacity-80" />
                    <span className="text-sm opacity-80">总行数</span>
                  </div>
                  <p className="text-3xl font-semibold font-display">{stats?.rowCount}</p>
                </div>
                <div className="stat-card-accent">
                  <div className="flex items-center gap-2 mb-2">
                    <Table className="w-5 h-5 opacity-80" />
                    <span className="text-sm opacity-80">总列数</span>
                  </div>
                  <p className="text-3xl font-semibold font-display">{stats?.columnCount}</p>
                </div>
                <div className="bg-gradient-to-br from-data-teal to-data-blue text-white rounded-xl p-5">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-5 h-5 opacity-80" />
                    <span className="text-sm opacity-80">变量类型</span>
                  </div>
                  <p className="text-lg font-medium">
                    {columnInfo.filter(c => c.type === 'numeric').length} 数值 / 
                    {columnInfo.filter(c => c.type === 'binary').length} 二元
                  </p>
                </div>
              </div>

              <div className="card">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <Table className="w-5 h-5 text-primary-500" />
                  数据预览
                </h3>
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        {columns.slice(0, 8).map((col) => (
                          <th key={col} className="px-4 py-3 text-left font-medium text-gray-600">
                            {col}
                          </th>
                        ))}
                        {columns.length > 8 && (
                          <th className="px-4 py-3 text-left font-medium text-gray-400">
                            +{columns.length - 8} 更多
                          </th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {data.slice(0, 5).map((row, idx) => (
                        <tr key={idx} className="border-b border-gray-50 hover:bg-gray-50">
                          {columns.slice(0, 8).map((col) => (
                            <td key={col} className="px-4 py-3 text-gray-700">
                              {row[col]}
                            </td>
                          ))}
                          {columns.length > 8 && (
                            <td className="px-4 py-3 text-gray-400">...</td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => navigate('/configure')}
                  className="btn-primary flex items-center gap-2"
                >
                  继续配置变量
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
