import React, { useEffect } from 'react';
import { Monitor, MonitorOff, Send, Users } from 'lucide-react';
import { useMultiScreenSync } from '../hooks/useMultiScreenSync';
import { useLEDStore } from '../store/ledStore';

export const MultiScreenSync: React.FC = () => {
  const { isSyncing, screenCount, toggleSync, broadcastState, broadcastPlayState } = useMultiScreenSync();
  const isPlaying = useLEDStore((s) => s.isPlaying);

  useEffect(() => {
    if (isSyncing) {
      broadcastPlayState();
    }
  }, [isPlaying, isSyncing, broadcastPlayState]);

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
        <Monitor className="w-4 h-4" />
        多屏同步
      </h3>

      <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {isSyncing ? (
              <span className="flex items-center gap-1.5 text-cyan-400">
                <Monitor className="w-4 h-4" />
                <span className="text-sm">同步中</span>
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-gray-500">
                <MonitorOff className="w-4 h-4" />
                <span className="text-sm">未同步</span>
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5 text-gray-400">
            <Users className="w-3.5 h-3.5" />
            <span className="text-xs">{screenCount} 块屏幕</span>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={toggleSync}
            className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm rounded-lg transition-all ${
              isSyncing
                ? 'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30'
                : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30'
            }`}
          >
            {isSyncing ? (
              <>
                <MonitorOff className="w-4 h-4" />
                停止同步
              </>
            ) : (
              <>
                <Monitor className="w-4 h-4" />
                开始同步
              </>
            )}
          </button>

          {isSyncing && (
            <button
              onClick={broadcastState}
              className="px-3 py-2 text-sm bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded-lg hover:bg-purple-500/30 transition-all"
              title="广播当前状态到所有屏幕"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <div className="text-xs text-gray-500 space-y-1">
        <p>• 使用 BroadcastChannel API 实现同源多屏同步</p>
        <p>• 在多个浏览器标签页中打开即可同步</p>
        <p>• 字幕内容、滚动状态、播放状态实时同步</p>
      </div>
    </div>
  );
};
