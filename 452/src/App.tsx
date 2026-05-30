import { useState } from 'react';
import { Leva } from 'leva';
import { Toolbar } from './components/Editor/Toolbar';
import { ModelLibrary } from './components/Editor/ModelLibrary';
import { Viewport } from './components/Editor/Viewport';
import { PropertyPanel } from './components/Editor/PropertyPanel';
import { SceneTemplateLibrary } from './components/Editor/SceneTemplateLibrary';
import { useSceneStore } from './store/useSceneStore';
import { Box, LayoutTemplate } from 'lucide-react';

function LeftPanel() {
  const [activeTab, setActiveTab] = useState<'models' | 'templates'>('models');

  return (
    <div className="flex">
      <div className="w-10 bg-gray-900 border-r border-gray-700 flex flex-col items-center py-2 gap-1">
        <button
          onClick={() => setActiveTab('models')}
          className={`p-2 rounded transition-all ${
            activeTab === 'models'
              ? 'bg-cyan-500 text-white'
              : 'text-gray-400 hover:bg-gray-700 hover:text-white'
          }`}
          title="模型库"
        >
          <Box size={18} />
        </button>
        <button
          onClick={() => setActiveTab('templates')}
          className={`p-2 rounded transition-all ${
            activeTab === 'templates'
              ? 'bg-cyan-500 text-white'
              : 'text-gray-400 hover:bg-gray-700 hover:text-white'
          }`}
          title="场景模板"
        >
          <LayoutTemplate size={18} />
        </button>
      </div>

      {activeTab === 'models' && <ModelLibrary />}
      {activeTab === 'templates' && <SceneTemplateLibrary />}
    </div>
  );
}

function App() {
  const { isPreviewMode } = useSceneStore();

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-950 overflow-hidden">
      <Toolbar />

      <div className="flex-1 flex overflow-hidden">
        {!isPreviewMode && <LeftPanel />}
        <Viewport />
        {!isPreviewMode && <PropertyPanel />}
      </div>

      <Leva
        theme={{
          colors: {
            accent1: '#00d4ff',
            accent2: '#0099cc',
            accent3: '#006699',
            highlight1: '#2a2a4a',
            highlight2: '#3a3a5a',
            highlight3: '#4a4a6a',
            inputBg: '#1a1a3a',
          },
        }}
        fill={false}
        flat={true}
        oneLineLabels={true}
      />
    </div>
  );
}

export default App;
