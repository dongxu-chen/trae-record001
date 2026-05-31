import { useState, useRef, useEffect } from 'react';
import { Image as ImageIcon, Loader2, Eye, ArrowLeftRight } from 'lucide-react';

function PreviewPanel({ originalImage, resultImage, previewImage, isProcessing, isPreviewing }) {
  const [compareMode, setCompareMode] = useState('side');
  const [sliderPosition, setSliderPosition] = useState(50);
  const containerRef = useRef(null);

  const displayImage = resultImage || previewImage;
  const hasImage = originalImage || displayImage;

  const handleSliderMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setSliderPosition(percentage);
  };

  if (!hasImage) {
    return (
      <div className="w-full aspect-square rounded-xl bg-gray-800/30 flex flex-col items-center justify-center">
        <ImageIcon className="w-16 h-16 text-gray-600 mb-4" />
        <p className="text-gray-500 text-center">
          上传图片并选择风格<br />
          后将在此处显示结果
        </p>
      </div>
    );
  }

  if (isProcessing) {
    return (
      <div className="w-full aspect-square rounded-xl bg-gray-800/30 flex flex-col items-center justify-center">
        <div className="loading-spinner w-12 h-12 mb-4" />
        <p className="text-gray-400">正在生成风格化图像...</p>
        <p className="text-gray-500 text-sm mt-2">请稍候，这可能需要几秒钟</p>
      </div>
    );
  }

  if (isPreviewing && !resultImage) {
    return (
      <div className="w-full aspect-square rounded-xl bg-gray-800/30 flex flex-col items-center justify-center">
        <div className="flex items-center gap-2 text-primary-400">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>生成预览中...</span>
        </div>
      </div>
    );
  }

  if (!displayImage) {
    return (
      <div className="w-full aspect-square rounded-xl overflow-hidden">
        <img
          src={originalImage}
          alt="Original"
          className="w-full h-full object-contain"
        />
      </div>
    );
  }

  if (compareMode === 'side') {
    return (
      <div className="space-y-3">
        <div className="flex gap-2">
          <button
            onClick={() => setCompareMode('side')}
            className="px-3 py-1.5 rounded-lg text-sm bg-primary-500/20 text-primary-400"
          >
            并排对比
          </button>
          <button
            onClick={() => setCompareMode('slider')}
            className="px-3 py-1.5 rounded-lg text-sm bg-gray-700/50 text-gray-400 hover:bg-gray-600/50"
          >
            <ArrowLeftRight className="w-4 h-4 inline mr-1" />
            滑动对比
          </button>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-gray-400 text-xs mb-2 text-center">原图</p>
            <div className="aspect-square rounded-lg overflow-hidden bg-gray-800/50">
              <img
                src={originalImage}
                alt="Original"
                className="w-full h-full object-contain"
              />
            </div>
          </div>
          <div>
            <p className="text-gray-400 text-xs mb-2 text-center">
              {resultImage ? '生成结果' : '预览'}
            </p>
            <div className="aspect-square rounded-lg overflow-hidden bg-gray-800/50">
              <img
                src={displayImage}
                alt="Result"
                className="w-full h-full object-contain"
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button
          onClick={() => setCompareMode('side')}
          className="px-3 py-1.5 rounded-lg text-sm bg-gray-700/50 text-gray-400 hover:bg-gray-600/50"
        >
          并排对比
        </button>
        <button
          onClick={() => setCompareMode('slider')}
          className="px-3 py-1.5 rounded-lg text-sm bg-primary-500/20 text-primary-400"
        >
          <ArrowLeftRight className="w-4 h-4 inline mr-1" />
          滑动对比
        </button>
      </div>
      
      <div
        ref={containerRef}
        className="relative aspect-square rounded-lg overflow-hidden cursor-ew-resize select-none"
        onMouseMove={handleSliderMove}
        onTouchMove={(e) => handleSliderMove(e.touches[0])}
      >
        <img
          src={displayImage}
          alt="Styled"
          className="absolute inset-0 w-full h-full object-contain"
        />
        
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ clipPath: `inset(0 ${100 - sliderPosition}% 0 0)` }}
        >
          <img
            src={originalImage}
            alt="Original"
            className="absolute inset-0 w-full h-full object-contain"
          />
        </div>
        
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg z-10"
          style={{ left: `${sliderPosition}%` }}
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center">
            <ArrowLeftRight className="w-4 h-4 text-gray-700" />
          </div>
        </div>
      </div>
      
      <div className="flex justify-between text-xs text-gray-500">
        <span>← 原图</span>
        <span>风格化 →</span>
      </div>
    </div>
  );
}

export default PreviewPanel;
