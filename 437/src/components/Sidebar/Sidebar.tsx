import React from 'react';
import { Play, Circle, Square, SplitSquareVertical, History, ChevronLeft, ChevronRight } from 'lucide-react';
import { NodeType, nodeTypeConfig } from '../../types';
import { cn } from '../../lib/utils';

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
}

const nodeTypes: { type: NodeType; icon: React.ReactNode; description: string }[] = [
  { type: 'initial', icon: <Play size={18} />, description: '状态机入口点' },
  { type: 'normal', icon: <Circle size={18} />, description: '标准状态节点' },
  { type: 'final', icon: <Square size={18} />, description: '状态机终止点' },
  { type: 'parallel', icon: <SplitSquareVertical size={18} />, description: '并行执行状态' },
  { type: 'history', icon: <History size={18} />, description: '历史状态恢复' },
];

export const Sidebar: React.FC<SidebarProps> = ({ isCollapsed, onToggle }) => {
  const onDragStart = (event: React.DragEvent, nodeType: NodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      className={cn(
        'h-full bg-slate-900/95 border-r border-slate-700/50 flex flex-col transition-all duration-300',
        isCollapsed ? 'w-14' : 'w-56'
      )}
    >
      <div className="flex items-center justify-between p-3 border-b border-slate-700/50">
        {!isCollapsed && (
          <span className="text-sm font-semibold text-slate-200">状态节点</span>
        )}
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors"
        >
          {isCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <div className="flex-1 p-2 overflow-y-auto">
        <div className="space-y-1.5">
          {nodeTypes.map(({ type, icon, description }) => (
            <div
              key={type}
              draggable
              onDragStart={(e) => onDragStart(e, type)}
              className={cn(
                'group cursor-grab active:cursor-grabbing rounded-lg border transition-all duration-200',
                'hover:shadow-lg hover:shadow-current/20',
                isCollapsed ? 'p-2.5 flex justify-center' : 'p-3',
                nodeTypeConfig[type].bgColor,
                'border-current/30 hover:border-current/60'
              )}
              style={{ color: nodeTypeConfig[type].color }}
            >
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-md bg-current/10 flex items-center justify-center">
                  {icon}
                </div>
                {!isCollapsed && (
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate">{nodeTypeConfig[type].label}</div>
                    <div className="text-xs opacity-70 truncate">{description}</div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {!isCollapsed && (
          <div className="mt-6 p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
            <div className="text-xs font-medium text-slate-300 mb-2">操作提示</div>
            <ul className="text-xs text-slate-400 space-y-1">
              <li>• 拖拽节点到画布</li>
              <li>• 点击节点连接转移</li>
              <li>• 选中节点编辑属性</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
