import { useCallback, useEffect, useState } from 'react';
import { Eye, RotateCcw, SplitSquareHorizontal, ZoomIn } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { useImageProcessor } from '@/hooks/useImageProcessor';
import { useColorblindSimulation } from '@/hooks/useColorblindSimulation';
import { useContrastChecker } from '@/hooks/useContrastChecker';
import { COLORBLIND_TYPES } from '@/types';
import type { ColorblindType } from '@/types';
import ImageUploader from '@/components/ImageUploader';
import ColorblindPreview from '@/components/ColorblindPreview';
import CompareSlider from '@/components/CompareSlider';
import ColorPicker from '@/components/ColorPicker';
import ContrastPanel from '@/components/ContrastPanel';
import ColorblindSvgFilters from '@/components/ColorblindSvgFilters';
import { cn } from '@/lib/utils';

const SAMPLE_IMAGES = [
  {
    label: '交通信号灯',
    url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=traffic%20light%20with%20red%20yellow%20green%20signals%20on%20urban%20street%20clear%20view&image_size=landscape_16_9',
  },
  {
    label: '数据图表',
    url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=colorful%20pie%20chart%20and%20bar%20chart%20dashboard%20with%20red%20green%20blue%20colors%20on%20white%20background&image_size=landscape_16_9',
  },
  {
    label: '网页界面',
    url: 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=modern%20web%20application%20interface%20with%20colored%20buttons%20forms%20and%20text%20on%20various%20backgrounds&image_size=landscape_16_9',
  },
];

