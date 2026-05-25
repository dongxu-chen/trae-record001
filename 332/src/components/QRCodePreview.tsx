import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { generateQRCodeCanvas } from '@/utils/qrGenerator';
import type { QRStyle } from '@/types';

interface QRCodePreviewProps {
  content: string;
  style: QRStyle;
  canvasId?: string;
}

export default function QRCodePreview({
  content,
  style,
  canvasId = 'qr-preview-canvas',
}: QRCodePreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const generate = async () => {
      if (!content) return;
      await generateQRCodeCanvas(content, style, canvasId);
    };
    generate();
  }, [content, style, canvasId]);

  return (
    <motion.div
      ref={containerRef}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className="relative flex items-center justify-center p-8 rounded-2xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700/50 backdrop-blur-sm"
    >
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 to-cyan-500/5 rounded-2xl" />
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-blue-500/30 to-transparent" />
      
      {content ? (
        <div className="relative">
          <canvas
            ref={canvasRef}
            id={canvasId}
            className="rounded-lg shadow-2xl"
            style={{ width: style.size, height: style.size }}
          />
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center text-slate-500 p-16">
          <div className="w-24 h-24 border-2 border-dashed border-slate-600 rounded-xl flex items-center justify-center mb-4">
            <span className="text-4xl">📱</span>
          </div>
          <p className="text-sm">输入内容后自动生成二维码</p>
        </div>
      )}
    </motion.div>
  );
}
