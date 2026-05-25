import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Palette, Settings, Image, ChevronDown, RotateCcw, Sparkles, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import ColorPicker from './ColorPicker';
import LogoUploader from './LogoUploader';
import type { QRStyle, DotStyle, ErrorCorrectionLevel, ArtPattern, EyeStyle } from '@/types';
import { artPatterns, eyeStyles } from '@/types';

interface StylePanelProps {
  style: QRStyle;
  onChange: (style: Partial<QRStyle>) => void;
  onReset: () => void;
  showArtOptions?: boolean;
}

const dotStyles: Array<{ value: DotStyle; label: string }> = [
  { value: 'square', label: '方形' },
  { value: 'round', label: '圆角' },
  { value: 'dots', label: '圆点' },
];

const errorLevels: Array<{ value: ErrorCorrectionLevel; label: string; desc: string }> = [
  { value: 'L', label: '低', desc: '7% 容错' },
  { value: 'M', label: '中', desc: '15% 容错' },
  { value: 'Q', label: '较高', desc: '25% 容错' },
  { value: 'H', label: '高', desc: '30% 容错' },
];

const gradientTypes: Array<{ value: 'linear' | 'radial' | 'diagonal'; label: string }> = [
  { value: 'linear', label: '线性' },
  { value: 'radial', label: '径向' },
  { value: 'diagonal', label: '对角' },
];

