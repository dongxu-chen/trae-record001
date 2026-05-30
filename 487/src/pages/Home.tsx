import { useState } from 'react';
import { ControlPanel } from '../components/ControlPanel';
import { IconPreview } from '../components/IconPreview';
import { BatchGenerator } from '../components/BatchGenerator';
import { AICreativePanel } from '../components/AICreativePanel';
import { AnimationPreview } from '../components/AnimationPreview';
import { DesignSystemPanel } from '../components/DesignSystemPanel';
import { useIconGenerator } from '../hooks/useIconGenerator';
import { Sparkles, Zap, Palette, Download, Wand2, Play, BookOpen } from 'lucide-react';

type TabType = 'single' | 'batch' | 'ai' | 'animation' | 'design';

const tabs: { id: TabType; label: string; icon: React.ReactNode; color: string }[] = [
  { id: 'single', label: '单个生成', icon: <Palette className="w-5 h-5" />, color: 'text-blue-600' },
  { id: 'batch', label: '批量生成', icon: <Zap className="w-5 h-5" />, color: 'text-emerald-600' },
  { id: 'ai', label: 'AI创意', icon: <Wand2 className="w-5 h-5" />, color: 'text-pink-600' },
  { id: 'animation', label: '动画效果', icon: <Play className="w-5 h-5" />, color: 'text-cyan-600' },
  { id: 'design', label: '设计系统', icon: <BookOpen className="w-5 h-5" />, color: 'text-indigo-600' },
];

