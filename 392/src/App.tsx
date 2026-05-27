import { useState } from 'react';
import { useIconStore, getFilteredIcons } from './store/iconStore';
import { categories } from './data/categories';
import { downloadMultipleIcons } from './utils/download';
import Sidebar from './components/Sidebar';
import SearchBar from './components/SearchBar';
import IconGrid from './components/IconGrid';
import DetailPanel from './components/DetailPanel';
import RightPanel from './components/RightPanel';
import UploadModal from './components/UploadModal';
import ProgressBar from './components/ProgressBar';
import BrandRecognitionModal from './components/BrandRecognitionModal';
import StyleRecommendationPanel from './components/StyleRecommendationPanel';
import ReplacementPanel from './components/ReplacementPanel';
import { Download, Heart, Clock, Search, Sparkles, AlertTriangle } from 'lucide-react';

function App() {
  const {
    currentLibrary,
    selectedIcons,
    clearSelection,
    currentColor,
    currentSize,
    showFavoritesPanel,
    showRecentPanel,
    setShowFavoritesPanel,
    setShowRecentPanel,
    activeIconId,
    downloadProgress,
    isDownloading,
    setDownloadProgress,
    setIsDownloading,
    showBrandRecognitionModal,
    setShowBrandRecognitionModal,
    showStylePanel,
    setShowStylePanel,
    showReplacementPanel,
    setShowReplacementPanel,
  } = useIconStore();

  const [showDetailPanel, setShowDetailPanel] = useState(true);

  const iconCategories = categories[currentLibrary] || [];

  const handleBatchDownload = async () => {
    const icons = getFilteredIcons().filter(icon => selectedIcons.has(icon.id));
    if (icons.length > 0) {
      setIsDownloading(true);
      setDownloadProgress(0);
      
      await downloadMultipleIcons(icons, currentColor, currentSize, (progress) => {
        setDownloadProgress(progress.percent);
      });
      
      setTimeout(() => {
        setIsDownloading(false);
        setDownloadProgress(0);
        clearSelection();
      }, 1500);
    }
  };

  return (
    <div className="h-screen flex bg-[#0a0a12] text-gray-100 overflow-hidden">
      <Sidebar categories={iconCategories} />

      <main className="flex-1 flex flex-col min-w-0">
        <SearchBar />

        <div className="px-4 py-2 bg-[#12121a] border-b border-[#2a2a3a] flex items-center gap-2 overflow-x-auto">
          <button
            onClick={() => setShowBrandRecognitionModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1a1a2a] text-gray-400 hover:text-white hover:bg-[#2a2a3a] transition-all text-xs whitespace-nowrap"
          >
            <Search size={14} />
            品牌识别
          </button>
          <button
            onClick={() => setShowStylePanel(!showStylePanel)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all text-xs whitespace-nowrap ${
              showStylePanel
                ? 'bg-[#4F46E5]/20 text-[#4F46E5] border border-[#4F46E5]/30'
                : 'bg-[#1a1a2a] text-gray-400 hover:text-white hover:bg-[#2a2a3a]'
            }`}
          >
            <Sparkles size={14} />
            风格推荐
          </button>
          <button
            onClick={() => setShowReplacementPanel(!showReplacementPanel)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all text-xs whitespace-nowrap ${
              showReplacementPanel
                ? 'bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/30'
                : 'bg-[#1a1a2a] text-gray-400 hover:text-white hover:bg-[#2a2a3a]'
            }`}
          >
            <AlertTriangle size={14} />
            替换建议
          </button>
        </div>

        {selectedIcons.size > 0 && (
          <div className="px-4 py-2 bg-[#4F46E5]/10 border-b border-[#4F46E5]/20 flex items-center justify-between">
            <span className="text-sm text-[#4F46E5]">
              已选择 {selectedIcons.size} 个图标
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={clearSelection}
                className="px-3 py-1.5 text-xs rounded-lg bg-[#1a1a2a] text-gray-400 hover:text-white transition-all"
              >
                清除选择
              </button>
              <button
                onClick={handleBatchDownload}
                disabled={isDownloading}
                className="px-4 py-1.5 text-xs rounded-lg bg-gradient-to-r from-[#4F46E5] to-[#06B6D4] text-white font-medium hover:opacity-90 transition-opacity flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download size={12} />
                批量下载
              </button>
            </div>
          </div>
        )}

        <div className="flex-1 flex min-h-0">
          <IconGrid />
        </div>
      </main>

      {activeIconId && showDetailPanel && (
        <DetailPanel />
      )}

      {showFavoritesPanel && (
        <RightPanel
          type="favorites"
          onClose={() => setShowFavoritesPanel(false)}
        />
      )}

      {showRecentPanel && (
        <RightPanel
          type="recent"
          onClose={() => setShowRecentPanel(false)}
        />
      )}

      {showStylePanel && (
        <StyleRecommendationPanel
          isOpen={showStylePanel}
          onClose={() => setShowStylePanel(false)}
        />
      )}

      {showReplacementPanel && (
        <ReplacementPanel
          isOpen={showReplacementPanel}
          onClose={() => setShowReplacementPanel(false)}
        />
      )}

      <UploadModal />
      <BrandRecognitionModal
        isOpen={showBrandRecognitionModal}
        onClose={() => setShowBrandRecognitionModal(false)}
      />

      <ProgressBar progress={downloadProgress} isDownloading={isDownloading} />

      <div className="fixed bottom-4 right-4 flex flex-col gap-2">
        {!showFavoritesPanel && (
          <button
            onClick={() => setShowFavoritesPanel(true)}
            className="w-12 h-12 rounded-full bg-[#12121a] border border-[#2a2a3a] text-gray-400 hover:text-[#4F46E5] hover:border-[#4F46E5]/30 transition-all flex items-center justify-center shadow-lg"
          >
            <Heart size={20} />
          </button>
        )}
        {!showRecentPanel && (
          <button
            onClick={() => setShowRecentPanel(true)}
            className="w-12 h-12 rounded-full bg-[#12121a] border border-[#2a2a3a] text-gray-400 hover:text-[#06B6D4] hover:border-[#06B6D4]/30 transition-all flex items-center justify-center shadow-lg"
          >
            <Clock size={20} />
          </button>
        )}
      </div>
    </div>
  );
}

export default App;