interface SectionProps {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function Section({ title, icon: Icon, children, defaultOpen = true }: SectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-slate-700/50 last:border-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 py-4 text-left hover:text-white transition-colors"
      >
        <Icon size={18} className="text-blue-400" />
        <span className="font-medium flex-1">{title}</span>
        <motion.div animate={{ rotate: isOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown size={18} className="text-slate-500" />
        </motion.div>
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden pb-4"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function StylePanel({ style, onChange, onReset, showArtOptions = true }: StylePanelProps) {
  const showGradientOptions = style.artPattern === 'gradient';

  return (
    <div className="rounded-xl bg-slate-800/30 border border-slate-700/50 backdrop-blur-sm">
      <div className="px-4 py-3 border-b border-slate-700/50 flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2">
          <Settings size={18} className="text-blue-400" />
          样式设置
        </h3>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onReset}
          className="flex items-center gap-1 px-3 py-1.5 text-xs rounded-lg bg-slate-700/50 hover:bg-slate-700 text-slate-300 transition-colors"
        >
          <RotateCcw size={14} />
          重置
        </motion.button>
      </div>

      <div className="px-4">
        {showArtOptions && (
          <Section title="艺术样式" icon={Sparkles} defaultOpen={false}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  艺术图案
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {artPatterns.map(({ value, label, description }) => (
                    <motion.button
                      key={value}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => onChange({ artPattern: value })}
                      className={cn(
                        'p-3 rounded-lg text-xs font-medium transition-all border text-left',
                        style.artPattern === value
                          ? 'bg-gradient-to-r from-blue-600/20 to-cyan-500/20 text-white border-blue-500/50'
                          : 'bg-slate-800/50 text-slate-300 border-slate-700 hover:border-slate-600'
                      )}
                    >
                      <div className="font-medium">{label}</div>
                      <div className="text-[10px] opacity-70 mt-0.5">{description}</div>
                    </motion.button>
                  ))}
                </div>
              </div>

              {showGradientOptions && (
                <div className="space-y-4 pt-2">
                  <div className="grid grid-cols-2 gap-3">
                    <ColorPicker
                      label="渐变起始色"
                      value={style.gradientStart || '#1e3a8a'}
                      onChange={(color) => onChange({ gradientStart: color })}
                    />
                    <ColorPicker
                      label="渐变结束色"
                      value={style.gradientEnd || '#06b6d4'}
                      onChange={(color) => onChange({ gradientEnd: color })}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      渐变类型
                    </label>
                    <div className="flex gap-2">
                      {gradientTypes.map(({ value, label }) => (
                        <motion.button
                          key={value}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => onChange({ gradientType: value })}
                          className={cn(
                            'flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-all border',
                            style.gradientType === value
                              ? 'bg-blue-600 text-white border-transparent'
                              : 'bg-slate-800/50 text-slate-300 border-slate-700 hover:border-slate-600'
                          )}
                        >
                          {label}
                        </motion.button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  角落图案样式
                </label>
                <div className="grid grid-cols-5 gap-2">
                  {eyeStyles.map(({ value, label }) => (
                    <motion.button
                      key={value}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => onChange({ eyeStyle: value })}
                      className={cn(
                        'aspect-square rounded-lg text-xs font-medium transition-all border flex items-center justify-center',
                        style.eyeStyle === value
                          ? 'bg-blue-600 text-white border-transparent'
                          : 'bg-slate-800/50 text-slate-300 border-slate-700 hover:border-slate-600'
                      )}
                      title={label}
                    >
                      {value === 'square' && '□'}
                      {value === 'rounded' && '◯'}
                      {value === 'circle' && '●'}
                      {value === 'heart' && '♥'}
                      {value === 'star' && '★'}
                    </motion.button>
                  ))}
                </div>
              </div>
            </div>
          </Section>
        )}

        <Section title="颜色设置" icon={Palette}>
          <div className="space-y-4">
            <ColorPicker
              label="前景色"
              value={style.foregroundColor}
              onChange={(color) => onChange({ foregroundColor: color })}
            />
            <ColorPicker
              label="背景色"
              value={style.backgroundColor}
              onChange={(color) => onChange({ backgroundColor: color })}
            />
          </div>
        </Section>

        <Section title="码点样式" icon={Layers}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                码点形状
              </label>
              <div className="flex gap-2">
                {dotStyles.map(({ value, label }) => (
                  <motion.button
                    key={value}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => onChange({ dotStyle: value })}
                    className={cn(
                      'flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all border',
                      style.dotStyle === value
                        ? 'bg-blue-600 text-white border-transparent'
                        : 'bg-slate-800/50 text-slate-300 border-slate-700 hover:border-slate-600'
                    )}
                  >
                    {label}
                  </motion.button>
                ))}
              </div>
            </div>

            {style.dotStyle === 'square' && (
              <div>
                <label className="block text-sm text-slate-400 mb-2">
                  圆角半径: {style.cornerRadius}px
                </label>
                <input
                  type="range"
                  min="0"
                  max="10"
                  value={style.cornerRadius}
                  onChange={(e) => onChange({ cornerRadius: parseInt(e.target.value) })}
                  className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
              </div>
            )}

            <div>
              <label className="block text-sm text-slate-400 mb-2">
                尺寸: {style.size}px
              </label>
              <input
                type="range"
                min="100"
                max="500"
                step="20"
                value={style.size}
                onChange={(e) => onChange({ size: parseInt(e.target.value) })}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                容错等级
              </label>
              <div className="grid grid-cols-4 gap-2">
                {errorLevels.map(({ value, label, desc }) => (
                  <motion.button
                    key={value}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => onChange({ errorCorrectionLevel: value })}
                    className={cn(
                      'px-2 py-2 rounded-lg text-xs transition-all border',
                      style.errorCorrectionLevel === value
                        ? 'bg-blue-600 text-white border-transparent'
                        : 'bg-slate-800/50 text-slate-300 border-slate-700 hover:border-slate-600'
                    )}
                  >
                    <div className="font-medium">{label}</div>
                    <div className="text-[10px] opacity-70">{desc}</div>
                  </motion.button>
                ))}
              </div>
              {style.logo && (
                <p className="text-xs text-cyan-400 mt-2 flex items-center gap-1">
                  <Sparkles size={12} />
                  Logo已启用，自动使用H级容错
                </p>
              )}
            </div>
          </div>
        </Section>

        <Section title="Logo设置" icon={Image} defaultOpen={false}>
          <LogoUploader
            value={style.logo}
            onChange={(logo) => onChange({ logo })}
            logoSize={style.logoSize}
            onLogoSizeChange={(logoSize) => onChange({ logoSize })}
            logoBgColor={style.logoBackgroundColor}
            onLogoBgColorChange={(logoBackgroundColor) => onChange({ logoBackgroundColor })}
          />
        </Section>
      </div>
    </div>
  );
}
