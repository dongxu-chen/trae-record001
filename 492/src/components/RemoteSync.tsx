import React from 'react';
import { Wifi, WifiOff, Send, Users, Radio } from 'lucide-react';
import { useWebSocket, WSConnectionStatus } from '../hooks/useWebSocket';

const statusConfig: Record<WSConnectionStatus, { label: string; color: string; icon: React.ReactNode }> = {
  disconnected: { label: '未连接', color: 'text-gray-500', icon: <WifiOff className="w-4 h-4" /> },
  connecting: { label: '连接中...', color: 'text-yellow-400', icon: <Wifi className="w-4 h-4 animate-pulse" /> },
  connected: { label: '已连接', color: 'text-green-400', icon: <Wifi className="w-4 h-4" /> }
};

export const RemoteSync: React.FC = () => {
  const { status, peerCount, connect, disconnect, pushSubtitle } = useWebSocket();

  const currentStatus = statusConfig[status];

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
        <Radio className="w-4 h-4" />
        远程字幕推送
      </h3>

      <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className={`flex items-center gap-1.5 ${currentStatus.color}`}>
              {currentStatus.icon}
              <span className="text-sm">{currentStatus.label}</span>
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-gray-400">
            <Users className="w-3.5 h-3.5" />
            <span className="text-xs">{peerCount} 个对端</span>
          </div>
        </div>

        <div className="flex gap-2">
          {status !== 'connected' ? (
            <button
              onClick={connect}
              className="flex-1 flex items-center justify-center gap-2 py-2 text-sm bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-lg hover:bg-cyan-500/30 transition-all"
            >
              <Wifi className="w-4 h-4" />
              连接服务器
            </button>
          ) : (
            <>
              <button
                onClick={pushSubtitle}
                className="flex-1 flex items-center justify-center gap-2 py-2 text-sm bg-green-500/20 text-green-400 border border-green-500/30 rounded-lg hover:bg-green-500/30 transition-all"
              >
                <Send className="w-4 h-4" />
                推送字幕
              </button>
              <button
                onClick={disconnect}
                className="px-3 py-2 text-sm bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-all"
              >
                断开
              </button>
            </>
          )}
        </div>
      </div>

      <div className="text-xs text-gray-500 space-y-1">
        <p>• 连接 WebSocket 服务器后，可向所有对端推送字幕</p>
        <p>• 服务器地址: ws://localhost:3001</p>
        <p>• 接收到的字幕会自动替换当前内容</p>
      </div>
    </div>
  );
};
