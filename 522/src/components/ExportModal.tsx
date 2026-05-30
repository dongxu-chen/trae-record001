import { useState } from 'react';
import { X, Download, Image, Settings } from 'lucide-react';
import useFilterStore from '@/store/filterStore';
import { FILTER_DEFINITIONS } from '@/utils/shaderManager';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (format: string, quality: number) => void;
}

export default function ExportModal({
  isOpen,
  onClose,
  onExport,
}: ExportModalProps) {
  const [format, setFormat] = useState('png');
  const [quality, setQuality] = useState(0.92);
  const { selectedImageId, images, activeFilter, filterIntensity } =
    useFilterStore();

  const selectedImage = images.find((img) => img.id === selectedImageId);
  const filterName =
    FILTER_DEFINITIONS.find((f) => f.id === activeFilter)?.name || '自定义';

  if (!isOpen) return null;

  const handleExport = () => {
    onExport(format, quality);
  };

  const formats = [
    { id: 'png', name: 'PNG', desc: '无损压缩，支持透明' },
    { id: 'jpeg', name: 'JPEG', desc: '有损压缩，文件较小' },
    { id: 'webp', name: 'WebP', desc: '现代格式，高效压缩' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-md glass-panel rounded-2xl overflow-hidden animate-fade-in">
        <div className="flex items-center justify-between p-4 border-b border-surface-border">
          <h3 className="font-display font-semibold text-lg neon-text">导出图片</h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-hover transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {selectedImage && (
            <div className="flex items-center gap-4 p-4 bg-surface-card rounded-lg">
              <div className="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0">
                <img
                  src={selectedImage.src}
                  alt={selectedImage.name}
                  className="w-full h-full object-cover"
                />
              </div>
              <div className="min-w-0">
                <p className="font-medium truncate">{selectedImage.name}</p>
                <p className="text-sm text-gray-400">
                  {selectedImage.width} × {selectedImage.height}px
                </p>
                <p className="text-xs text-neon-cyan mt-1">
                  滤镜: {filterName} · 强度: {Math.round(filterIntensity * 100)}%
                </p>
              </div>
            </div>
          )}

          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
              <Image size={16} />
              输出格式
            </div>
            <div className="grid grid-cols-3 gap-2">
              {formats.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setFormat(f.id)}
                  className={`p-3 rounded-lg border transition-all duration-200 text-center ${
                    format === f.id
                      ? 'border-neon-cyan bg-neon-cyan/10'
                      : 'border-surface-border hover:border-surface-hover bg-surface-card'
                  }`}
                >
                  <p className="font-medium">{f.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{f.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {format !== 'png' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
                  <Settings size={16} />
                  质量
                </div>
                <span className="text-xs text-neon-cyan font-mono">
                  {Math.round(quality * 100)}%
                </span>
              </div>
              <input
                type="range"
                min={0.1}
                max={1}
                step={0.01}
                value={quality}
                onChange={(e) => setQuality(parseFloat(e.target.value))}
                className="range-neon w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>低质量</span>
                <span>高质量</span>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 p-4 border-t border-surface-border bg-surface-card/50">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-surface-card rounded-lg text-sm font-medium hover:bg-surface-hover transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleExport}
            disabled={!selectedImage}
            className="px-6 py-2 bg-gradient-to-r from-neon-cyan to-neon-purple rounded-lg text-sm font-medium text-white hover:shadow-lg hover:shadow-neon-cyan/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Download size={16} />
            导出图片
          </button>
        </div>
      </div>
    </div>
  );
}
