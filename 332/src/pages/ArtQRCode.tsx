import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Download, Copy, Check, Wand2, RefreshCw } from 'lucide-react';
import { toast } from '@/components/ui/toast';
import { useAppStore } from '@/store';
import TypeSelector from '@/components/TypeSelector';
import FormInputs from '@/components/FormInputs';
import StylePanel from '@/components/StylePanel';
import QRCodePreview from '@/components/QRCodePreview';
import { generateContent } from '@/utils/contentGenerator';
import { downloadAsPNG, downloadAsSVG, downloadAsJPEG, copyImageToClipboard, generateFileName } from '@/utils/exportUtils';
import type { QRCodeType, QRFormData, QRStyle, ArtPattern } from '@/types';
import { artPatterns } from '@/types';

const presetStyles: Array<{
  name: string;
  pattern: ArtPattern;
  gradientStart: string;
  gradientEnd: string;
  gradientType: 'linear' | 'radial' | 'diagonal';
  eyeStyle: QRStyle['eyeStyle'];
  dotStyle: QRStyle['dotStyle'];
}> = [
  { name: '蓝海科技', pattern: 'gradient', gradientStart: '#1e40af', gradientEnd: '#06b6d4', gradientType: 'linear', eyeStyle: 'rounded', dotStyle: 'round' },
  { name: '彩虹梦境', pattern: 'rainbow', gradientStart: '#ef4444', gradientEnd: '#8b5cf6', gradientType: 'linear', eyeStyle: 'circle', dotStyle: 'dots' },
  { name: '自然绿意', pattern: 'nature', gradientStart: '#166534', gradientEnd: '#22c55e', gradientType: 'radial', eyeStyle: 'rounded', dotStyle: 'round' },
  { name: '赛博朋克', pattern: 'cyber', gradientStart: '#00ffff', gradientEnd: '#ff00ff', gradientType: 'diagonal', eyeStyle: 'square', dotStyle: 'square' },
  { name: '复古怀旧', pattern: 'vintage', gradientStart: '#92400e', gradientEnd: '#d97706', gradientType: 'linear', eyeStyle: 'rounded', dotStyle: 'round' },
  { name: '几何抽象', pattern: 'geometric', gradientStart: '#1d4ed8', gradientEnd: '#0284c7', gradientType: 'linear', eyeStyle: 'star', dotStyle: 'square' },
];

