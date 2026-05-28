import { useState } from 'react';
import { Pipette, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useColorStore } from '@/hooks/useColorStore';

declare global {
  interface Window {
    EyeDropper?: new () => {
      open: () => Promise<{ sRGBHex: string }>;
    };
  }
}

export default function EyeDropperTool() {
  const setCurrentColor = useColorStore((s) => s.setCurrentColor);
  const [isSupported, setIsSupported] = useState(typeof window !== 'undefined' && 'EyeDropper' in window);
  const [isPicking, setIsPicking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePick = async () => {
    if (!window.EyeDropper) {
      setError('您的浏览器不支持取色器 API，请使用 Chrome、Edge 或 Opera 浏览器');
      return;
    }

    try {
      setIsPicking(true);
      setError(null);
      const eyeDropper = new window.EyeDropper();
      const result = await eyeDropper.open();
      setCurrentColor(result.sRGBHex);
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setError('取色失败，请重试');
      }
    } finally {
      setIsPicking(false);
    }
  };

  return (
    <div className="bg-[#1e1e2e] rounded-xl p-5 shadow-lg">
      <div className="flex items-center gap-2 mb-4">
        <Pipette className="w-5 h-5 text-gray-300" />
        <h3 className="text-gray-200 font-medium">屏幕取色器</h3>
      </div>

      <button
        onClick={handlePick}
        disabled={isPicking || !isSupported}
        className="w-full flex items-center justify-center gap-2 bg-[#5b5fc7] hover:bg-[#6b6fd7] disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg py-2.5 text-sm font-medium transition-colors"
      >
        <Pipette className="w-4 h-4" />
        {isPicking ? '取色中...' : '开始取色'}
      </button>

      {error && (
        <div className="mt-3 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-red-300 text-xs">{error}</p>
        </div>
      )}

      {!isSupported && (
        <div className="mt-3 bg-amber-500/10 border border-amber-500/30 rounded-lg px-3 py-2 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-amber-300 text-xs">
            取色器功能需要 Chrome 95+、Edge 95+ 或 Opera 81+ 浏览器
          </p>
        </div>
      )}

      <p className="mt-3 text-gray-500 text-xs">
        点击按钮后鼠标变成取色器，可在屏幕任意位置点击取色
      </p>
    </div>
  );
}
