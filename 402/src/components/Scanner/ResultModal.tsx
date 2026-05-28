import { useState } from 'react';
import { Copy, Check, Save, X } from 'lucide-react';

interface ResultModalProps {
  result: {
    content: string;
    format: string;
  } | null;
  onClose: () => void;
  onSave: (content: string, format: string) => void;
  autoSave: boolean;
}

export function ResultModal({ result, onClose, onSave, autoSave }: ResultModalProps) {
  const [copied, setCopied] = useState(false);
  const [saved, setSaved] = useState(false);

  if (!result) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const handleSave = () => {
    if (autoSave) return;
    onSave(result.content, result.format);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      <div className="relative w-full max-w-md bg-[#161b22] rounded-2xl shadow-2xl border border-gray-700 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-purple-500" />
        
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                <Check className="w-5 h-5 text-green-400" />
              </div>
              <span className="text-sm font-medium text-gray-400">识别成功</span>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-gray-700 transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>

          <div className="mb-4">
            <span className="inline-block px-2 py-1 text-xs font-medium rounded bg-blue-500/20 text-blue-400">
              {result.format}
            </span>
          </div>

          <div className="p-4 bg-gray-900/50 rounded-xl border border-gray-700 mb-4">
            <p className="text-white text-sm break-all font-mono leading-relaxed">
              {result.content}
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleCopy}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-xl text-white text-sm font-medium transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4" />
                  已复制
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  复制内容
                </>
              )}
            </button>
            
            {!autoSave && (
              <button
                onClick={handleSave}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-white text-sm font-medium transition-colors"
              >
                {saved ? (
                  <>
                    <Check className="w-4 h-4" />
                    已保存
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    保存记录
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
