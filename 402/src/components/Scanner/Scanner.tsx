import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, Settings, Keyboard, QrCode, BarChart3, Usb } from 'lucide-react';
import { ScannerFrame } from './ScannerFrame';
import { ControlBar } from './ControlBar';
import { ResultModal } from './ResultModal';
import { useCamera } from '../../hooks/useCamera';
import { useScanner } from '../../hooks/useScanner';
import { useHistory } from '../../hooks/useHistory';
import { useSettings } from '../../hooks/useSettings';
import { useScannerGun } from '../../hooks/useScannerGun';
import type { ScanRecord } from '../../types';

export function Scanner() {
  const navigate = useNavigate();
  const [showResult, setShowResult] = useState(false);
  const [gunResult, setGunResult] = useState<string | null>(null);
  
  const camera = useCamera();
  const { settings } = useSettings();
  const { addRecord } = useHistory();
  
  const scanner = useScanner(
    camera.videoRef,
    camera.isActive,
    settings.lowLightEnhance
  );

  const handleGunScan = useCallback((content: string) => {
    if (settings.autoSave) {
      const record: ScanRecord = {
        id: Date.now().toString(),
        content,
        type: 'qrcode',
        format: 'scanner_gun',
        timestamp: Date.now(),
      };
      addRecord(record);
    }
    setGunResult(content);
    setTimeout(() => setGunResult(null), 3000);
  }, [settings.autoSave, addRecord]);

  const scannerGun = useScannerGun(handleGunScan, settings.autoSave);

  useEffect(() => {
    if (scanner.lastResult) {
      setShowResult(true);
      
      if (settings.autoSave) {
        const record: ScanRecord = {
          id: Date.now().toString(),
          content: scanner.lastResult.content,
          type: scanner.lastResult.format === 'qr_code' ? 'qrcode' : 'barcode',
          format: scanner.lastResult.format,
          timestamp: Date.now(),
        };
        addRecord(record);
      }
    }
  }, [scanner.lastResult, settings.autoSave, addRecord]);

  useEffect(() => {
    scanner.setContinuousMode(settings.continuousMode);
  }, [settings.continuousMode, scanner]);

  const handleToggleCamera = async () => {
    if (camera.isActive) {
      scanner.stopScanning();
      camera.stopCamera();
    } else {
      await camera.startCamera(settings.frontCamera ? 'user' : 'environment');
    }
  };

  const handleToggleScanning = () => {
    if (scanner.isScanning) {
      scanner.stopScanning();
    } else {
      scanner.startScanning();
    }
  };

  const handleSaveResult = (content: string, format: string) => {
    const record: ScanRecord = {
      id: Date.now().toString(),
      content,
      type: format === 'qr_code' ? 'qrcode' : 'barcode',
      format,
      timestamp: Date.now(),
    };
    addRecord(record);
  };

  const handleCloseResult = () => {
    setShowResult(false);
    if (scanner.continuousMode) {
      scanner.startScanning();
    }
  };

  return (
    <div className="relative min-h-screen bg-[#0d1117] overflow-hidden">
      <div className="absolute inset-0">
        <video
          ref={camera.videoRef}
          className="w-full h-full object-cover"
          playsInline
          muted
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60" />
      </div>

      {camera.isActive && (
        <ScannerFrame
          isScanning={scanner.isScanning}
          detected={showResult}
        />
      )}

      <div className="absolute top-0 left-0 right-0 z-30">
        <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-b from-black/50 to-transparent">
          <h1 className="text-lg font-semibold text-white">扫码识别</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={() => scannerGun.setIsGunMode(!scannerGun.isGunMode)}
              className={`p-2 rounded-lg transition-colors ${
                scannerGun.isGunMode
                  ? 'bg-yellow-500/30 text-yellow-400'
                  : 'bg-gray-800/80 hover:bg-gray-700 text-gray-300'
              }`}
              title={scannerGun.isGunMode ? '扫码枪模式已开启' : '开启扫码枪模式'}
            >
              <Usb className="w-5 h-5" />
            </button>
            <button
              onClick={() => navigate('/qrcode')}
              className="p-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-gray-300 transition-colors"
              title="二维码生成"
            >
              <QrCode className="w-5 h-5" />
            </button>
            <button
              onClick={() => navigate('/manual')}
              className="p-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-gray-300 transition-colors"
              title="手动输入"
            >
              <Keyboard className="w-5 h-5" />
            </button>
            <button
              onClick={() => navigate('/history')}
              className="p-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-gray-300 transition-colors"
              title="历史记录"
            >
              <History className="w-5 h-5" />
            </button>
            <button
              onClick={() => navigate('/statistics')}
              className="p-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-gray-300 transition-colors"
              title="扫码统计"
            >
              <BarChart3 className="w-5 h-5" />
            </button>
            <button
              onClick={() => navigate('/settings')}
              className="p-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-gray-300 transition-colors"
              title="设置"
            >
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {scannerGun.isGunMode && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-30">
          <div className="px-4 py-2 bg-yellow-500/20 backdrop-blur-sm rounded-full border border-yellow-500/30">
            <span className="text-xs text-yellow-400 font-medium flex items-center gap-1">
              <Usb className="w-3 h-3" />
              扫码枪模式已开启
            </span>
          </div>
        </div>
      )}

      {gunResult && (
        <div className="absolute top-24 left-1/2 -translate-x-1/2 z-30 animate-in fade-in zoom-in-95">
          <div className="px-4 py-3 bg-green-500/20 backdrop-blur-sm rounded-xl border border-green-500/30 max-w-xs">
            <p className="text-sm text-green-400 font-medium mb-1">扫码枪输入</p>
            <p className="text-white text-xs break-all">{gunResult}</p>
          </div>
        </div>
      )}

      {!camera.isActive && !scannerGun.isGunMode && (
        <div className="absolute inset-0 flex items-center justify-center z-20">
          <div className="text-center px-6">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-800 flex items-center justify-center">
              <svg
                className="w-10 h-10 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">
              {camera.error ? '摄像头访问失败' : '准备开始扫码'}
            </h2>
            <p className="text-gray-400 mb-6 max-w-xs mx-auto text-sm">
              {camera.error || '点击下方按钮开启摄像头，将二维码对准扫描框即可识别'}
            </p>
            <button
              onClick={handleToggleCamera}
              className="px-8 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-medium transition-all shadow-lg shadow-blue-600/30"
            >
              开启摄像头
            </button>
          </div>
        </div>
      )}

      {camera.isActive && !scanner.isScanning && !showResult && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
          <div className="text-center">
            <p className="text-white/80 text-sm mb-3">点击下方按钮开始扫描</p>
          </div>
        </div>
      )}

      {scanner.isScanning && scanner.scanQueueSize > 0 && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-30">
          <div className="px-3 py-1 bg-black/60 backdrop-blur-sm rounded-full">
            <span className="text-xs text-gray-300">
              处理中: {scanner.scanQueueSize} 帧
            </span>
          </div>
        </div>
      )}

      <ControlBar
        isActive={camera.isActive}
        isScanning={scanner.isScanning}
        continuousMode={scanner.continuousMode}
        torchSupported={camera.torchSupported}
        torchEnabled={camera.torchEnabled}
        onToggleCamera={handleToggleCamera}
        onToggleScanning={handleToggleScanning}
        onToggleContinuous={() => scanner.setContinuousMode(!scanner.continuousMode)}
        onToggleTorch={camera.toggleTorch}
        onSwitchCamera={camera.switchCamera}
      />

      <ResultModal
        result={showResult ? scanner.lastResult : null}
        onClose={handleCloseResult}
        onSave={handleSaveResult}
        autoSave={settings.autoSave}
      />
    </div>
  );
}
