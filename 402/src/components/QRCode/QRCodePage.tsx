import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Smartphone, Check, X, RefreshCw, Copy } from 'lucide-react';
import { QRCodeGenerator } from '../QRCode/QRCodeGenerator';
import { useSettings } from '../../hooks/useSettings';

export function QRCodePage() {
  const navigate = useNavigate();
  const { settings } = useSettings();
  const [qrContent, setQrContent] = useState('');
  const [customContent, setCustomContent] = useState('');
  const [sessionToken, setSessionToken] = useState('');
  const [isWaitingScan, setIsWaitingScan] = useState(false);
  const [scanStatus, setScanStatus] = useState<'idle' | 'waiting' | 'success' | 'timeout'>('idle');
  
  const generateSessionToken = useCallback(() => {
    const token = Math.random().toString(36).substring(2, 10).toUpperCase() + 
                  Date.now().toString(36).toUpperCase();
    return token;
  }, []);

  const generateLoginQR = useCallback(() => {
    const token = generateSessionToken();
    setSessionToken(token);
    
    const loginPayload = JSON.stringify({
      type: 'login',
      token,
      timestamp: Date.now(),
      mode: 'cross-device',
    });
    
    setQrContent(loginPayload);
    setIsWaitingScan(true);
    setScanStatus('waiting');
  }, [generateSessionToken]);

  const generateContentQR = useCallback(() => {
    if (customContent.trim()) {
      setQrContent(customContent);
      setIsWaitingScan(false);
      setScanStatus('idle');
    }
  }, [customContent]);

  const handleCopyToken = async () => {
    if (sessionToken) {
      await navigator.clipboard.writeText(sessionToken);
    }
  };

  useEffect(() => {
    if (isWaitingScan && scanStatus === 'waiting') {
      const timeout = setTimeout(() => {
        setScanStatus('timeout');
        setIsWaitingScan(false);
      }, 60000);
      
      return () => clearTimeout(timeout);
    }
  }, [isWaitingScan, scanStatus]);

  return (
    <div className="min-h-screen bg-[#0d1117]">
      <div className="sticky top-0 z-40 bg-[#0d1117]/95 backdrop-blur-xl border-b border-gray-800">
        <div className="px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="p-2 -ml-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-lg font-semibold text-white">二维码生成</h1>
        </div>
      </div>

      <div className="p-4 max-w-lg mx-auto space-y-6">
        <div className="bg-[#161b22] rounded-xl border border-gray-700/50 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-700/50 bg-gray-800/30">
            <div className="flex items-center gap-2">
              <Smartphone className="w-4 h-4 text-blue-400" />
              <h2 className="text-sm font-medium text-gray-300">跨设备登录</h2>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              使用手机扫描此二维码在大屏登录
            </p>
          </div>
          
          <div className="p-4">
            {isWaitingScan ? (
              <div className="flex flex-col items-center gap-4">
                <div className="relative">
                  <QRCodeGenerator value={qrContent} size={200} />
                  
                  {scanStatus === 'waiting' && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-ping" />
                    </div>
                  )}
                </div>
                
                {scanStatus === 'success' && (
                  <div className="flex items-center gap-2 px-4 py-2 bg-green-500/20 rounded-lg">
                    <Check className="w-4 h-4 text-green-400" />
                    <span className="text-sm text-green-400">登录成功</span>
                  </div>
                )}
                
                {scanStatus === 'timeout' && (
                  <div className="flex items-center gap-2 px-4 py-2 bg-red-500/20 rounded-lg">
                    <X className="w-4 h-4 text-red-400" />
                    <span className="text-sm text-red-400">二维码已过期</span>
                  </div>
                )}
                
                {sessionToken && (
                  <div className="flex items-center gap-2 px-3 py-2 bg-gray-800/50 rounded-lg">
                    <span className="text-xs text-gray-500">会话:</span>
                    <code className="text-sm text-blue-400 font-mono">{sessionToken}</code>
                    <button
                      onClick={handleCopyToken}
                      className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                  </div>
                )}
                
                <div className="flex gap-2">
                  <button
                    onClick={generateLoginQR}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-white text-sm font-medium transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    刷新二维码
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 py-4">
                <div className="w-48 h-48 bg-gray-800/30 rounded-xl border border-dashed border-gray-700 flex items-center justify-center">
                  <div className="text-center">
                    <Smartphone className="w-10 h-10 text-gray-600 mx-auto mb-2" />
                    <p className="text-sm text-gray-500">点击生成登录二维码</p>
                  </div>
                </div>
                
                <button
                  onClick={generateLoginQR}
                  className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-medium transition-colors shadow-lg shadow-blue-600/30"
                >
                  <Smartphone className="w-5 h-5" />
                  生成登录二维码
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="bg-[#161b22] rounded-xl border border-gray-700/50 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-700/50 bg-gray-800/30">
            <h2 className="text-sm font-medium text-gray-300">自定义内容</h2>
          </div>
          
          <div className="p-4 space-y-4">
            <textarea
              value={customContent}
              onChange={(e) => setCustomContent(e.target.value)}
              placeholder="输入要生成二维码的内容..."
              rows={4}
              className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none font-mono text-sm"
            />
            
            {customContent.trim() && (
              <QRCodeGenerator value={customContent} size={200} />
            )}
            
            <button
              onClick={generateContentQR}
              disabled={!customContent.trim()}
              className={`w-full py-3 rounded-xl font-medium transition-colors ${
                customContent.trim()
                  ? 'bg-green-600 hover:bg-green-500 text-white'
                  : 'bg-gray-700 text-gray-500 cursor-not-allowed'
              }`}
            >
              生成二维码
            </button>
          </div>
        </div>

        <div className="bg-[#161b22] rounded-xl border border-gray-700/50 p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">快速生成</h3>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: '网址', value: 'https://' },
              { label: '邮箱', value: 'mailto:' },
              { label: '电话', value: 'tel:' },
              { label: 'WiFi', value: 'WIFI:T:WPA;S:network;P:password;;' },
            ].map((item) => (
              <button
                key={item.label}
                onClick={() => {
                  setCustomContent(item.value);
                  setQrContent(item.value);
                }}
                className="px-3 py-2 bg-gray-800/50 hover:bg-gray-700/50 rounded-lg text-sm text-gray-300 transition-colors text-left"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
