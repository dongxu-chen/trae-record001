import { useState, useEffect, useRef } from 'react';
import { Copy, Check, Download, RefreshCw } from 'lucide-react';
import QRCode from 'qrcode';

interface QRCodeGeneratorProps {
  value: string;
  size?: number;
  onGenerated?: (dataUrl: string) => void;
}

export function QRCodeGenerator({ value, size = 256, onGenerated }: QRCodeGeneratorProps) {
  const [dataUrl, setDataUrl] = useState<string>('');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!value.trim()) {
      setDataUrl('');
      return;
    }

    const generateQR = async () => {
      try {
        setError(null);
        const url = await QRCode.toDataURL(value, {
          width: size,
          margin: 2,
          color: {
            dark: '#000000',
            light: '#ffffff',
          },
          errorCorrectionLevel: 'H',
        });
        setDataUrl(url);
        onGenerated?.(url);
      } catch (err) {
        setError(err instanceof Error ? err.message : '生成二维码失败');
      }
    };

    generateQR();
  }, [value, size, onGenerated]);

  const handleCopy = async () => {
    if (!dataUrl) return;
    
    try {
      const response = await fetch(dataUrl);
      const blob = await response.blob();
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': blob }),
      ]);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const handleDownload = () => {
    if (!dataUrl) return;
    
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = `qrcode-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (error) {
    return (
      <div className="flex items-center justify-center p-4 bg-red-500/10 rounded-xl">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    );
  }

  if (!value.trim()) {
    return (
      <div className="flex items-center justify-center p-8 bg-gray-800/50 rounded-xl border border-dashed border-gray-700">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-gray-600 mx-auto mb-2" />
          <p className="text-sm text-gray-500">输入内容生成二维码</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4">
      {dataUrl && (
        <div className="p-4 bg-white rounded-xl shadow-lg">
          <img 
            src={dataUrl} 
            alt="QR Code" 
            className="block"
            style={{ width: size, height: size }}
          />
        </div>
      )}
      
      <canvas ref={canvasRef} className="hidden" />
      
      <div className="flex gap-2">
        <button
          onClick={handleCopy}
          disabled={!dataUrl}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
            copied
              ? 'bg-green-500/20 text-green-400'
              : dataUrl
              ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              : 'bg-gray-800 text-gray-600 cursor-not-allowed'
          }`}
        >
          {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          {copied ? '已复制' : '复制图片'}
        </button>
        
        <button
          onClick={handleDownload}
          disabled={!dataUrl}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
            dataUrl
              ? 'bg-blue-600 text-white hover:bg-blue-500'
              : 'bg-gray-800 text-gray-600 cursor-not-allowed'
          }`}
        >
          <Download className="w-4 h-4" />
          下载
        </button>
      </div>
    </div>
  );
}
