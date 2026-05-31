import { useState, useEffect, useRef, useCallback } from 'react';
import { Sparkles, Download, RefreshCw, Info, Zap, Palette, Layers, Package } from 'lucide-react';
import ImageUpload from './components/ImageUpload';
import StyleSelector from './components/StyleSelector';
import ModelSelector from './components/ModelSelector';
import IntensitySlider from './components/IntensitySlider';
import PreviewPanel from './components/PreviewPanel';
import TransferButton from './components/TransferButton';
import FeedbackRating from './components/FeedbackRating';
import StyleBlender from './components/StyleBlender';
import BatchPanel from './components/BatchPanel';
import api from './services/api';

function App() {
  const [activeTab, setActiveTab] = useState('single');
  const [contentImage, setContentImage] = useState(null);
  const [contentId, setContentId] = useState(null);
  const [selectedStyle, setSelectedStyle] = useState(null);
  const [customStyleImage, setCustomStyleImage] = useState(null);
  const [selectedModel, setSelectedModel] = useState('sd_turbo');
  const [intensity, setIntensity] = useState(0.55);
  const [resultImage, setResultImage] = useState(null);
  const [previewImage, setPreviewImage] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [styles, setStyles] = useState([]);
  const [error, setError] = useState(null);
  const [inferenceTime, setInferenceTime] = useState(null);
  const [feedbackCount, setFeedbackCount] = useState(0);

  const previewAbortRef = useRef(null);
  const debounceTimerRef = useRef(null);

  useEffect(() => {
    fetchStyles();
  }, []);

  const fetchStyles = async () => {
    try {
      const response = await api.getStyles();
      setStyles(response.data.styles);
      if (response.data.styles.length > 0) {
        setSelectedStyle(response.data.styles[0]);
      }
    } catch (err) {
      console.error('Failed to fetch styles:', err);
      setError('加载风格列表失败');
    }
  };

  const handleContentUpload = async (file) => {
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.uploadImage(formData);
      setContentImage(URL.createObjectURL(file));
      setContentId(response.data.id);
      setResultImage(null);
      setPreviewImage(null);
      setInferenceTime(null);
    } catch (err) {
      console.error('Upload failed:', err);
      setError('图片上传失败，请重试');
    }
  };

  const handleStyleUpload = async (file) => {
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.uploadImage(formData);
      setCustomStyleImage({
        url: URL.createObjectURL(file),
        id: response.data.id
      });
      setSelectedStyle(null);
      setResultImage(null);
    } catch (err) {
      console.error('Style upload failed:', err);
      setError('风格图片上传失败');
    }
  };

  const handleTransfer = async () => {
    if (!contentId || (!selectedStyle && !customStyleImage)) {
      setError('请先上传内容图片并选择风格');
      return;
    }

    setError(null);
    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append('content_id', contentId);
      formData.append('style_id', selectedStyle ? selectedStyle.id : customStyleImage.id);
      formData.append('intensity', intensity);
      formData.append('model_type', selectedModel);

      const response = await api.transferStyle(formData);
      setResultImage(`http://localhost:8000${response.data.output_url}`);
      setInferenceTime(response.data.inference_time_ms);
    } catch (err) {
      console.error('Style transfer failed:', err);
      setError('风格迁移失败，请重试');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRated = (rating) => {
    setFeedbackCount(prev => prev + 1);
  };

  const cancelPreview = useCallback(() => {
    if (previewAbortRef.current) {
      previewAbortRef.current.abort();
      previewAbortRef.current = null;
    }
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      debounceTimerRef.current = null;
    }
  }, []);

  const handlePreview = useCallback(async () => {
    if (!contentId || !selectedStyle) return;

    cancelPreview();

    setIsPreviewing(true);
    
    const abortController = new AbortController();
    previewAbortRef.current = abortController;

    try {
      const formData = new FormData();
      formData.append('content_id', contentId);
      formData.append('style_id', selectedStyle.id);
      formData.append('intensity', intensity);
      formData.append('model_type', selectedModel);

      const response = await api.getPreview(formData, abortController.signal);
      
      if (!abortController.signal.aborted) {
        setPreviewImage(`http://localhost:8000${response.data.preview_url}`);
      }
    } catch (err) {
      if (err.name !== 'CanceledError' && err.code !== 'ERR_CANCELED') {
        console.error('Preview failed:', err);
      }
    } finally {
      if (!abortController.signal.aborted) {
        setIsPreviewing(false);
      }
      previewAbortRef.current = null;
    }
  }, [contentId, selectedStyle, intensity, selectedModel, cancelPreview]);

  const handleReset = () => {
    cancelPreview();
    setContentImage(null);
    setContentId(null);
    setSelectedStyle(styles[0] || null);
    setCustomStyleImage(null);
    setIntensity(0.55);
    setResultImage(null);
    setPreviewImage(null);
    setError(null);
    setInferenceTime(null);
  };

  const handleDownload = () => {
    if (resultImage) {
      const link = document.createElement('a');
      link.href = resultImage;
      link.download = `style-transfer-${Date.now()}.jpg`;
      link.click();
    }
  };

  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (contentId && selectedStyle && !resultImage) {
      debounceTimerRef.current = setTimeout(() => {
        handlePreview();
      }, 200);
    }

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [selectedStyle?.id, intensity, contentId, resultImage, handlePreview]);

  useEffect(() => {
    return () => {
      cancelPreview();
    };
  }, [cancelPreview]);

  const tabs = [
    { id: 'single', name: '单风格', icon: Palette, desc: '单图单风格快速生成' },
    { id: 'blend', name: '风格融合', icon: Layers, desc: '多风格加权混合创作' },
    { id: 'batch', name: '批量生成', icon: Package, desc: '多图多风格批量处理' }
  ];

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <header className="text-center mb-10">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Sparkles className="w-10 h-10 text-primary-400" />
            <h1 className="text-4xl font-bold gradient-text">AI 风格迁移</h1>
            <div className="flex items-center gap-1 px-3 py-1 bg-accent-500/20 rounded-full text-accent-400 text-sm font-medium">
              <Zap className="w-4 h-4" />
              SD Turbo
            </div>
          </div>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            上传您的图片，选择艺术风格，让 AI 为您创作独特的艺术作品
          </p>
        </header>

        <div className="flex justify-center mb-8">
          <div className="inline-flex bg-gray-800/50 rounded-xl p-1 backdrop-blur-sm border border-gray-700/50">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id);
                    setError(null);
                  }}
                  className={`relative px-6 py-3 rounded-lg font-medium transition-all duration-200 flex items-center gap-2
                    ${activeTab === tab.id
                      ? 'bg-gradient-to-r from-primary-500 to-accent-500 text-white shadow-lg'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                    }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.name}
                  {feedbackCount > 0 && tab.id === 'blend' && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-pink-500 text-white text-[10px] rounded-full flex items-center justify-center">
                      {feedbackCount}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-center">
            {error}
          </div>
        )}

        {activeTab === 'single' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-4 space-y-6">
              <div className="gradient-border p-6">
                <h2 className="text-xl font-semibold text-white mb-4">上传内容图片</h2>
                <ImageUpload
                  onImageUpload={handleContentUpload}
                  currentImage={contentImage}
                  type="content"
                />
              </div>

              <div className="gradient-border p-6">
                <h2 className="text-xl font-semibold text-white mb-4">选择模型</h2>
                <ModelSelector
                  selectedModel={selectedModel}
                  onModelChange={(model) => {
                    setSelectedModel(model);
                    if (resultImage) setResultImage(null);
                  }}
                />
              </div>

              <div className="gradient-border p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white">风格强度</h2>
                  <span className="text-primary-400 font-mono">{Math.round(intensity * 100)}%</span>
                </div>
                <IntensitySlider
                  intensity={intensity}
                  onIntensityChange={(value) => {
                    setIntensity(value);
                    if (resultImage) setResultImage(null);
                  }}
                />
                <p className="text-gray-500 text-sm mt-3 flex items-center gap-1">
                  <Info className="w-4 h-4" />
                  调节滑块控制风格化程度（感知线性映射）
                </p>
              </div>
            </div>

            <div className="lg:col-span-4 space-y-6">
              <div className="gradient-border p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white">选择艺术风格</h2>
                </div>
                <StyleSelector
                  styles={styles}
                  selectedStyle={selectedStyle}
                  onStyleSelect={(style) => {
                    setSelectedStyle(style);
                    setCustomStyleImage(null);
                    setResultImage(null);
                  }}
                  customStyleImage={customStyleImage}
                  onCustomStyleUpload={handleStyleUpload}
                />
              </div>

              <div className="flex gap-4">
                <TransferButton
                  onClick={handleTransfer}
                  disabled={!contentId || (!selectedStyle && !customStyleImage) || isProcessing}
                  isProcessing={isProcessing}
                />
                <button
                  onClick={handleReset}
                  className="flex-1 px-6 py-3 glass-effect rounded-xl text-gray-300 hover:bg-white/10 transition-colors flex items-center justify-center gap-2"
                >
                  <RefreshCw className="w-5 h-5" />
                  重置
                </button>
              </div>
            </div>

            <div className="lg:col-span-4 space-y-6">
              <div className="gradient-border p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-white">结果预览</h2>
                  <div className="flex items-center gap-3">
                    {inferenceTime && (
                      <span className="text-xs text-green-400 bg-green-400/10 px-2 py-1 rounded">
                        {inferenceTime}ms
                      </span>
                    )}
                    {resultImage && (
                      <button
                        onClick={handleDownload}
                        className="flex items-center gap-2 px-4 py-2 bg-primary-500/20 text-primary-400 rounded-lg hover:bg-primary-500/30 transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        下载
                      </button>
                    )}
                  </div>
                </div>
                <PreviewPanel
                  originalImage={contentImage}
                  resultImage={resultImage}
                  previewImage={previewImage}
                  isProcessing={isProcessing}
                  isPreviewing={isPreviewing}
                />
                
                {resultImage && selectedStyle && (
                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <p className="text-xs text-gray-400 mb-2 text-center">对生成结果进行评价，帮助AI学习您的偏好</p>
                    <FeedbackRating
                      contentId={contentId}
                      styleId={selectedStyle.id}
                      onRated={handleRated}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'blend' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-5 space-y-6">
              <div className="gradient-border p-6">
                <h2 className="text-xl font-semibold text-white mb-4">上传内容图片</h2>
                <ImageUpload
                  onImageUpload={handleContentUpload}
                  currentImage={contentImage}
                  type="content"
                />
                {contentImage && (
                  <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                    <p className="text-xs text-blue-400">
                      <span className="font-medium">💡 提示：</span>
                      在右侧选择多个风格并调整权重，创造独特的混合风格效果
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="lg:col-span-7">
              <StyleBlender
                contentId={contentId}
                feedbackCount={feedbackCount}
              />
            </div>
          </div>
        )}

        {activeTab === 'batch' && (
          <div className="max-w-4xl mx-auto">
            <BatchPanel />
          </div>
        )}

        <footer className="mt-12 text-center text-gray-500 text-sm">
          <p>SD Turbo 超高速推理 · 感知线性强度映射 · 请求自动取消 · 用户反馈学习 · 风格加权融合 · 批量生成</p>
          <p className="mt-1">© 2024 AI Style Transfer. All rights reserved.</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
