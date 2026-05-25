import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Download, Copy, Save, Sparkles, Check, Loader2 } from 'lucide-react';
import { toast } from '../components/ui/toast';
import TypeSelector from '@/components/TypeSelector';
import FormInputs from '@/components/FormInputs';
import StylePanel from '@/components/StylePanel';
import QRCodePreview from '@/components/QRCodePreview';
import { useAppStore } from '@/store';
import { generateContent, getTypeLabel } from '@/utils/contentGenerator';
import {
  downloadAsPNG,
  downloadAsSVG,
  downloadAsJPEG,
  copyImageToClipboard,
  generateFileName,
} from '@/utils/exportUtils';
import type { QRCodeType } from '@/types';

export default function Generator() {
  const {
    formData,
    style,
    setStyle,
    setFormData,
    resetStyle,
    saveQRCode,
    currentContent,
    setCurrentContent,
  } = useAppStore();

  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [downloadFormat, setDownloadFormat] = useState<'png' | 'svg' | 'jpeg'>('png');
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);

  useEffect(() => {
    const content = generateContent(formData);
    setCurrentContent(content);
  }, [formData, setCurrentContent]);

  const handleTypeChange = (type: QRCodeType) => {
    setFormData({ type });
  };

  const handleDownload = async () => {
    if (!currentContent) {
      toast.error('请先输入内容');
      return;
    }

    setIsGenerating(true);
    try {
      const filename = generateFileName(formData.type);
      
      switch (downloadFormat) {
        case 'png':
          await downloadAsPNG('qr-preview-canvas', filename);
          break;
        case 'svg':
          await downloadAsSVG(currentContent, style, filename);
          break;
        case 'jpeg':
          await downloadAsJPEG('qr-preview-canvas', filename);
          break;
      }
      
      toast.success(`二维码已下载 (${downloadFormat.toUpperCase()})`);
    } catch (error) {
      toast.error('下载失败，请重试');
    } finally {
      setIsGenerating(false);
      setShowDownloadMenu(false);
    }
  };

  const handleCopy = async () => {
    if (!currentContent) {
      toast.error('请先输入内容');
      return;
    }

    try {
      await copyImageToClipboard('qr-preview-canvas');
      setCopied(true);
      toast.success('已复制到剪贴板');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error('复制失败，请重试');
    }
  };

  const handleSave = () => {
    if (!currentContent) {
      toast.error('请先输入内容');
      return;
    }

    const name = prompt('请输入二维码名称：', `${getTypeLabel(formData.type)}二维码`);
    if (name === null) return;

    saveQRCode({
      name: name || '未命名二维码',
      type: formData.type,
      content: currentContent,
      style: { ...style },
    });

    toast.success('二维码已保存');
  };

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/20 via-transparent to-cyan-900/20 pointer-events-none" />
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{
        backgroundImage: `linear-gradient(rgba(59, 130, 246, 0.5) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(59, 130, 246, 0.5) 1px, transparent 1px)`,
        backgroundSize: '40px 40px',
      }} />

      <div className="relative max-w-7xl mx-auto px-4 py-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent mb-3">
            二维码生成器
          </h1>
          <p className="text-slate-400 text-lg">
            快速生成文本、网址、名片、WiFi、邮件等多种类型二维码
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-8">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="space-y-6"
          >
            <div className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6">
              <h2 className="text-lg font-semibold mb-4 text-slate-200 flex items-center gap-2">
                <Sparkles size={20} className="text-yellow-500" />
                选择二维码类型
              </h2>
              <TypeSelector value={formData.type} onChange={handleTypeChange} />
            </div>

            <div className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6">
              <h2 className="text-lg font-semibold mb-4 text-slate-200">
                输入内容
              </h2>
              <AnimatePresence mode="wait">
                <FormInputs
                  type={formData.type}
                  formData={formData}
                  onChange={setFormData}
                />
              </AnimatePresence>
            </div>

            <StylePanel style={style} onChange={setStyle} onReset={resetStyle} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-6"
          >
            <QRCodePreview content={currentContent} style={style} />

            <div className="rounded-2xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm p-6">
              <h3 className="text-sm font-medium text-slate-400 mb-4">操作</h3>
              <div className="flex flex-wrap gap-3">
                <div className="relative">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setShowDownloadMenu(!showDownloadMenu)}
                    disabled={!currentContent || isGenerating}
                    className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-medium shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isGenerating ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <Download size={18} />
                    )}
                    下载
                  </motion.button>

                  <AnimatePresence>
                    {showDownloadMenu && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="absolute top-full mt-2 right-0 z-50 w-40 rounded-xl bg-slate-800 border border-slate-700 shadow-2xl overflow-hidden"
                      >
                        {[
                          { value: 'png', label: 'PNG 格式' },
                          { value: 'svg', label: 'SVG 格式' },
                          { value: 'jpeg', label: 'JPEG 格式' },
                        ].map((format) => (
                          <button
                            key={format.value}
                            onClick={() => {
                              setDownloadFormat(format.value as typeof downloadFormat);
                              handleDownload();
                            }}
                            className={`w-full px-4 py-3 text-left text-sm hover:bg-slate-700/50 transition-colors flex items-center gap-2 ${
                              downloadFormat === format.value
                                ? 'text-blue-400 bg-slate-700/30'
                                : 'text-slate-300'
                            }`}
                          >
                            {downloadFormat === format.value && (
                              <Check size={14} />
                            )}
                            {format.label}
                          </button>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleCopy}
                  disabled={!currentContent}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium border border-slate-700 hover:border-slate-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {copied ? (
                    <>
                      <Check size={18} className="text-green-400" />
                      已复制
                    </>
                  ) : (
                    <>
                      <Copy size={18} />
                      复制
                    </>
                  )}
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleSave}
                  disabled={!currentContent}
                  className="flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium border border-slate-700 hover:border-slate-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Save size={18} />
                  保存
                </motion.button>
              </div>

              {currentContent && (
                <div className="mt-4 p-3 rounded-xl bg-slate-800/30 border border-slate-700/50">
                  <p className="text-xs text-slate-500 mb-1">当前内容</p>
                  <p className="text-sm text-slate-300 font-mono break-all line-clamp-2">
                    {currentContent}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
