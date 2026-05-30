import React, { useState } from 'react';
import { Settings, Type, Move, Wand2, LayoutGrid, ChevronRight, ChevronLeft, Radio, Monitor } from 'lucide-react';
import { TextEditor } from './TextEditor';
import { FontSettings } from './FontSettings';
import { ScrollSettings } from './ScrollSettings';
import { EffectSettings } from './EffectSettings';
import { PresetTemplates } from './PresetTemplates';
import { RemoteSync } from './RemoteSync';
import { MultiScreenSync } from './MultiScreenSync';

type TabId = 'text' | 'font' | 'scroll' | 'effect' | 'preset' | 'remote' | 'sync';

const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'text', label: '文字', icon: <Type className="w-4 h-4" /> },
  { id: 'font', label: '样式', icon: <Settings className="w-4 h-4" /> },
  { id: 'scroll', label: '滚动', icon: <Move className="w-4 h-4" /> },
  { id: 'effect', label: '特效', icon: <Wand2 className="w-4 h-4" /> },
  { id: 'preset', label: '模板', icon: <LayoutGrid className="w-4 h-4" /> },
  { id: 'remote', label: '推送', icon: <Radio className="w-4 h-4" /> },
  { id: 'sync', label: '同步', icon: <Monitor className="w-4 h-4" /> }
];

export const ControlPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('text');
  const [isCollapsed, setIsCollapsed] = useState(false);

  const renderTabContent = () => {
    switch (activeTab) {
      case 'text':
        return <TextEditor />;
      case 'font':
        return <FontSettings />;
      case 'scroll':
        return <ScrollSettings />;
      case 'effect':
        return <EffectSettings />;
      case 'preset':
        return <PresetTemplates />;
      case 'remote':
        return <RemoteSync />;
      case 'sync':
        return <MultiScreenSync />;
      default:
        return null;
    }
  };

  if (isCollapsed) {
    return (
      <div className="h-full bg-gray-900/80 backdrop-blur-xl border-l border-gray-700 flex flex-col">
        <div className="p-3 border-b border-gray-700">
          <button
            onClick={() => setIsCollapsed(false)}
            className="w-full p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-all"
            title="展开控制面板"
          >
            <ChevronLeft className="w-5 h-5 mx-auto" />
          </button>
        </div>
        <div className="flex-1 p-2 space-y-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setIsCollapsed(false);
              }}
              className={`w-full p-3 rounded-lg transition-all ${
                activeTab === tab.id
                  ? 'bg-cyan-500/20 text-cyan-400'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}
              title={tab.label}
            >
              {tab.icon}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-80 bg-gray-900/80 backdrop-blur-xl border-l border-gray-700 flex flex-col">
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Settings className="w-5 h-5 text-cyan-400" />
          控制面板
        </h2>
        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-all"
          title="收起"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      <div className="flex border-b border-gray-700 overflow-x-auto custom-scrollbar">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-shrink-0 px-2.5 py-3 text-xs font-medium transition-all border-b-2 flex items-center justify-center gap-1 ${
              activeTab === tab.id
                ? 'text-cyan-400 border-cyan-400 bg-cyan-500/10'
                : 'text-gray-400 border-transparent hover:text-gray-200 hover:bg-gray-800/50'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
        {renderTabContent()}
      </div>

      <div className="p-3 border-t border-gray-700">
        <div className="text-xs text-center text-gray-500">
          LED 字幕滚动组件 · v2.0
        </div>
      </div>
    </div>
  );
};
