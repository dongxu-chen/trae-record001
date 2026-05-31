import { useState, useEffect, useRef } from 'react';
import { Trophy, Gauge, Activity, TrendingUp, Zap } from 'lucide-react';
import { useAppStore, type ActionResult } from '@/store/appStore';
import { cn } from '@/lib/utils';

function getProgressColor(confidence: number): string {
  if (confidence >= 0.8) return 'bg-emerald-400';
  if (confidence >= 0.6) return 'bg-cyan-400';
  if (confidence >= 0.4) return 'bg-yellow-400';
  return 'bg-red-400';
}

function getTextColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-emerald-400';
  if (confidence >= 0.6) return 'text-cyan-400';
  if (confidence >= 0.4) return 'text-yellow-400';
  return 'text-red-400';
}

function getGlowColor(confidence: number): string {
  if (confidence >= 0.8) return 'shadow-emerald-500/30';
  if (confidence >= 0.6) return 'shadow-cyan-500/30';
  if (confidence >= 0.4) return 'shadow-yellow-500/30';
  return 'shadow-red-500/30';
}

export default function ResultPanel() {
  const { topActions, currentFps, latency, connection } = useAppStore();
  const [pulsedIndex, setPulsedIndex] = useState<number | null>(null);
  const prevActionsRef = useRef<ActionResult[]>([]);

  useEffect(() => {
    const prevLabels = prevActionsRef.current.map((a) => a.label);
    const currentLabels = topActions.map((a) => a.label);

    for (let i = 0; i < Math.min(currentLabels.length, 3); i++) {
      if (currentLabels[i] !== prevLabels[i]) {
        setPulsedIndex(i);
        const timer = setTimeout(() => setPulsedIndex(null), 800);
        return () => clearTimeout(timer);
      }
    }

    prevActionsRef.current = topActions;
  }, [topActions]);

  const displayActions = topActions.slice(0, 3);

  while (displayActions.length < 3) {
    displayActions.push({ label: '--', confidence: 0, timestamp: 0 });
  }

  return (
    <div className="w-full h-full bg-gray-900/40 backdrop-blur-xl rounded-2xl border border-gray-700/50 overflow-hidden">
      <div className="p-4 border-b border-gray-700/50 bg-gradient-to-r from-gray-900/80 to-gray-800/50">
        <div className="flex items-center gap-2">
          <Trophy className="w-5 h-5 text-yellow-400" />
          <h3 className="text-lg font-bold text-white">Real-time Results</h3>
          <div
            className={cn(
              'ml-auto w-2 h-2 rounded-full',
              connection.isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
            )}
          />
        </div>
      </div>

      <div className="p-4 space-y-3">
        {displayActions.map((action, index) => (
          <div
            key={`${action.label}-${index}`}
            className={cn(
              'relative p-4 rounded-xl border transition-all duration-300',
              'bg-gray-800/30 backdrop-blur-sm',
              'border-gray-700/50 hover:border-gray-600/50',
              pulsedIndex === index && [
                'animate-pulse',
                'border-yellow-400/50',
                `shadow-lg ${getGlowColor(action.confidence)}`,
              ]
            )}
          >
            <div className="flex items-center gap-3 mb-2">
              <div
                className={cn(
                  'w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm',
                  index === 0 && 'bg-yellow-500/20 text-yellow-400',
                  index === 1 && 'bg-gray-400/20 text-gray-300',
                  index === 2 && 'bg-amber-600/20 text-amber-500'
                )}
              >
                {index + 1}
              </div>
              <span className="flex-1 font-semibold text-white truncate">
                {action.label}
              </span>
              <span
                className={cn(
                  'text-lg font-mono font-bold',
                  getTextColor(action.confidence)
                )}
              >
                {(action.confidence * 100).toFixed(1)}%
              </span>
            </div>
            <div className="relative h-2 bg-gray-700/50 rounded-full overflow-hidden">
              <div
                className={cn(
                  'absolute inset-y-0 left-0 rounded-full transition-all duration-500 ease-out',
                  getProgressColor(action.confidence)
                )}
                style={{ width: `${action.confidence * 100}%` }}
              />
              <div
                className={cn(
                  'absolute inset-y-0 left-0 rounded-full opacity-50 blur-sm transition-all duration-500 ease-out',
                  getProgressColor(action.confidence)
                )}
                style={{ width: `${action.confidence * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 border-t border-gray-700/50 bg-gray-900/30">
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-xl bg-gray-800/30 border border-gray-700/30">
            <div className="flex items-center gap-2 mb-1">
              <Gauge className="w-4 h-4 text-cyan-400" />
              <span className="text-xs text-gray-400">FPS</span>
            </div>
            <span className="text-2xl font-bold font-mono text-cyan-400">
              {currentFps.toFixed(1)}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-gray-800/30 border border-gray-700/30">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-purple-400" />
              <span className="text-xs text-gray-400">Latency</span>
            </div>
            <span className="text-2xl font-bold font-mono text-purple-400">
              {latency.toFixed(0)}
              <span className="text-sm text-gray-500 ml-1">ms</span>
            </span>
          </div>
          <div className="p-3 rounded-xl bg-gray-800/30 border border-gray-700/30">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-gray-400">Connection</span>
            </div>
            <span
              className={cn(
                'text-sm font-semibold',
                connection.isConnected ? 'text-emerald-400' : 'text-red-400'
              )}
            >
              {connection.isConnected
                ? 'Connected'
                : connection.isReconnecting
                ? 'Reconnecting...'
                : 'Disconnected'}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-gray-800/30 border border-gray-700/30">
            <div className="flex items-center gap-2 mb-1">
              <Zap className="w-4 h-4 text-yellow-400" />
              <span className="text-xs text-gray-400">Retry</span>
            </div>
            <span className="text-lg font-bold font-mono text-yellow-400">
              {connection.reconnectAttempts}
              <span className="text-sm text-gray-500">/5</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