export function Home() {
  const [activeTab, setActiveTab] = useState<TabType>('single');
  const {
    config,
    setStyle,
    setText,
    setSize,
    setPrimaryColor,
    setSecondaryColor,
    updateConfig,
    downloadPng,
    downloadSvg,
  } = useIconGenerator();

  const renderContent = () => {
    switch (activeTab) {
      case 'single':
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="order-2 lg:order-1">
              <ControlPanel
                config={config}
                onTextChange={setText}
                onSizeChange={setSize}
                onStyleChange={setStyle}
                onPrimaryColorChange={setPrimaryColor}
                onSecondaryColorChange={setSecondaryColor}
                onPaddingChange={(padding) => updateConfig({ padding })}
                onBorderRadiusChange={(borderRadius) => updateConfig({ borderRadius })}
                onShowBackgroundChange={(showBackground) => updateConfig({ showBackground })}
              />
            </div>

            <div className="order-1 lg:order-2 space-y-6">
              <IconPreview
                config={config}
                onDownloadPng={downloadPng}
                onDownloadSvg={downloadSvg}
              />

              <div className="grid grid-cols-3 gap-4">
                <div className="bg-white rounded-xl p-4 text-center shadow-md">
                  <div className="text-3xl font-bold text-blue-600">4+</div>
                  <div className="text-sm text-gray-500">图标风格</div>
                </div>
                <div className="bg-white rounded-xl p-4 text-center shadow-md">
                  <div className="text-3xl font-bold text-purple-600">PNG/SVG</div>
                  <div className="text-sm text-gray-500">导出格式</div>
                </div>
                <div className="bg-white rounded-xl p-4 text-center shadow-md">
                  <div className="text-3xl font-bold text-pink-600">512px</div>
                  <div className="text-sm text-gray-500">最大尺寸</div>
                </div>
              </div>
            </div>
          </div>
        );

      case 'batch':
        return (
          <div className="max-w-2xl mx-auto">
            <BatchGenerator baseConfig={config} />
          </div>
        );

      case 'ai':
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="order-2 lg:order-1">
              <AICreativePanel
                currentConfig={config}
                onApplySuggestion={(newConfig) => updateConfig(newConfig)}
              />
            </div>
            <div className="order-1 lg:order-2 space-y-6">
              <IconPreview
                config={config}
                onDownloadPng={downloadPng}
                onDownloadSvg={downloadSvg}
              />
              <div className="bg-gradient-to-r from-pink-50 to-orange-50 rounded-xl p-6 border border-pink-100">
                <h4 className="font-semibold text-pink-800 mb-2 flex items-center gap-2">
                  <Wand2 className="w-5 h-5" />
                  AI创意生成
                </h4>
                <p className="text-sm text-pink-700">
                  输入关键词（如"科技公司"、"环保品牌"、"游戏App"），AI将为您推荐匹配的图标设计方案，包括风格、配色和适用场景。
                </p>
              </div>
            </div>
          </div>
        );

      case 'animation':
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="order-2 lg:order-1">
              <AnimationPreview config={config} />
            </div>
            <div className="order-1 lg:order-2 space-y-6">
              <div className="bg-white rounded-2xl shadow-xl p-6">
                <h4 className="font-semibold text-gray-800 mb-4">支持的动画效果</h4>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { name: '呼吸', desc: '平缓缩放' },
                    { name: '脉冲', desc: '节奏脉动' },
                    { name: '弹跳', desc: '活泼弹跳' },
                    { name: '旋转', desc: '优雅旋转' },
                    { name: '抖动', desc: '快速抖动' },
                    { name: '摇摆', desc: '左右摇摆' },
                    { name: '淡入', desc: '渐隐渐现' },
                    { name: '缩放', desc: '缩放弹入' },
                    { name: '波动', desc: '波浪起伏' },
                    { name: '闪光', desc: '闪光掠过' },
                  ].map((anim) => (
                    <div
                      key={anim.name}
                      className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-500 rounded-lg flex items-center justify-center">
                        <Play className="w-4 h-4 text-white" />
                      </div>
                      <div>
                        <div className="font-medium text-sm text-gray-800">{anim.name}</div>
                        <div className="text-xs text-gray-500">{anim.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="bg-gradient-to-r from-cyan-50 to-blue-50 rounded-xl p-6 border border-cyan-100">
                <h4 className="font-semibold text-cyan-800 mb-2 flex items-center gap-2">
                  <Download className="w-5 h-5" />
                  Lottie动画导出
                </h4>
                <p className="text-sm text-cyan-700">
                  导出为Lottie JSON格式，可在Web、iOS、Android端原生渲染，保持矢量清晰度和流畅动画效果。
                </p>
              </div>
            </div>
          </div>
        );

      case 'design':
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="order-2 lg:order-1">
              <DesignSystemPanel config={config} />
            </div>
            <div className="order-1 lg:order-2 space-y-6">
              <IconPreview
                config={config}
                onDownloadPng={downloadPng}
                onDownloadSvg={downloadSvg}
              />
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: '尺寸规范', icon: '📏', count: '4项' },
                  { label: '颜色规范', icon: '🎨', count: '4色' },
                  { label: '间距规范', icon: '📐', count: '3项' },
                  { label: '使用场景', icon: '💼', count: '6种' },
                  { label: '背景适配', icon: '🖼️', count: '4种' },
                  { label: '使用禁忌', icon: '🚫', count: '5项' },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="bg-white rounded-xl p-4 text-center shadow-md hover:shadow-lg transition-shadow"
                  >
                    <div className="text-2xl mb-1">{item.icon}</div>
                    <div className="text-lg font-bold text-indigo-600">{item.count}</div>
                    <div className="text-xs text-gray-500">{item.label}</div>
                  </div>
                ))}
              </div>
              <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl p-6 border border-indigo-100">
                <h4 className="font-semibold text-indigo-800 mb-2 flex items-center gap-2">
                  <BookOpen className="w-5 h-5" />
                  设计规范文档
                </h4>
                <p className="text-sm text-indigo-700">
                  自动生成完整的图标设计规范文档，包含尺寸、颜色、间距、使用场景等9个章节，支持Markdown和HTML格式导出。
                </p>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      <header className="relative z-10 py-8 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/80 backdrop-blur-sm rounded-full shadow-lg mb-6">
            <Sparkles className="w-5 h-5 text-blue-500" />
            <span className="text-sm font-medium text-gray-700">AI 驱动的图标生成器</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent mb-4">
            图标生成器
          </h1>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            输入文字，一键生成多种风格的精美图标。支持AI创意推荐、动画效果生成、Lottie导出和设计系统规范文档。
          </p>
        </div>
      </header>

      <div className="relative z-10 max-w-7xl mx-auto px-4 pb-12">
        <div className="flex flex-wrap justify-center gap-2 md:gap-4 mb-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 md:px-6 py-3 rounded-xl font-medium transition-all duration-200 ${
                activeTab === tab.id
                  ? `bg-white shadow-lg ${tab.color}`
                  : 'bg-white/50 text-gray-600 hover:bg-white/80'
              }`}
            >
              <span className={activeTab === tab.id ? tab.color : ''}>
                {tab.icon}
              </span>
              <span className="hidden md:inline">{tab.label}</span>
              <span className="md:hidden text-sm">{tab.label.slice(0, 2)}</span>
            </button>
          ))}
        </div>

        {renderContent()}
      </div>

      <footer className="relative z-10 py-8 border-t border-white/20">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-gray-500 text-sm">
            使用 React + Canvas + SVG + WebGL 技术构建 · 支持AI创意、批量生成、动画效果、Lottie导出、设计系统
          </p>
        </div>
      </footer>
    </div>
  );
}