export default function Workspace() {
  const {
    originalImage,
    selectedType,
    showCompare,
    isAnalyzing,
    contrastIssues,
    setSelectedType,
    setShowCompare,
    reset,
  } = useAppStore();
  const { loadImage, loadImageFromUrl } = useImageProcessor();
  useColorblindSimulation();
  const { pickedColor, checkPair } = useContrastChecker();

  const [activeCategory, setActiveCategory] = useState<'red-green' | 'blue-yellow' | 'total'>('red-green');
  const [selectedIssueIdx, setSelectedIssueIdx] = useState(0);

  const handleCopy = useCallback((text: string) => {
    navigator.clipboard.writeText(text).catch(() => {});
  }, []);

  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile();
          if (file) loadImage(file);
          break;
        }
      }
    };
    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [loadImage]);

  const categories = [
    { key: 'red-green' as const, label: '红绿色盲', count: 4 },
    { key: 'blue-yellow' as const, label: '蓝黄色盲', count: 2 },
    { key: 'total' as const, label: '全色盲', count: 2 },
  ];

  const filteredTypes = COLORBLIND_TYPES.filter((t) => t.category === activeCategory);

  const currentIssue = contrastIssues[selectedIssueIdx];

  return (
    <div className="space-y-6">
      <ColorblindSvgFilters />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100">检测工作台</h1>
          <p className="text-sm text-zinc-500 mt-1">上传页面截图，模拟色盲视图，检测对比度问题</p>
        </div>
        {originalImage && (
          <button
            onClick={reset}
            className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 border border-zinc-700 hover:border-zinc-600 transition-colors flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            重新开始
          </button>
        )}
      </div>

      <ImageUploader onImageLoad={loadFile} hasImage={!!originalImage} />

      {!originalImage && (
        <div className="space-y-3">
          <p className="text-sm text-zinc-500">或选择示例图片：</p>
          <div className="flex gap-3">
            {SAMPLE_IMAGES.map((img) => (
              <button
                key={img.label}
                onClick={() => loadImageFromUrl(img.url)}
                className="px-4 py-3 rounded-xl border border-zinc-700 hover:border-[#00d4aa] text-sm text-zinc-300 hover:text-[#00d4aa] transition-colors flex items-center gap-2"
              >
                <Eye className="w-4 h-4" />
                {img.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {originalImage && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex gap-1">
                {categories.map((cat) => (
                  <button
                    key={cat.key}
                    onClick={() => setActiveCategory(cat.key)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                      activeCategory === cat.key
                        ? 'bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/20'
                        : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                    )}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
              <div className="flex gap-1 ml-auto">
                {filteredTypes.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => setSelectedType(type.id as ColorblindType)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                      selectedType === type.id
                        ? 'bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/20'
                        : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
                    )}
                    title={type.description}
                  >
                    {type.labelZh}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3 text-xs text-zinc-500">
              <button
                onClick={() => setShowCompare(!showCompare)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors',
                  showCompare
                    ? 'bg-[#00d4aa]/10 text-[#00d4aa]'
                    : 'text-zinc-500 hover:text-zinc-300'
                )}
              >
                <SplitSquareHorizontal className="w-3.5 h-3.5" />
                对比模式
              </button>
              <span className="flex items-center gap-1.5">
                <ZoomIn className="w-3.5 h-3.5" />
                点击图像拾取颜色
              </span>
              {isAnalyzing && (
                <span className="text-[#00d4aa] animate-pulse">分析中...</span>
              )}
            </div>

            <div className="aspect-video bg-zinc-900 rounded-xl overflow-hidden border border-zinc-800">
              <ColorblindPreview />
            </div>

            {showCompare && (
              <CompareSlider />
            )}
          </div>

          <div className="space-y-4">
            <ColorPicker />

            {pickedColor && currentIssue && (
              <ContrastPanel
                foreground={currentIssue.foreground}
                background={currentIssue.background}
                ratio={currentIssue.contrastRatio}
              />
            )}

            {pickedColor && !currentIssue && (
              <ContrastPanel
                foreground={pickedColor}
                background={{ r: 255, g: 255, b: 255 }}
                ratio={checkPair(pickedColor, { r: 255, g: 255, b: 255 }).ratio}
              />
            )}

            {contrastIssues.length > 0 && (
              <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-zinc-300">检测到的问题</span>
                  <span className="text-xs text-[#ff6b35] font-mono">
                    {contrastIssues.length} 个
                  </span>
                </div>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {contrastIssues.slice(0, 10).map((issue, idx) => (
                    <button
                      key={issue.id}
                      onClick={() => setSelectedIssueIdx(idx)}
                      className={cn(
                        'w-full text-left px-3 py-2 rounded-lg text-xs transition-colors',
                        selectedIssueIdx === idx
                          ? 'bg-[#ff6b35]/10 border border-[#ff6b35]/20'
                          : 'hover:bg-zinc-800'
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <div
                          className="w-4 h-4 rounded border border-zinc-700"
                          style={{ backgroundColor: `rgb(${issue.foreground.r},${issue.foreground.g},${issue.foreground.b})` }}
                        />
                        <span className="text-zinc-400">/</span>
                        <div
                          className="w-4 h-4 rounded border border-zinc-700"
                          style={{ backgroundColor: `rgb(${issue.background.r},${issue.background.g},${issue.background.b})` }}
                        />
                        <span className="font-mono text-zinc-300">
                          {issue.contrastRatio.toFixed(2)}:1
                        </span>
                        <span
                          className={cn(
                            'ml-auto px-1.5 py-0.5 rounded text-xs',
                            issue.severity === 'critical'
                              ? 'bg-red-500/10 text-red-500'
                              : issue.severity === 'major'
                              ? 'bg-[#ff6b35]/10 text-[#ff6b35]'
                              : 'bg-yellow-500/10 text-yellow-500'
                          )}
                        >
                          {issue.severity === 'critical' ? '严重' : issue.severity === 'major' ? '重要' : '轻微'}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {contrastIssues.length === 0 && originalImage && !isAnalyzing && (
              <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-6 text-center">
                <div className="text-3xl mb-2">✅</div>
                <p className="text-sm text-[#00d4aa] font-medium">未检测到对比度问题</p>
                <p className="text-xs text-zinc-500 mt-1">当前图像色彩对比度符合WCAG标准</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );

  function loadFile(file: File) {
    loadImage(file);
  }
}
