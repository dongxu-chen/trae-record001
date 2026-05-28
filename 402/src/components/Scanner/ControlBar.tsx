import { Camera, CameraOff, Repeat, Repeat1, Sun, Flashlight, SwitchCamera } from 'lucide-react';

interface ControlBarProps {
  isActive: boolean;
  isScanning: boolean;
  continuousMode: boolean;
  torchSupported: boolean;
  torchEnabled: boolean;
  onToggleCamera: () => void;
  onToggleScanning: () => void;
  onToggleContinuous: () => void;
  onToggleTorch: () => void;
  onSwitchCamera: () => void;
}

export function ControlBar({
  isActive,
  isScanning,
  continuousMode,
  torchSupported,
  torchEnabled,
  onToggleCamera,
  onToggleScanning,
  onToggleContinuous,
  onToggleTorch,
  onSwitchCamera,
}: ControlBarProps) {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-40">
      <div className="mx-auto max-w-lg px-4 pb-6">
        <div className="flex items-center justify-center gap-3 p-2 bg-gray-900/90 backdrop-blur-xl rounded-2xl border border-gray-700/50 shadow-2xl">
          <button
            onClick={onToggleCamera}
            className={`p-3 rounded-xl transition-all duration-200 ${
              isActive
                ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
            }`}
            title={isActive ? '关闭摄像头' : '开启摄像头'}
          >
            {isActive ? <CameraOff className="w-6 h-6" /> : <Camera className="w-6 h-6" />}
          </button>

          <button
            onClick={onToggleScanning}
            disabled={!isActive}
            className={`p-3 rounded-xl transition-all duration-200 ${
              isActive
                ? isScanning
                  ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                  : 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30'
                : 'bg-gray-700/50 text-gray-500 cursor-not-allowed'
            }`}
            title={isScanning ? '暂停扫描' : '开始扫描'}
          >
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
              isScanning ? 'border-white' : 'border-current'
            }`}>
              {isScanning ? (
                <div className="w-2 h-2 rounded-sm bg-current" />
              ) : (
                <div className="w-0 h-0 border-l-[6px] border-l-current border-y-[5px] border-y-transparent ml-1" />
              )}
            </div>
          </button>

          <button
            onClick={onToggleContinuous}
            disabled={!isActive}
            className={`p-3 rounded-xl transition-all duration-200 ${
              isActive
                ? continuousMode
                  ? 'bg-purple-500/20 text-purple-400 hover:bg-purple-500/30'
                  : 'bg-gray-700/50 text-gray-400 hover:bg-gray-700'
                : 'bg-gray-700/30 text-gray-600 cursor-not-allowed'
            }`}
            title={continuousMode ? '单次模式' : '连续模式'}
          >
            {continuousMode ? <Repeat className="w-6 h-6" /> : <Repeat1 className="w-6 h-6" />}
          </button>

          <button
            onClick={onSwitchCamera}
            disabled={!isActive}
            className={`p-3 rounded-xl transition-all duration-200 ${
              isActive
                ? 'bg-gray-700/50 text-gray-400 hover:bg-gray-700'
                : 'bg-gray-700/30 text-gray-600 cursor-not-allowed'
            }`}
            title="切换摄像头"
          >
            <SwitchCamera className="w-6 h-6" />
          </button>

          {torchSupported && (
            <button
              onClick={onToggleTorch}
              disabled={!isActive}
              className={`p-3 rounded-xl transition-all duration-200 ${
                isActive
                  ? torchEnabled
                    ? 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30'
                    : 'bg-gray-700/50 text-gray-400 hover:bg-gray-700'
                  : 'bg-gray-700/30 text-gray-600 cursor-not-allowed'
              }`}
              title={torchEnabled ? '关闭闪光灯' : '开启闪光灯'}
            >
              {torchEnabled ? <Sun className="w-6 h-6" /> : <Flashlight className="w-6 h-6" />}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
