import { useState } from 'react';
import { LineChart, ScatterChart, BarChart3 } from 'lucide-react';
import { Modal } from './Modal';
import type { ChartType } from '../types';
import Papa from 'papaparse';
import { generateId } from '../stores/useStore';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (project: any) => void;
}

const chartTypes: { value: ChartType; label: string; icon: any; description: string }[] = [
  { value: 'timeSeries', label: '时序图', icon: LineChart, description: '时间序列数据分析' },
  { value: 'scatter', label: '散点图', icon: ScatterChart, description: '相关性分析' },
  { value: 'bar', label: '柱状图', icon: BarChart3, description: '分类对比分析' },
];

export const CreateProjectModal = ({ isOpen, onClose, onCreate }: CreateProjectModalProps) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [chartType, setChartType] = useState<ChartType>('timeSeries');
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProcessing(true);

    let dataPoints: any[] = [];

    if (file) {
      const text = await file.text();
      const result = Papa.parse(text, { header: true, skipEmptyLines: true });
      dataPoints = result.data.map((row: any) => ({
        x: row.x || row.date || row.time || row[0],
        y: parseFloat(row.y || row.value || row[1]) || 0,
      }));
    }

    if (dataPoints.length === 0) {
      dataPoints = Array.from({ length: 50 }, (_, i) => ({
        x: chartType === 'timeSeries' ? `2024-${String(i + 1).padStart(2, '0')}-01` : i,
        y: Math.random() * 100 + 20,
      }));
    }

    const project = {
      id: generateId(),
      name,
      description,
      chartType,
      dataPoints,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      dataFileName: file?.name,
    };

    onCreate(project);
    setName('');
    setDescription('');
    setChartType('timeSeries');
    setFile(null);
    setIsProcessing(false);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="创建新项目">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">项目名称</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="输入项目名称"
            className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">项目描述</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="输入项目描述"
            rows={3}
            className="w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all resize-none"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-3">图表类型</label>
          <div className="grid grid-cols-3 gap-3">
            {chartTypes.map((type) => {
              const Icon = type.icon;
              const isSelected = chartType === type.value;
              return (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setChartType(type.value)}
                  className={`p-4 rounded-xl border-2 transition-all text-center ${
                    isSelected
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-600 bg-slate-700 hover:border-slate-500'
                  }`}
                >
                  <Icon className={`w-8 h-8 mx-auto mb-2 ${isSelected ? 'text-blue-400' : 'text-slate-400'}`} />
                  <p className={`text-sm font-medium ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                    {type.label}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">{type.description}</p>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">数据文件（可选）</label>
          <div className="border-2 border-dashed border-slate-600 rounded-xl p-6 text-center hover:border-slate-500 transition-colors">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <div className="text-slate-400">
                {file ? (
                  <p className="text-white">已选择: {file.name}</p>
                ) : (
                  <>
                    <p className="text-sm">点击上传 CSV 文件</p>
                    <p className="text-xs mt-1">支持包含 x/y 列的 CSV 格式</p>
                  </>
                )}
              </div>
            </label>
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white font-medium rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={!name || isProcessing}
            className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
          >
            {isProcessing ? '处理中...' : '创建项目'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
