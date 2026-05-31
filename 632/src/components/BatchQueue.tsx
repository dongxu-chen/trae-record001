import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Layers, 
  Play, 
  Trash2, 
  Download, 
  X, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  Loader2,
  Plus,
  Sparkles,
  Wand2,
  BarChart3
} from 'lucide-react';
import JSZip from 'jszip';
import { useImageStore } from '../store/useImageStore';
import { ProgressBar } from './ProgressBar';
import { ComplexityLevel } from '../types';

export function BatchQueue() {
  const { 
    images, 
    removeImage, 
    clearImages, 
    setCurrentImage, 
    currentImageId,
    updateImage,
    outputFormat,
    outputQuality,
    imageDataToUrl,
    classifyAllImages,
    getGroupedByComplexity,
    preClassified,
    autoParamsEnabled,
    setAutoParamsEnabled
  } = useImageStore();
  
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);
  const [showGrouped, setShowGrouped] = useState(true);

  const getComplexityColor = (level?: ComplexityLevel) => {
    switch (level) {
      case 'simple': return { bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-400' };
      case 'medium': return { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400' };
      case 'complex': return { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400' };
      default: return { bg: 'bg-deep-space-700', border: 'border-deep-space-600', text: 'text-deep-space-400' };
    }
  };

  const getComplexityLabel = (level?: ComplexityLevel) => {
    switch (level) {
      case 'simple': return '简单';
      case 'medium': return '中等';
      case 'complex': return '复杂';
      default: return '未分析';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 text-neon-blue-400 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      default:
        return <Clock className="w-4 h-4 text-deep-space-500" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed': return '已完成';
      case 'processing': return '处理中';
      case 'error': return '错误';
      default: return '待处理';
    }
  };

  const handleBatchDownload = async () => {
    const completedImages = images.filter((img) => img.status === 'completed' && img.processedData);
    if (completedImages.length === 0) return;

    const zip = new JSZip();
    const ext = outputFormat === 'jpeg' ? 'jpg' : outputFormat;

    for (const img of completedImages) {
      if (img.processedData) {
        const dataUrl = imageDataToUrl(img.processedData, outputFormat, outputQuality);
        const base64Data = dataUrl.split(',')[1];
        const fileName = img.name.replace(/\.[^/.]+$/, '') + `_antialiased.${ext}`;
        zip.file(fileName, base64Data, { base64: true });
      }
    }

    const content = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(content);
    const link = document.createElement('a');
    link.href = url;
    link.download = `antialiased_images_${Date.now()}.zip`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleAddToQueue = () => {
    const currentImage = images.find((img) => img.id === currentImageId);
    if (currentImage && currentImage.status === 'completed') {
      updateImage(currentImage.id, { status: 'pending', progress: 0 });
    }
  };

  const handleClassify = () => {
    classifyAllImages();
  };

  const handleBatchProcess = () => {
    if (!preClassified) {
      classifyAllImages();
    }
    setIsBatchProcessing(true);
    const pendingImages = images.filter((img) => img.status === 'pending');
    pendingImages.forEach((img) => {
      updateImage(img.id, { status: 'processing', progress: 0 });
    });
    setTimeout(() => setIsBatchProcessing(false), 500);
  };

  const completedCount = images.filter((img) => img.status === 'completed').length;
  const pendingCount = images.filter((img) => img.status === 'pending').length;
  const processingCount = images.filter((img) => img.status === 'processing').length;

  const groups = showGrouped && preClassified ? getGroupedByComplexity() : null;

  const renderImageItem = (image: typeof images[0]) => {
    const complexityColor = getComplexityColor(image.complexity?.level);
    return (
      <motion.div
        key={image.id}
        layout
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        onClick={() => setCurrentImage(image.id)}
        className={`relative p-3 rounded-xl border-2 cursor-pointer transition-all ${
          currentImageId === image.id
            ? 'border-neon-blue-400 bg-neon-blue-500/10'
            : 'border-deep-space-700 bg-deep-space-800/50 hover:border-deep-space-600'
        }`}
      >
        <div className="flex gap-3">
          <div className="relative w-14 h-14 rounded-lg overflow-hidden bg-deep-space-700 flex-shrink-0">
            <img
              src={image.originalUrl}
              alt={image.name}
              className="w-full h-full object-cover"
            />
            <div className="absolute top-1 right-1">
              {getStatusIcon(image.status)}
            </div>
            {image.complexity && (
              <div className={`absolute bottom-1 left-1 px-1 py-0.5 rounded text-[9px] font-mono ${complexityColor.bg} ${complexityColor.text} border ${complexityColor.border}`}>
                {getComplexityLabel(image.complexity.level)}
              </div>
            )}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium text-deep-space-200 truncate">
                {image.name}
              </p>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeImage(image.id);
                }}
                className="p-1 text-deep-space-500 hover:text-red-400 transition-colors rounded"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[10px] text-deep-space-500 font-mono">
                {image.width}×{image.height}
              </span>
              {image.useAutoParams && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-neon-blue-500/20 text-neon-blue-400 font-mono">
                  自动
                </span>
              )}
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                image.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                image.status === 'processing' ? 'bg-neon-blue-500/20 text-neon-blue-400' :
                image.status === 'error' ? 'bg-red-500/20 text-red-400' :
                'bg-deep-space-700 text-deep-space-400'
              }`}>
                {getStatusText(image.status)}
              </span>
            </div>

            {image.status === 'processing' && (
              <div className="mt-2">
                <ProgressBar 
                  progress={image.progress} 
                  showLabel={false} 
                  height="h-1"
                />
              </div>
            )}

            {image.params && image.useAutoParams && (
              <div className="mt-1 flex items-center gap-1 text-[9px] text-deep-space-500 font-mono">
                <span>{image.params.algorithm.toUpperCase()}</span>
                <span>·</span>
                <span>强度{image.params.intensity}%</span>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    );
  };

  return (
    <motion.div
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="h-full flex flex-col bg-deep-space-900 border-l border-deep-space-700"
    >
      <div className="p-4 border-b border-deep-space-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-deep-space-100 font-display flex items-center gap-2">
            <Layers className="w-5 h-5 text-neon-purple-400" />
            批量队列
          </h2>
          <span className="text-xs text-deep-space-400 font-mono">
            {images.length} 张图片
          </span>
        </div>

        <div className="flex gap-2 flex-wrap mb-3">
          <button
            onClick={() => setShowGrouped(!showGrouped)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] transition-all ${
              showGrouped && preClassified
                ? 'bg-neon-blue-500/20 text-neon-blue-400 border border-neon-blue-500/30'
                : 'bg-deep-space-700 text-deep-space-400 border border-transparent hover:bg-deep-space-600'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            分组
          </button>
          <button
            onClick={handleClassify}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] transition-all ${
              preClassified
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : 'bg-deep-space-700 text-deep-space-400 border border-transparent hover:bg-deep-space-600'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            {preClassified ? '已分类' : '预分类'}
          </button>
          <button
            onClick={() => setAutoParamsEnabled(!autoParamsEnabled)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] transition-all ${
              autoParamsEnabled
                ? 'bg-neon-purple-500/20 text-neon-purple-400 border border-neon-purple-500/30'
                : 'bg-deep-space-700 text-deep-space-400 border border-transparent hover:bg-deep-space-600'
            }`}
          >
            <Wand2 className="w-3.5 h-3.5" />
            自动参数
          </button>
        </div>

        <div className="flex gap-2">
          <div className="flex-1 flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-deep-space-500" />
              <span className="text-deep-space-400">{pendingCount} 待处理</span>
            </div>
            <div className="flex items-center gap-1">
              <Loader2 className="w-3 h-3 text-neon-blue-400" />
              <span className="text-deep-space-400">{processingCount} 处理中</span>
            </div>
            <div className="flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-green-400" />
              <span className="text-deep-space-400">{completedCount} 已完成</span>
            </div>
          </div>
        </div>

        {preClassified && groups && (
          <div className="mt-3 grid grid-cols-3 gap-2">
            {(['simple', 'medium', 'complex'] as ComplexityLevel[]).map((level) => {
              const color = getComplexityColor(level);
              return (
                <div
                  key={level}
                  className={`p-2 rounded-lg text-center ${color.bg} border ${color.border}`}
                >
                  <div className={`text-lg font-bold ${color.text}`}>
                    {groups[level].length}
                  </div>
                  <div className="text-[9px] text-deep-space-400">
                    {getComplexityLabel(level)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        <AnimatePresence>
          {images.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="h-full flex flex-col items-center justify-center text-center p-8"
            >
              <div className="w-16 h-16 rounded-2xl bg-deep-space-800/50 flex items-center justify-center mb-4 border border-deep-space-700">
                <Layers className="w-8 h-8 text-deep-space-600" />
              </div>
              <p className="text-deep-space-400 text-sm">队列为空</p>
              <p className="text-deep-space-500 text-xs mt-1">上传图片后会自动添加到队列</p>
              <p className="text-deep-space-500 text-xs mt-1">并自动进行复杂度分析</p>
            </motion.div>
          ) : groups ? (
            (['simple', 'medium', 'complex'] as ComplexityLevel[]).map((level) => {
              if (groups[level].length === 0) return null;
              const color = getComplexityColor(level);
              return (
                <div key={level} className="space-y-2">
                  <div className={`flex items-center gap-2 px-2 py-1 rounded ${color.bg} border ${color.border}`}>
                    <div className={`w-2 h-2 rounded-full ${color.text.replace('text-', 'bg-')}`} />
                    <span className={`text-[11px] font-medium ${color.text}`}>
                      {getComplexityLabel(level)} ({groups[level].length})
                    </span>
                  </div>
                  {groups[level].map((image) => renderImageItem(image))}
                </div>
              );
            })
          ) : (
            images.map((image) => renderImageItem(image))
          )}
        </AnimatePresence>
      </div>

      <div className="p-4 border-t border-deep-space-700 space-y-2">
        <button
          onClick={handleAddToQueue}
          disabled={!currentImageId || images.find((img) => img.id === currentImageId)?.status !== 'completed'}
          className="w-full btn-ripple flex items-center justify-center gap-2 py-2.5 px-4 bg-deep-space-700 hover:bg-deep-space-600 disabled:bg-deep-space-800 disabled:text-deep-space-600 disabled:cursor-not-allowed text-deep-space-200 rounded-xl text-sm font-medium transition-all"
        >
          <Plus className="w-4 h-4" />
          添加当前图到队列
        </button>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={handleBatchProcess}
            disabled={pendingCount === 0 || isBatchProcessing}
            className="btn-ripple flex items-center justify-center gap-2 py-2.5 px-4 bg-neon-purple-500 hover:bg-neon-purple-400 disabled:bg-deep-space-700 disabled:text-deep-space-500 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-all"
          >
            <Play className="w-4 h-4" />
            批量处理
          </button>
          
          <button
            onClick={handleBatchDownload}
            disabled={completedCount === 0}
            className="btn-ripple flex items-center justify-center gap-2 py-2.5 px-4 bg-neon-blue-500 hover:bg-neon-blue-400 disabled:bg-deep-space-700 disabled:text-deep-space-500 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-all"
          >
            <Download className="w-4 h-4" />
            下载全部
          </button>
        </div>

        <button
          onClick={clearImages}
          disabled={images.length === 0}
          className="w-full flex items-center justify-center gap-2 py-2 px-4 text-deep-space-400 hover:text-red-400 hover:bg-red-500/10 disabled:text-deep-space-600 disabled:cursor-not-allowed rounded-xl text-sm transition-all"
        >
          <Trash2 className="w-4 h-4" />
          清空队列
        </button>
      </div>
    </motion.div>
  );
}
