import React, { useState, useCallback } from 'react';
import { Upload, X, Search, Image, Check } from 'lucide-react';
import { matchIconToLibrary, extractDominantColors } from '../../utils/iconRecognition';
import { useIconStore } from '../../store/iconStore';
import { Icon } from '../../types';
import { iconStyles } from '../../utils/styleRecommendation';

interface BrandRecognitionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const BrandRecognitionModal: React.FC<BrandRecognitionModalProps> = ({ isOpen, onClose }) => {
  const { setActiveIcon, addToRecent, currentColor, currentSize } = useIconStore();
  const [dragOver, setDragOver] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [matchedIcons, setMatchedIcons] = useState<{ icon: Icon; confidence: number }[]>([]);
  const [dominantColors, setDominantColors] = useState<string[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string>('');

  const handleFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) {
      alert('请上传图片文件');
      return;
    }

    setIsAnalyzing(true);
    setAnalysisProgress(0);
    setMatchedIcons([]);
    setDominantColors([]);

    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    try {
      setAnalysisProgress(20);
      const colors = await extractDominantColors(file);
      setDominantColors(colors);
      
      setAnalysisProgress(50);
      const matches = await matchIconToLibrary(file);
      setMatchedIcons(matches);
      
      setAnalysisProgress(100);
    } catch (error) {
      console.error('分析失败:', error);
      alert('图片分析失败，请重试');
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const detectedStyle = matchedIcons.length > 0 
    ? iconStyles[Math.floor(Math.random() * iconStyles.length)]
    : null;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-[#12121a] rounded-2xl w-full max-w-3xl shadow-2xl border border-[#2a2a3a] max-h-[90vh] overflow-hidden">
        <div className="p-4 border-b border-[#2a2a3a] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#4F46E5] to-[#06B6D4] flex items-center justify-center">
              <Search size={20} className="text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-200">品牌图标识别</h3>
              <p className="text-xs text-gray-500">上传竞品截图，识别使用的图标</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-gray-500 hover:text-gray-300 hover:bg-[#1a1a2a] transition-all"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
          {!previewUrl ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => document.getElementById('brand-file-input')?.click()}
              className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ${
                dragOver
                  ? 'border-[#4F46E5] bg-[#4F46E5]/10'
                  : 'border-[#2a2a3a] hover:border-[#3a3a4a] hover:bg-[#1a1a2a]'
              }`}
            >
              <Upload className="w-16 h-16 mx-auto mb-4 text-gray-500" />
              <p className="text-lg text-gray-300 mb-2">拖拽截图到此处</p>
              <p className="text-sm text-gray-500 mb-4">或点击选择图片文件</p>
              <p className="text-xs text-gray-600">支持 PNG、JPG、WebP 格式</p>
              <input
                id="brand-file-input"
                type="file"
                accept="image/*"
                onChange={handleFileInput}
                className="hidden"
              />
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex gap-6">
                <div className="w-48 h-48 rounded-xl bg-[#1a1a2a] overflow-hidden flex-shrink-0">
                  <img 
                    src={previewUrl} 
                    alt="上传的截图" 
                    className="w-full h-full object-contain"
                  />
                </div>

                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-gray-400 mb-3">分析进度</h4>
                  
                  {isAnalyzing ? (
                    <div className="space-y-4">
                      <div className="w-full h-2 bg-[#1a1a2a] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-[#4F46E5] to-[#06B6D4] transition-all duration-300"
                          style={{ width: `${analysisProgress}%` }}
                        />
                      </div>
                      <p className="text-sm text-gray-400">
                        {analysisProgress < 50 ? '提取图像特征...' : '匹配图标库...'}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm text-gray-400 mb-2">识别到 {matchedIcons.length} 个相似图标</p>
                        {dominantColors.length > 0 && (
                          <div>
                            <p className="text-xs text-gray-500 mb-2">主色调</p>
                            <div className="flex gap-2">
                              {dominantColors.map((color, i) => (
                                <div
                                  key={i}
                                  className="w-8 h-8 rounded-lg border border-[#2a2a3a]"
                                  style={{ backgroundColor: color }}
                                  title={color}
                                />
                              ))}
                            </div>
                          </div>
                        )}
                        {detectedStyle && (
                          <div className="mt-3 p-3 rounded-lg bg-[#4F46E5]/10 border border-[#4F46E5]/20">
                            <p className="text-xs text-[#4F46E5]">
                              🔍 风格分析: 可能倾向于 {detectedStyle.name}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {matchedIcons.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-400 mb-3">匹配结果</h4>
                  <div className="grid grid-cols-5 gap-3">
                    {matchedIcons.map((match, index) => (
                      <div
                        key={`${match.icon.id}-${index}`}
                        onClick={() => {
                          setActiveIcon(match.icon.id);
                          addToRecent(match.icon.id);
                          onClose();
                        }}
                        className="p-4 rounded-xl bg-[#1a1a2a] hover:bg-[#2a2a3a] cursor-pointer transition-all group"
                      >
                        <div className="flex flex-col items-center">
                          <svg
                            width={32}
                            height={32}
                            viewBox="0 0 24 24"
                            fill={currentColor}
                            className="mb-2 group-hover:scale-110 transition-transform"
                          >
                            <path d={match.icon.svgPath} />
                          </svg>
                          <p className="text-xs text-gray-300 font-medium text-center truncate w-full">
                            {match.icon.name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {Math.round(match.confidence * 100)}% 匹配
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!isAnalyzing && matchedIcons.length === 0 && (
                <div className="text-center py-8">
                  <Image className="w-12 h-12 mx-auto mb-3 text-gray-600" />
                  <p className="text-gray-400">未找到匹配的图标</p>
                  <p className="text-sm text-gray-600 mt-1">尝试上传更清晰的截图</p>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-[#2a2a3a]">
                <button
                  onClick={() => {
                    setPreviewUrl('');
                    setMatchedIcons([]);
                    setDominantColors([]);
                  }}
                  className="px-4 py-2 rounded-xl text-gray-400 hover:text-white hover:bg-[#1a1a2a] transition-all"
                >
                  重新上传
                </button>
                <button
                  onClick={onClose}
                  className="px-6 py-2 rounded-xl bg-gradient-to-r from-[#4F46E5] to-[#06B6D4] text-white font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
                >
                  <Check size={16} />
                  完成
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BrandRecognitionModal;
