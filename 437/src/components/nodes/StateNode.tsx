import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Play, Circle, Square, SplitSquareVertical, History } from 'lucide-react';
import { StateNodeData, nodeTypeConfig } from '../../types';
import { cn } from '../../lib/utils';

const iconMap = {
  initial: Play,
  normal: Circle,
  final: Square,
  parallel: SplitSquareVertical,
  history: History,
};

interface CustomNodeData extends StateNodeData {
  isActive?: boolean;
}

export const StateNode = memo(({ data, selected }: NodeProps<CustomNodeData>) => {
  const config = nodeTypeConfig[data.nodeType];
  const Icon = iconMap[data.nodeType];
  const isActive = data.isActive;

  return (
    <div
      className={cn(
        'relative min-w-[140px] rounded-xl border-2 bg-slate-800/90 backdrop-blur-sm transition-all duration-300',
        selected ? 'ring-2 ring-cyan-400 ring-offset-2 ring-offset-slate-900 scale-105 z-10' : '',
        isActive ? 'ring-2 ring-emerald-400 ring-offset-2 ring-offset-slate-900 scale-105 z-20' : '',
        'hover:shadow-lg hover:shadow-current/20'
      )}
      style={{
        borderColor: isActive ? '#10b981' : config.color,
        boxShadow: isActive
          ? '0 0 30px rgba(16, 185, 129, 0.4), 0 0 60px rgba(16, 185, 129, 0.2)'
          : undefined,
      }}
    >
      {isActive && (
        <div className="absolute -inset-1 rounded-xl bg-emerald-500/20 animate-pulse -z-10" />
      )}

      <Handle
        type="target"
        position={Position.Left}
        className={cn(
          '!w-3 !h-3 !border-2 transition-all duration-200',
          isActive
            ? '!bg-emerald-400 !border-emerald-400 !scale-125'
            : '!bg-slate-700 !border-slate-500 hover:!bg-cyan-400 hover:!border-cyan-400'
        )}
      />

      <div className="p-3 relative">
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-6 h-6 rounded-md flex items-center justify-center transition-all duration-300"
            style={{
              backgroundColor: isActive ? 'rgba(16, 185, 129, 0.2)' : `${config.color}20`,
              color: isActive ? '#10b981' : config.color,
            }}
          >
            <Icon size={14} className={cn(isActive && 'animate-pulse')} />
          </div>
          <span
            className="text-xs font-medium px-2 py-0.5 rounded-full transition-all duration-300"
            style={{
              backgroundColor: isActive ? 'rgba(16, 185, 129, 0.2)' : `${config.color}20`,
              color: isActive ? '#10b981' : config.color,
            }}
          >
            {config.label}
          </span>
          {isActive && (
            <span className="ml-auto flex items-center gap-1 text-xs text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              活动
            </span>
          )}
        </div>
        <div className={cn('text-sm font-semibold truncate transition-colors duration-300', isActive ? 'text-emerald-300' : 'text-slate-100')}>
          {data.label}
        </div>
        {data.description && (
          <div className="text-xs text-slate-400 mt-1 truncate">{data.description}</div>
        )}
        {(data.entry || data.exit) && (
          <div className="mt-2 pt-2 border-t border-slate-700/50 space-y-0.5">
            {data.entry && (
              <div className="text-xs text-emerald-400 truncate">
                ↳ entry: {data.entry}
              </div>
            )}
            {data.exit && (
              <div className="text-xs text-rose-400 truncate">
                ↳ exit: {data.exit}
              </div>
            )}
          </div>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className={cn(
          '!w-3 !h-3 !border-2 transition-all duration-200',
          isActive
            ? '!bg-emerald-400 !border-emerald-400 !scale-125'
            : '!bg-slate-700 !border-slate-500 hover:!bg-cyan-400 hover:!border-cyan-400'
        )}
      />
    </div>
  );
});

StateNode.displayName = 'StateNode';
