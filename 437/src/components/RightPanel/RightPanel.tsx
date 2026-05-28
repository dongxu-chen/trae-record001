import React, { useState } from 'react';
import { Settings, Code, Play, ChevronLeft, ChevronRight } from 'lucide-react';
import { Properties } from './Properties';
import { CodeEditor } from './CodeEditor';
import { Simulator } from './Simulator';
import { cn } from '../../lib/utils';

type TabType = 'properties' | 'code' | 'simulator';

interface RightPanelProps {
  isCollapsed: boolean;
  onToggle: () => void;
}

export const RightPanel: React.FC<RightPanelProps> = ({ isCollapsed, onToggle }) => {
  const [activeTab, setActiveTab] = useState<TabType>('code');

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'properties', label: '属性', icon: <Settings size={16} /> },
    { id: 'code', label: '代码', icon: <Code size={16} /> },
    { id: 'simulator', label: '模拟', icon: <Play size={16} /> },
  ];

  return (
    <div
      className={cn(
        'h-full bg-slate-900/95 border-l border-slate-700/50 flex flex-col transition-all duration-300',
        isCollapsed ? 'w-12' : 'w-80'
      )}
    >
      {isCollapsed ? (
        <div className="flex flex-col items-center py-3 gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                onToggle();
              }}
              className={cn(
                'p-2 rounded-lg transition-colors',
                activeTab === tab.id
                  ? 'bg-cyan-500/20 text-cyan-400'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
              )}
              title={tab.label}
            >
              {tab.icon}
            </button>
          ))}
          <div className="w-6 h-px bg-slate-700 my-1" />
          <button
            onClick={onToggle}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-colors"
            title="展开面板"
          >
            <ChevronLeft size={16} />
          </button>
        </div>
      ) : (
        <>
          <div className="flex items-center border-b border-slate-700/50">
            <div className="flex-1 flex">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium transition-colors border-b-2 -mb-px',
                    activeTab === tab.id
                      ? 'text-cyan-400 border-cyan-400 bg-cyan-500/10'
                      : 'text-slate-400 border-transparent hover:text-slate-200 hover:bg-slate-800/50'
                  )}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>
            <button
              onClick={onToggle}
              className="p-2 mr-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-colors"
              title="收起面板"
            >
              <ChevronRight size={16} />
            </button>
          </div>

          <div className="flex-1 min-h-0 overflow-hidden">
            {activeTab === 'properties' && <Properties />}
            {activeTab === 'code' && <CodeEditor />}
            {activeTab === 'simulator' && <Simulator />}
          </div>
        </>
      )}
    </div>
  );
};
