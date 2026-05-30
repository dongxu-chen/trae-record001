import { useState } from 'react';
import {
  Home,
  ChevronRight,
  RotateCcw,
  Clock,
  Undo2,
  Redo2,
} from 'lucide-react';
import {
  useDrillPath,
  useCurrentLevel,
  useCanUndo,
  useCanRedo,
  useHistoryStack,
  useHistoryIndex,
  useDrillStore,
  useIsLoading,
} from '@/hooks/useDrillStore';
import { StateSnapshot } from '@/types/drill';
import { BreadcrumbSkeleton } from '@/components/Skeleton';

export default function Breadcrumb() {
  const path = useDrillPath();
  const currentLevel = useCurrentLevel();
  const canUndo = useCanUndo();
  const canRedo = useCanRedo();
  const historyStack = useHistoryStack();
  const historyIndex = useHistoryIndex();
  const isLoading = useIsLoading();
  const { drillUp, resetDrill, undo, redo, jumpToSnapshot } = useDrillStore();

  const [showHistory, setShowHistory] = useState(false);

  const handleDrillUp = (index: number) => {
    drillUp(index);
  };

  const handleReset = () => {
    resetDrill();
  };

  const handleUndo = () => {
    undo();
  };

  const handleRedo = () => {
    redo();
  };

  const handleJumpToSnapshot = (snapshot: StateSnapshot) => {
    jumpToSnapshot(snapshot.id);
    setShowHistory(false);
  };

  const formatActionLabel = (action: string) => {
    const labels: Record<string, string> = {
      drillDown: '下钻',
      drillUp: '上钻',
      reset: '重置',
      init: '初始化',
      restore: '恢复',
    };
    return labels[action] || action;
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (isLoading) {
    return <BreadcrumbSkeleton />;
  }

  return (
    <div className="bg-slate-800/60 backdrop-blur-sm rounded-2xl p-5 border border-slate-700/50">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-6 bg-gradient-to-b from-cyan-400 to-blue-500 rounded-full" />
          <h3 className="text-lg font-semibold text-white">钻取路径</h3>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleUndo}
            disabled={!canUndo}
            className={`p-2 rounded-lg transition-all duration-200 ${
              canUndo
                ? 'bg-slate-700/80 text-slate-300 hover:bg-slate-600/80 hover:text-white'
                : 'bg-slate-800/50 text-slate-600 cursor-not-allowed'
            }`}
            title="撤销"
          >
            <Undo2 className="w-4 h-4" />
          </button>

          <button
            onClick={handleRedo}
            disabled={!canRedo}
            className={`p-2 rounded-lg transition-all duration-200 ${
              canRedo
                ? 'bg-slate-700/80 text-slate-300 hover:bg-slate-600/80 hover:text-white'
                : 'bg-slate-800/50 text-slate-600 cursor-not-allowed'
            }`}
            title="重做"
          >
            <Redo2 className="w-4 h-4" />
          </button>

          <div className="relative">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className={`p-2 rounded-lg transition-all duration-200 ${
                showHistory
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700/80 text-slate-300 hover:bg-slate-600/80 hover:text-white'
              }`}
              title="历史记录"
            >
              <Clock className="w-4 h-4" />
            </button>

            {showHistory && historyStack.length > 0 && (
              <div className="absolute right-0 top-full mb-2 w-72 bg-slate-800 rounded-xl shadow-xl border border-slate-700 z-50 overflow-hidden">
                <div className="p-3 border-b border-slate-700/50">
                  <h4 className="text-sm font-semibold text-white">历史快照历史记录</h4>
                  <p className="text-xs text-slate-400">
                    共 {historyStack.length} 条记录
                  </p>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {historyStack.slice().reverse().map((snapshot, index) => (
                    <button
                      key={snapshot.id}
                      onClick={() => handleJumpToSnapshot(snapshot)}
                      className="w-full p-3 text-left hover:bg-slate-700/50 transition-colors border-b border-slate-700/30 last:border-b-0"
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className={`text-sm font-medium ${
                            historyStack.length - 1 - index === historyIndex
                              ? 'text-cyan-400'
                              : 'text-slate-300'
                          }`}
                        >
                          {snapshot.path.length > 0
                            ? snapshot.path[snapshot.path.length - 1].name
                            : '全国'}
                        </span>
                        <span className="text-xs px-2 py-0.5 bg-slate-700 rounded text-slate-400">
                          {formatActionLabel(snapshot.action)}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        {formatTime(snapshot.timestamp)} · 层级 {snapshot.currentLevel}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700/80 hover:bg-slate-600/80 text-slate-300 hover:text-white rounded-xl transition-all duration-200 text-sm font-medium group"
          >
            <RotateCcw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" />
            重置
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={handleReset}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all duration-200 ${
            currentLevel === 0
              ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-500/20'
              : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/50 hover:text-white'
          }`}
        >
          <Home className="w-4 h-4" />
          <span className="font-medium">全国</span>
        </button>

        {path.map((node, index) => (
          <div key={node.id} className="flex items-center gap-2">
            <ChevronRight className="w-4 h-4 text-slate-500" />
            <button
              onClick={() => handleDrillUp(index)}
              className={`px-4 py-2 rounded-xl transition-all duration-200 ${
                index === path.length - 1
                  ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-500/20'
                  : 'bg-slate-700/50 text-slate-300 hover:bg-slate-600/50 hover:text-white'
              }`}
            >
              <span className="font-medium">{node.name}</span>
            </button>
          </div>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <span className="text-slate-400">当前层级：</span>
          <span className="text-cyan-400 font-semibold">
            {currentLevel === 0
              ? '全国（省级）'
              : currentLevel === 1
              ? '省级（市级）'
              : '市级（区县）'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-400">钻取深度：</span>
          <span className="text-purple-400 font-semibold">
            {currentLevel} / 2
          </span>
        </div>
      </div>
    </div>
  );
}
