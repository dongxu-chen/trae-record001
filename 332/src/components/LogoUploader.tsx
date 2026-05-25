import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Upload, X, Image as ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LogoUploaderProps {
  value?: string;
  onChange: (logo?: string) => void;
  logoSize?: number;
  onLogoSizeChange?: (size: number) => void;
  logoBgColor?: string;
  onLogoBgColorChange?: (color: string) => void;
}

export default function LogoUploader({
  value,
  onChange,
  logoSize = 0.2,
  onLogoSizeChange,
  logoBgColor = '#ffffff',
  onLogoBgColorChange,
}: LogoUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = (file: File) => {
    if (!file.type.startsWith('image/')) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      onChange(result);
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  return (
    <div className="space-y-4">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200',
          isDragging
            ? 'border-blue-500 bg-blue-500/10'
            : 'border-slate-700 hover:border-slate-600 bg-slate-800/30'
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          className="hidden"
        />
        
        {value ? (
          <div className="relative inline-block">
            <img
              src={value}
              alt="Logo"
              className="max-w-24 max-h-24 rounded-lg mx-auto"
            />
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={(e) => {
                e.stopPropagation();
                onChange(undefined);
              }}
              className="absolute -top-2 -right-2 w-6 h-6 flex items-center justify-center rounded-full bg-red-500 text-white shadow-lg"
            >
              <X size={14} />
            </motion.button>
          </div>
        ) : (
          <div className="py-4">
            <Upload className="mx-auto h-10 w-10 text-slate-500 mb-3" />
            <p className="text-sm text-slate-400">
              点击或拖拽上传Logo图片
            </p>
            <p className="text-xs text-slate-500 mt-1">
              支持 PNG, JPG, SVG 格式
            </p>
          </div>
        )}
      </div>

      {value && (
        <div className="space-y-3 pt-2 border-t border-slate-700/50">
          <div>
            <label className="block text-sm text-slate-400 mb-2">
              Logo 大小: {Math.round(logoSize * 100)}%
            </label>
            <input
              type="range"
              min="0.1"
              max="0.4"
              step="0.05"
              value={logoSize}
              onChange={(e) => onLogoSizeChange?.(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">
              Logo 背景色
            </label>
            <div className="flex gap-2">
              {['#ffffff', '#000000', 'transparent'].map((color) => (
                <motion.button
                  key={color}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => onLogoBgColorChange?.(color)}
                  className={cn(
                    'w-8 h-8 rounded-lg border-2 transition-all',
                    logoBgColor === color
                      ? 'border-blue-500 ring-2 ring-blue-500/30'
                      : 'border-slate-600 hover:border-slate-500'
                  )}
                  style={{
                    backgroundColor: color === 'transparent' ? 'initial' : color,
                    backgroundImage: color === 'transparent'
                      ? 'linear-gradient(45deg, #64748b 25%, transparent 25%), linear-gradient(-45deg, #64748b 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #64748b 75%), linear-gradient(-45deg, transparent 75%, #64748b 75%)'
                      : 'none',
                    backgroundSize: '8px 8px',
                    backgroundPosition: '0 0, 0 4px, 4px -4px, -4px 0px',
                  }}
                />
              ))}
              <input
                type="color"
                value={logoBgColor === 'transparent' ? '#ffffff' : logoBgColor}
                onChange={(e) => onLogoBgColorChange?.(e.target.value)}
                className="w-8 h-8 rounded-lg cursor-pointer bg-transparent"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