export default function ArtQRCode() {
  const { style, setStyle, resetStyle, formData, setFormData, addSavedQRCode } = useAppStore();
  const [activeTab, setActiveTab] = useState<'generate' | 'templates'>('generate');
  const [copied, setCopied] = useState(false);
  const [downloadMenu, setDownloadMenu] = useState(false);

  const content = generateContent(formData);

  const applyPreset = (preset: typeof presetStyles[0]) => {
    setStyle({
      artPattern: preset.pattern,
      gradientStart: preset.gradientStart,
      gradientEnd: preset.gradientEnd,
      gradientType: preset.gradientType,
      eyeStyle: preset.eyeStyle,
      dotStyle: preset.dotStyle,
      foregroundColor: preset.gradientStart,
    });
    toast.success(`已应用 "${preset.name}" 样式`);
  };

  const randomizeStyle = () => {
    const randomPreset = presetStyles[Math.floor(Math.random() * presetStyles.length)];
    applyPreset(randomPreset);
  };

  const handleTypeChange = (type: QRCodeType) => {
    setFormData({ ...formData, type });
  };

  const handleCopy = async () => {
    try {
      await copyImageToClipboard('qr-preview');
      setCopied(true);
      toast.success('二维码已复制到剪贴板');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error('复制失败，请重试');
    }
  };

  const handleDownload = async (format: 'png' | 'svg' | 'jpeg') => {
    const filename = generateFileName(formData.type, 'art-qrcode');
    try {
      if (format === 'png') {
        await downloadAsPNG('qr-preview', filename);
      } else if (format === 'svg') {
        await downloadAsSVG(content, style, filename);
      } else {
        await downloadAsJPEG('qr-preview', filename);
      }
      toast.success(`已下载 ${format.toUpperCase()} 格式`);
    } catch (error) {
      toast.error('下载失败');
    }
    setDownloadMenu(false);
  };

  const handleSave = () => {
    if (!content) {
      toast.error('请输入内容');
      return;
    }
    addSavedQRCode({
      name: `艺术二维码 - ${new Date().toLocaleDateString()}`,
      type: formData.type,
      content,
      style: { ...style },
    });
    toast.success('已保存到我的二维码');
  };

  return (
    <div className="min-h-screen bg-slate-950 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <div className="flex items-center justify-center gap-3 mb-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500 via-pink-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-purple-500/25">
              <Sparkles size={24} className="text-white" />
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-cyan-400 bg-clip-text text-transparent">
              AI 艺术二维码
            </h1>
          </div>
          <p className="text-slate-400">
            使用AI艺术风格生成独一无二的精美二维码
          </p>
        </motion.div>

        <div className="flex justify-center gap-2 mb-8">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setActiveTab('generate')}
            className={`px-6 py-2 rounded-xl font-medium transition-all ${
              activeTab === 'generate'
                ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white'
                : 'bg-slate-800/50 text-slate-400 hover:text-white'
            }`}
          >
            自由创作
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setActiveTab('templates')}
            className={`px-6 py-2 rounded-xl font-medium transition-all ${
              activeTab === 'templates'
                ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white'
                : 'bg-slate-800/50 text-slate-400 hover:text-white'
            }`}
          >
            模板库
          </motion.button>
        </div>

        {activeTab === 'templates' ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8"
          >
            {presetStyles.map((preset, index) => (
              <motion.div
                key={preset.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ scale: 1.05, y: -4 }}
                onClick={() => applyPreset(preset)}
                className="cursor-pointer group"
              >
                <div
                  className="aspect-square rounded-2xl mb-2 overflow-hidden border-2 border-transparent group-hover:border-purple-500/50 transition-all"
                  style={{
                    background: `linear-gradient(135deg, ${preset.gradientStart}, ${preset.gradientEnd})`,
                  }}
                >
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="w-16 h-16 bg-white/90 rounded-xl p-2">
                      <div className="w-full h-full bg-slate-900/90 rounded" style={{
                        background: `repeating-linear-gradient(45deg, ${preset.gradientStart}, ${preset.gradientStart} 4px, ${preset.gradientEnd} 4px, ${preset.gradientEnd} 8px)`
                      }} />
                    </div>
                  </div>
                </div>
                <p className="text-center text-sm font-medium text-slate-300 group-hover:text-white transition-colors">
                  {preset.name}
                </p>
              </motion.div>
            ))}
          </motion.div>
        ) : null}

        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6"
            >
              <TypeSelector value={formData.type} onChange={handleTypeChange} />
              <FormInputs formData={formData} onChange={setFormData} />
            </motion.div>

            <div className="flex gap-3">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={randomizeStyle}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-medium shadow-lg shadow-purple-500/25"
              >
                <Wand2 size={18} />
                AI 随机生成
              </motion.button>
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleSave}
                className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-slate-800 text-slate-300 font-medium hover:bg-slate-700 transition-colors"
              >
                <RefreshCw size={18} />
                保存
              </motion.button>
            </div>
          </div>

          <div className="space-y-6">
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
            >
              <QRCodePreview
                content={content}
                style={style}
                canvasId="qr-preview"
              />

              <div className="mt-4 grid grid-cols-2 gap-3">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleCopy}
                  className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-slate-800 text-slate-300 font-medium hover:bg-slate-700 transition-colors"
                >
                  {copied ? <Check size={18} className="text-green-400" /> : <Copy size={18} />}
                  {copied ? '已复制' : '复制'}
                </motion.button>

                <div className="relative">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setDownloadMenu(!downloadMenu)}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-medium"
                  >
                    <Download size={18} />
                    下载
                  </motion.button>

                  {downloadMenu && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute bottom-full left-0 right-0 mb-2 rounded-xl bg-slate-800 border border-slate-700 overflow-hidden shadow-xl"
                    >
                      <button
                        onClick={() => handleDownload('png')}
                        className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        PNG 格式
                      </button>
                      <button
                        onClick={() => handleDownload('svg')}
                        className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        SVG 格式
                      </button>
                      <button
                        onClick={() => handleDownload('jpeg')}
                        className="w-full px-4 py-2 text-left text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        JPEG 格式
                      </button>
                    </motion.div>
                  )}
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
            >
              <StylePanel style={style} onChange={setStyle} onReset={resetStyle} />
            </motion.div>
          </div>
        </div>
      </div>
    </div>
  );
}
