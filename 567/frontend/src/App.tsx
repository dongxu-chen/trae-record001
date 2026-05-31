import { useState } from 'react';
import { ChevronLeft, ChevronRight, Download, MapPin } from 'lucide-react';
import MapView from './components/Map/MapView';
import AnimationControlBar from './components/Map/AnimationControlBar';
import PhotoPanel from './components/PhotoPanel/PhotoPanel';
import TrackPanel from './components/TrackPanel/TrackPanel';
import ExportPanel from './components/ExportPanel/ExportPanel';
import { useStore } from './store/useStore';

function App() {
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [showExportPanel, setShowExportPanel] = useState(false);
  const { photos, tracks, privacy } = useStore();

  return (
    <div className="w-full h-screen flex bg-gray-100 overflow-hidden">
      <div 
        className={`h-full bg-white shadow-lg transition-all duration-300 flex flex-col ${
          leftPanelOpen ? 'w-80' : 'w-0 overflow-hidden'
        }`}
      >
        <PhotoPanel />
      </div>
      
      {leftPanelOpen && (
        <button
          onClick={() => setLeftPanelOpen(false)}
          className="absolute left-80 top-1/2 -translate-y-1/2 z-[1000] bg-white shadow-md rounded-r-lg p-1 hover:bg-gray-50 transition-colors"
        >
          <ChevronLeft size={20} className="text-gray-600" />
        </button>
      )}
      
      <div className="flex-1 relative flex flex-col">
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] bg-white/90 backdrop-blur-sm rounded-full shadow-lg px-6 py-2 flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <MapPin size={16} className="text-accent-500" />
            <span className="font-medium text-gray-700">
              {photos.filter(p => p.matchedGps || p.manualGps || p.originalGps).length} / {photos.length}
            </span>
            <span className="text-gray-400">已标记</span>
          </div>
          <div className="w-px h-4 bg-gray-300" />
          <div className="text-sm text-gray-500">
            {tracks.length} 条轨迹
          </div>
          {privacy.enabled && (
            <>
              <div className="w-px h-4 bg-gray-300" />
              <div className="text-sm text-orange-500 flex items-center gap-1">
                🔒 隐私保护已开启
              </div>
            </>
          )}
        </div>
        
        <div className="flex-1">
          <MapView />
        </div>
        
        <div className="absolute bottom-16 left-1/2 -translate-x-1/2 z-[1000] w-[calc(100%-2rem)] max-w-4xl">
          <AnimationControlBar />
        </div>
        
        <button
          onClick={() => setShowExportPanel(!showExportPanel)}
          className="absolute bottom-4 right-4 z-[1000] bg-gradient-to-r from-warning-500 to-warning-600 text-white rounded-full shadow-lg px-5 py-3 flex items-center gap-2 hover:shadow-xl transition-all hover:scale-105"
        >
          <Download size={18} />
          <span className="font-medium">导出</span>
        </button>
        
        {showExportPanel && (
          <div className="absolute bottom-16 right-4 z-[1000] w-80">
            <ExportPanel />
          </div>
        )}
        
        {!leftPanelOpen && (
          <button
            onClick={() => setLeftPanelOpen(true)}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-[1000] bg-white shadow-md rounded-r-lg p-1 hover:bg-gray-50 transition-colors"
          >
            <ChevronRight size={20} className="text-gray-600" />
          </button>
        )}
        
        {!rightPanelOpen && (
          <button
            onClick={() => setRightPanelOpen(true)}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-[1000] bg-white shadow-md rounded-l-lg p-1 hover:bg-gray-50 transition-colors"
          >
            <ChevronLeft size={20} className="text-gray-600" />
          </button>
        )}
      </div>
      
      {rightPanelOpen && (
        <button
          onClick={() => setRightPanelOpen(false)}
          className="absolute right-80 top-1/2 -translate-y-1/2 z-[1000] bg-white shadow-md rounded-l-lg p-1 hover:bg-gray-50 transition-colors"
        >
          <ChevronRight size={20} className="text-gray-600" />
        </button>
      )}
      
      <div 
        className={`h-full bg-white shadow-lg transition-all duration-300 flex flex-col ${
          rightPanelOpen ? 'w-80' : 'w-0 overflow-hidden'
        }`}
      >
        <TrackPanel />
      </div>
    </div>
  );
}

export default App;
