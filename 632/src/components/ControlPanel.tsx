import { motion } from 'framer-motion';
import { 
  RotateCcw, Download, Settings2, ChevronDown, ChevronUp, Wand2, Cpu, Zap, 
  Compass, Sparkles, Type, Film, Sun, Moon, Droplets, Target
} from 'lucide-react';
import { useState } from 'react';
import { Slider } from './Slider';
import { AlgorithmSelector } from './AlgorithmSelector';
import { useImageStore } from '../store/useImageStore';
import { ProgressBar } from './ProgressBar';
import { isWebGLAvailable } from '../algorithms/gpuResample';

export function ControlPanel() {
  const { 
    params, 
    setParams, 
    resetParams, 
    currentImageId, 
    images,
    outputFormat,
    outputQuality,
    setOutputFormat,
    setOutputQuality,
    imageDataToUrl,
    autoParamsEnabled,
    setAutoParamsEnabled,
    applyRecommendedParams
  } = useImageStore();
  
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showContent, setShowContent] = useState(false);
  const gpuAvailable = isWebGLAvailable();
  
  const currentImage = images.find((img) => img.id === currentImageId);
  const isProcessing = currentImage?.status === 'processing';

  const handleDownload = () => {
    if (!currentImage?.processedData) return;
    
    const url = imageDataToUrl(currentImage.processedData, outputFormat, outputQuality);
    const link = document.createElement('a');
    const ext = outputFormat === 'jpeg' ? 'jpg' : outputFormat;
    link.download = currentImage.name.replace(/\.[^/.]+$/, '') + `_antialiased.${ext}`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  };

  const formatOptions: Array<{ value: 'png' | 'jpeg' | 'webp'; label: string }> = [
    { value: 'png', label: 'PNG' },
    { value: 'jpeg', label: 'JPEG' },
    { value: 'webp', label: 'WebP' }
  ];

  const contentTypeOptions: Array<{ value: 'photo' | 'text' | 'illustration' | 'video'; label: string; icon: any }> = [
    { value: 'photo', label: '照片', icon: Sun },
    { value: 'text', label: '文字', icon: Type },
    { value: 'illustration', label: '插画', icon: Droplets },
    { value: 'video', label: '动画', icon: Film }
  ];

  const subpixelOptions: Array<{ value: 'rgb' | 'bgr' | 'none'; label: string }> = [
    { value: 'rgb', label: 'RGB' },
    { value: 'bgr', label: 'BGR' },
    { value: 'none', label: '关闭' }
  ];

  const getComplexityColor = (level?: string) => {
    switch (level) {
      case 'simple': return { bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-400' };
      case 'medium': return { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400' };
      case 'complex': return { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400' };
      default: return { bg: 'bg-deep-space-700', border: 'border-deep-space-600', text: 'text-deep-space-400' };
    }
  };

  return (
    <motion.div
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="h-full overflow-y-auto p-4 space-y-5"
    >
      <div className="space-y-2">
        <h2 className="text-xl font-bold text-deep-space-100 font-display flex items-center gap-2">
          <Settings2 className="w-5 h-5 text-neon-blue-400" />
          处理参数
        </h2>
        <p className="text-xs text-deep-space-400">
          调整参数以获得最佳抗锯齿效果
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className={`p-3 rounded-lg border ${gpuAvailable ? 'bg-green-500/10 border-green-500/30' : 'bg-deep-space-700 border-deep-space-600'}`}>
          <div className={`flex items-center gap-1.5 ${gpuAvailable ? 'text-green-400' : 'text-deep-space-500'}`}>
            <Zap className="w-4 h-4" />
            <span className="text-[10px] font-medium">GPU加速</span>
          </div>
          <div className={`text-[10px] mt-1 ${gpuAvailable ? 'text-green-400/70' : 'text-deep-space-500'}`}>
            {gpuAvailable ? '已启用 (WebGL)' : '未检测到'}
          </div>
        </div>
        <div className="p-3 rounded-lg border bg-neon-blue-500/10 border-neon-blue-500/30">
          <div className="flex items-center gap-1.5 text-neon-blue-400">
            <Compass className="w-4 h-4" />
            <span className="text-[10px] font-medium">方向检测</span>
          </div>
          <div className="text-[10px] mt-1 text-neon-blue-400/70">
            各向异性Sobel
          </div>
        </div>
      </div>

      <div className={`p-3 rounded-lg border transition-all ${autoParamsEnabled ? 'bg-neon-purple-500/10 border-neon-purple-500/30' : 'bg-deep-space-800/50 border-deep-space-700'}`}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Wand2 className={`w-4 h-4 ${autoParamsEnabled ? 'text-neon-purple-400' : 'text-deep-space-500'}`} />
            <span className={`text-sm font-medium ${autoParamsEnabled ? 'text-neon-purple-300' : 'text-deep-space-400'}`}>
              自动参数推荐
            </span>
          </div>
          <button
            onClick={() => setAutoParamsEnabled(!autoParamsEnabled)}
            className={`relative w-11 h-6 rounded-full transition-colors ${autoParamsEnabled ? 'bg-neon-purple-500' : 'bg-deep-space-700'}`}
          >
            <motion.div
              animate={{ x: autoParamsEnabled ? 20 : 2 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              className="absolute top-1 w-4 h-4 bg-white rounded-full shadow-lg"
            />
          </button>
        </div>
        {currentImage && currentImage.complexity && (
          <div className="mt-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-deep-space-400">图像复杂度</span>
              <span className={`text-[11px] font-mono px-2 py-0.5 rounded ${getComplexityColor(currentImage.complexity.level).bg} ${getComplexityColor(currentImage.complexity.level).text} border ${getComplexityColor(currentImage.complexity.level).border}`}>
                {currentImage.complexity.level === 'simple' ? '简单' :
                 currentImage.complexity.level === 'medium' ? '中等' : '复杂'}
              </span>
            </div>
            {currentImage.contentType && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-deep-space-400">内容类型</span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-neon-blue-500/20 text-neon-blue-400 border border-neon-blue-500/30">
                  {currentImage.contentType === 'photo' ? '照片' :
                   currentImage.contentType === 'text' ? '文字' :
                   currentImage.contentType === 'illustration' ? '插画' : '动画'}
                </span>
              </div>
            )}
            {currentImage.textConfidence !== undefined && currentImage.contentType === 'text' && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-deep-space-400">文字置信度</span>
                <span className="text-[11px] font-mono text-neon-green-400">
                  {Math.round(currentImage.textConfidence * 100)}%
                </span>
              </div>
            )}
            <div className="grid grid-cols-3 gap-1 text-[9px] text-deep-space-500 font-mono">
              <div className="text-center">
                <div className="text-deep-space-300">{Math.round(currentImage.complexity.edgeDensity * 100)}</div>
                <div>边缘密度</div>
              </div>
              <div className="text-center">
                <div className="text-deep-space-300">{Math.round(currentImage.complexity.colorVariance / 100)}</div>
                <div>色阶方差</div>
              </div>
              <div className="text-center">
                <div className="text-deep-space-300">{Math.round(currentImage.complexity.detailLevel * 100)}</div>
                <div>细节程度</div>
              </div>
            </div>
            {autoParamsEnabled && currentImage.params && (
              <div className="mt-2 pt-2 border-t border-deep-space-700/50">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-deep-space-400">推荐参数</span>
                  <span className="text-neon-purple-400 font-mono">
                    {currentImage.params.algorithm.toUpperCase()} · 强度{currentImage.params.intensity}% · 锐利{currentImage.params.sharpness}%
                  </span>
                </div>
              </div>
            )}
            {!autoParamsEnabled && currentImage.complexity && (
              <button
                onClick={() => currentImageId && applyRecommendedParams(currentImageId)}
                className="w-full mt-2 flex items-center justify-center gap-1.5 py-1.5 px-3 bg-neon-purple-500/20 hover:bg-neon-purple-500/30 text-neon-purple-400 rounded-lg text-[11px] font-medium transition-all"
              >
                <Sparkles className="w-3.5 h-3.5" />
                应用推荐参数
              </button>
            )}
          </div>
        )}
      </div>

      <AlgorithmSelector />

      <div className="space-y-4">
        <Slider
          label="边缘检测阈值"
          value={params.threshold}
          min={0}
          max={255}
          onChange={(v) => setParams({ threshold: v })}
          hint="EDAA/MSAA"
        />

        <Slider
          label="抗锯齿强度"
          value={params.intensity}
          min={0}
          max={100}
          onChange={(v) => setParams({ intensity: v })}
          unit="%"
        />

        <div className="relative">
          <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-0.5">
            <Moon className="w-4 h-4 text-neon-blue-400" />
          </div>
          <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-0.5">
            <Sun className="w-4 h-4 text-neon-orange-400" />
          </div>
          <Slider
            label="锐利度 / 柔滑度"
            value={params.sharpness}
            min={0}
            max={100}
            onChange={(v) => setParams({ sharpness: v })}
            unit="%"
            labelLeft="柔滑"
            labelRight="锐利"
          />
        </div>
      </div>

      <div className="border-t border-deep-space-700 pt-4">
        <button
          onClick={() => setShowContent(!showContent)}
          className="w-full flex items-center justify-between text-sm text-deep-space-300 hover:text-deep-space-100 transition-colors mb-3"
        >
          <span className="font-medium flex items-center gap-2">
            <Target className="w-4 h-4 text-neon-green-400" />
            内容优化
          </span>
          {showContent ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        {showContent && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            className="space-y-4 overflow-hidden"
          >
            <div className="space-y-2">
              <label className="text-xs text-deep-space-400">内容类型</label>
              <div className="grid grid-cols-4 gap-1.5">
                {contentTypeOptions.map((opt) => {
                  const Icon = opt.icon;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => setParams({ contentMode: opt.value })}
                      className={`flex flex-col items-center gap-1 py-2 px-1 rounded-lg text-xs font-medium transition-all ${
                        params.contentMode === opt.value
                          ? 'bg-neon-green-500/20 text-neon-green-400 border border-neon-green-500/30'
                          : 'bg-deep-space-700 text-deep-space-400 border border-transparent hover:bg-deep-space-600'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{opt.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center justify-between p-3 bg-deep-space-800/50 rounded-lg border border-deep-space-700">
              <div className="flex items-center gap-2">
                <Type className="w-4 h-4 text-neon-purple-400" />
                <span className="text-xs text-deep-space-300">文字优化</span>
              </div>
              <button
                onClick={() => setParams({ textOptimization: !params.textOptimization })}
                className={`relative w-9 h-5 rounded-full transition-colors ${params.textOptimization ? 'bg-neon-purple-500' : 'bg-deep-space-700'}`}
              >
                <motion.div
                  animate={{ x: params.textOptimization ? 18 : 2 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  className="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow"
                />
              </button>
            </div>

            {params.textOptimization && (
              <div className="space-y-2">
                <label className="text-xs text-deep-space-400">子像素渲染</label>
                <div className="grid grid-cols-3 gap-1.5">
                  {subpixelOptions.map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setParams({ subpixelLayout: opt.value })}
                      className={`py-1.5 px-2 rounded-lg text-xs font-medium transition-all ${
                        params.subpixelLayout === opt.value
                          ? 'bg-neon-purple-500/20 text-neon-purple-400 border border-neon-purple-500/30'
                          : 'bg-deep-space-700 text-deep-space-400 border border-transparent hover:bg-deep-space-600'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                <p className="text-[10px] text-deep-space-500">
                  RGB适合大多数LCD显示器，BGR适合部分旧显示器
                </p>
              </div>
            )}

            <div className="flex items-center justify-between p-3 bg-deep-space-800/50 rounded-lg border border-deep-space-700">
              <div className="flex items-center gap-2">
                <Film className="w-4 h-4 text-neon-orange-400" />
                <span className="text-xs text-deep-space-300">时间抗锯齿</span>
              </div>
              <button
                onClick={() => setParams({ temporalAA: !params.temporalAA })}
                className={`relative w-9 h-5 rounded-full transition-colors ${params.temporalAA ? 'bg-neon-orange-500' : 'bg-deep-space-700'}`}
              >
                <motion.div
                  animate={{ x: params.temporalAA ? 18 : 2 }}
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  className="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow"
                />
              </button>
            </div>

            {params.temporalAA && (
              <Slider
                label="帧间混合强度"
                value={params.frameBlend}
                min={10}
                max={80}
                onChange={(v) => setParams({ frameBlend: v })}
                unit="%"
                hint="视频帧平滑"
              />
            )}
          </motion.div>
        )}
      </div>

      <div className="border-t border-deep-space-700 pt-4">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="w-full flex items-center justify-between text-sm text-deep-space-300 hover:text-deep-space-100 transition-colors"
        >
          <span className="font-medium">高级设置</span>
          {showAdvanced ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        {showAdvanced && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-4 space-y-4 overflow-hidden"
          >
            <Slider
              label="超采样倍率"
              value={params.sampleRate}
              min={2}
              max={8}
              step={1}
              onChange={(v) => setParams({ sampleRate: v })}
              unit="x"
              hint="SSAA/MSAA · GPU加速"
            />

            <Slider
              label="卷积核大小"
              value={params.kernelSize}
              min={3}
              max={7}
              step={2}
              onChange={(v) => setParams({ kernelSize: v })}
              hint="EDAA · 方向性"
            />

            <Slider
              label="边缘模糊程度"
              value={params.edgeBlur}
              min={1}
              max={10}
              step={1}
              onChange={(v) => setParams({ edgeBlur: v })}
              hint="EDAA · 各向异性"
            />
          </motion.div>
        )}
      </div>

      <div className="border-t border-deep-space-700 pt-4 space-y-4">
        <h3 className="text-sm font-medium text-deep-space-200">输出设置</h3>
        
        <div className="space-y-2">
          <label className="text-xs text-deep-space-400">输出格式</label>
          <div className="flex gap-2">
            {formatOptions.map((fmt) => (
              <button
                key={fmt.value}
                onClick={() => setOutputFormat(fmt.value)}
                className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                  outputFormat === fmt.value
                    ? 'bg-neon-blue-500 text-white'
                    : 'bg-deep-space-700 text-deep-space-300 hover:bg-deep-space-600'
                }`}
              >
                {fmt.label}
              </button>
            ))}
          </div>
        </div>

        {outputFormat !== 'png' && (
          <Slider
            label="输出质量"
            value={Math.round(outputQuality * 100)}
            min={10}
            max={100}
            onChange={(v) => setOutputQuality(v / 100)}
            unit="%"
          />
        )}
      </div>

      {isProcessing && currentImage && (
        <div className="p-4 bg-deep-space-800/50 rounded-xl border border-deep-space-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-deep-space-300">处理中...</span>
            <span className="text-xs font-mono text-neon-blue-400">
              {currentImage.progress}%
            </span>
          </div>
          <ProgressBar progress={currentImage.progress} showLabel={false} />
        </div>
      )}

      <div className="flex gap-3 pt-2">
        <button
          onClick={resetParams}
          className="flex-1 btn-ripple flex items-center justify-center gap-2 py-3 px-4 bg-deep-space-700 hover:bg-deep-space-600 text-deep-space-200 rounded-xl font-medium transition-all"
        >
          <RotateCcw className="w-4 h-4" />
          重置
        </button>
        <button
          onClick={handleDownload}
          disabled={!currentImage?.processedData}
          className="flex-1 btn-ripple flex items-center justify-center gap-2 py-3 px-4 bg-neon-blue-500 hover:bg-neon-blue-400 disabled:bg-deep-space-700 disabled:text-deep-space-500 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-all neon-glow"
        >
          <Download className="w-4 h-4" />
          下载
        </button>
      </div>

      {currentImage && (
        <div className="p-3 bg-deep-space-800/30 rounded-lg border border-deep-space-700/50">
          <div className="text-xs text-deep-space-400 space-y-1 font-mono">
            <div className="flex justify-between">
              <span>尺寸:</span>
              <span className="text-deep-space-300">
                {currentImage.width} × {currentImage.height}
              </span>
            </div>
            <div className="flex justify-between">
              <span>状态:</span>
              <span className={`${
                currentImage.status === 'completed' ? 'text-green-400' :
                currentImage.status === 'processing' ? 'text-neon-blue-400' :
                currentImage.status === 'error' ? 'text-red-400' :
                'text-deep-space-400'
              }`}>
                {currentImage.status === 'pending' && '待处理'}
                {currentImage.status === 'processing' && '处理中'}
                {currentImage.status === 'completed' && '已完成'}
                {currentImage.status === 'error' && '错误'}
              </span>
            </div>
            <div className="flex justify-between">
              <span>算法:</span>
              <span className="text-neon-blue-400">
                {params.algorithm.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
