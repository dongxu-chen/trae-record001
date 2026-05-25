import React from 'react';
import useMeetingStore from '../store/useMeetingStore';
import { VIRTUAL_BACKGROUNDS } from '../config/webrtcConfig';
import { BackgroundIcon } from './icons';

const SettingsPanel = () => {
  const {
    virtualBackground,
    setVirtualBackground,
    currentResolution
  } = useMeetingStore();

  const handleVirtualBgChange = (bg) => {
    if (bg.id === 'none') {
      setVirtualBackground(null);
    } else {
      setVirtualBackground(bg);
    }
  };

  const getBgPreviewStyle = (bg) => {
    if (bg.type === 'none') {
      return { background: '#1e293b' };
    }
    if (bg.type === 'blur') {
      return { background: '#475569', filter: 'blur(4px)' };
    }
    if (bg.type === 'color') {
      return { background: bg.color };
    }
    if (bg.type === 'gradient') {
      return {
        background: `linear-gradient(135deg, ${bg.colors[0]}, ${bg.colors[1]})`
      };
    }
    return {};
  };

  return (
    <div className="w-80 h-full bg-slate-800 border-l border-slate-700 flex flex-col">
      <div className="p-4 border-b border-slate-700">
        <h3 className="text-lg font-semibold text-white">设置</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div>
          <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
            <BackgroundIcon className="w-4 h-4" />
            虚拟背景
          </h4>
          <div className="grid grid-cols-3 gap-3">
            {VIRTUAL_BACKGROUNDS.map((bg) => {
              const isSelected = virtualBackground
                ? virtualBackground.id === bg.id
                : bg.id === 'none';

              return (
                <button
                  key={bg.id}
                  onClick={() => handleVirtualBgChange(bg)}
                  className={`relative aspect-video rounded-lg overflow-hidden transition-all ${
                    isSelected
                      ? 'ring-2 ring-primary-500 ring-offset-2 ring-offset-slate-800'
                      : 'hover:ring-2 hover:ring-slate-500'
                  }`}
                >
                  <div
                    className="absolute inset-0"
                    style={getBgPreviewStyle(bg)}
                  />
                  {bg.id === 'blur' && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-xs text-white bg-black/50 px-2 py-1 rounded">
                        模糊
                      </span>
                    </div>
                  )}
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-1.5">
                    <span className="text-xs text-white truncate block">
                      {bg.name}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-slate-300 mb-3">当前视频设置</h4>
          <div className="bg-slate-700/50 rounded-lg p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">分辨率</span>
              <span className="text-white">
                {currentResolution.width} × {currentResolution.height}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">回声消除</span>
              <span className="text-green-400">已启用</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">噪声抑制</span>
              <span className="text-green-400">已启用</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-400">自动增益</span>
              <span className="text-green-400">已启用</span>
            </div>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-medium text-slate-300 mb-3">关于</h4>
          <div className="bg-slate-700/50 rounded-lg p-4 space-y-2">
            <p className="text-sm text-slate-400">
              基于 WebRTC + Simple-Peer 技术构建
            </p>
            <p className="text-xs text-slate-500">
              支持最多 50 人同时参会
            </p>
            <p className="text-xs text-slate-500">
              带宽自适应动态调整分辨率
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
