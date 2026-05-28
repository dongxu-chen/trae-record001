import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Sun, Moon, RotateCcw, RefreshCcw } from 'lucide-react';
import { ToggleSwitch } from './ToggleSwitch';
import { useSettings } from '../../hooks/useSettings';

export function SettingsPanel() {
  const navigate = useNavigate();
  const { settings, updateSettings, resetSettings } = useSettings();

  const handleReset = () => {
    if (confirm('确定要恢复默认设置吗？')) {
      resetSettings();
    }
  };

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
          <h1 className="text-lg font-semibold text-white">设置</h1>
        </div>
      </div>

      <div className="p-4 max-w-lg mx-auto space-y-6">
        <div className="bg-[#161b22] rounded-xl border border-gray-700/50 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-700/50">
            <h2 className="text-sm font-medium text-gray-400">扫码设置</h2>
          </div>
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">连续扫码模式</p>
                <p className="text-sm text-gray-500">识别成功后继续扫描</p>
              </div>
              <ToggleSwitch
                checked={settings.continuousMode}
                onChange={(v) => updateSettings({ continuousMode: v })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">自动保存记录</p>
                <p className="text-sm text-gray-500">识别成功后自动保存到历史</p>
              </div>
              <ToggleSwitch
                checked={settings.autoSave}
                onChange={(v) => updateSettings({ autoSave: v })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">振动反馈</p>
                <p className="text-sm text-gray-500">识别成功时手机振动</p>
              </div>
              <ToggleSwitch
                checked={settings.vibrateOnSuccess}
                onChange={(v) => updateSettings({ vibrateOnSuccess: v })}
              />
            </div>
          </div>
        </div>

        <div className="bg-[#161b22] rounded-xl border border-gray-700/50 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-700/50">
            <h2 className="text-sm font-medium text-gray-400">摄像头设置</h2>
          </div>
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sun className="w-4 h-4 text-yellow-500" />
                <div>
                  <p className="text-white font-medium">使用前置摄像头</p>
                  <p className="text-sm text-gray-500">默认使用后置摄像头</p>
                </div>
              </div>
              <ToggleSwitch
                checked={settings.frontCamera}
                onChange={(v) => updateSettings({ frontCamera: v })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-white font-medium">低光照增强</p>
                <p className="text-sm text-gray-500">自适应伽马校正 + 噪声抑制</p>
              </div>
              <ToggleSwitch
                checked={settings.lowLightEnhance}
                onChange={(v) => updateSettings({ lowLightEnhance: v })}
              />
            </div>
          </div>
        </div>

        <div className="bg-[#161b22] rounded-xl border border-gray-700/50 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-700/50">
            <h2 className="text-sm font-medium text-gray-400">导出设置</h2>
          </div>
          <div className="p-4">
            <p className="text-white font-medium mb-3">导出格式</p>
            <div className="flex gap-2">
              <button
                onClick={() => updateSettings({ exportFormat: 'json' })}
                className={`flex-1 px-4 py-2.5 rounded-xl font-medium transition-all ${
                  settings.exportFormat === 'json'
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                JSON
              </button>
              <button
                onClick={() => updateSettings({ exportFormat: 'csv' })}
                className={`flex-1 px-4 py-2.5 rounded-xl font-medium transition-all ${
                  settings.exportFormat === 'csv'
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                }`}
              >
                CSV
              </button>
            </div>
          </div>
        </div>

        <div className="bg-[#161b22] rounded-xl border border-gray-700/50 overflow-hidden">
          <div className="p-4">
            <button
              onClick={handleReset}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 text-red-400 hover:bg-red-500/10 rounded-xl transition-colors"
            >
              <RotateCcw className="w-5 h-5" />
              恢复默认设置
            </button>
          </div>
        </div>

        <div className="text-center text-sm text-gray-500 pt-4 space-y-1">
          <p>版本 2.0.0</p>
          <p className="text-xs">ZXing WASM · 自适应伽马校正 · 生产者消费者模式</p>
        </div>
      </div>
    </div>
  );
}
