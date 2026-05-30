import { useState, useEffect } from 'react';
import { X, Tag, AlertTriangle, TrendingUp } from 'lucide-react';
import type { AnnotationType, Annotation } from '../types';
import { getAnnotationColor, getAnnotationTypeName } from '../utils/export';

interface AnnotationFormProps {
  dataPointIndex: number;
  dataPoint: { x: any; y: number };
  onSubmit: (data: { type: AnnotationType; label: string; description: string }) => void;
  onCancel: () => void;
  editAnnotation?: Annotation | null;
}

const annotationTypes: { value: AnnotationType; label: string; icon: any; description: string }[] = [
  { value: 'classification', label: '分类标注', icon: Tag, description: '对数据点进行分类' },
  { value: 'anomaly', label: '异常标记', icon: AlertTriangle, description: '标记异常数据点' },
  { value: 'trend', label: '趋势标注', icon: TrendingUp, description: '标注趋势变化点' },
];

export const AnnotationForm = ({
  dataPointIndex,
  dataPoint,
  onSubmit,
  onCancel,
  editAnnotation,
}: AnnotationFormProps) => {
  const [type, setType] = useState<AnnotationType>(editAnnotation?.type || 'classification');
  const [label, setLabel] = useState(editAnnotation?.label || '');
  const [description, setDescription] = useState(editAnnotation?.description || '');

  useEffect(() => {
    if (editAnnotation) {
      setType(editAnnotation.type);
      setLabel(editAnnotation.label);
      setDescription(editAnnotation.description || '');
    }
  }, [editAnnotation]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim()) return;
    onSubmit({ type, label, description });
  };

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 shadow-xl w-80">
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div>
          <h3 className="text-white font-semibold">
            {editAnnotation ? '编辑标注' : '添加标注'}
          </h3>
          <p className="text-sm text-slate-400">
            数据点 #{dataPointIndex}: ({String(dataPoint.x)}, {dataPoint.y.toFixed(2)})
          </p>
        </div>
        <button
          onClick={onCancel}
          className="p-1 hover:bg-slate-700 rounded-lg transition-colors text-slate-400"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="p-4 space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">标注类型</label>
          <div className="space-y-2">
            {annotationTypes.map((t) => {
              const Icon = t.icon;
              const isSelected = type === t.value;
              return (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setType(t.value)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
                    isSelected
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-600 bg-slate-700 hover:border-slate-500'
                  }`}
                >
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: getAnnotationColor(t.value) + '30' }}
                  >
                    <Icon className="w-4 h-4" style={{ color: getAnnotationColor(t.value) }} />
                  </div>
                  <div className="text-left">
                    <p className={`text-sm font-medium ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                      {t.label}
                    </p>
                    <p className="text-xs text-slate-500">{t.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">标注标签</label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="输入标签名称"
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 text-sm"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">描述（可选）</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="添加详细描述"
            rows={2}
            className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 text-sm resize-none"
          />
        </div>

        <div className="flex gap-2 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={!label.trim()}
            className="flex-1 px-3 py-2 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: getAnnotationColor(type) }}
          >
            {editAnnotation ? '保存修改' : '添加标注'}
          </button>
        </div>
      </form>
    </div>
  );
};
