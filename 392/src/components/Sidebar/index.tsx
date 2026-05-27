import React from 'react';
import { useIconStore } from '../../store/iconStore';
import { IconLibrary, ViewMode } from '../../types';
import { Search, Grid, List, Download, Upload, Heart, Clock, X } from 'lucide-react';
import { libraryNames } from '../../data/categories';

interface SidebarProps {
  categories: string[];
}

const Sidebar: React.FC<SidebarProps> = ({ categories }) => {
  const {
    currentLibrary,
    setCurrentLibrary,
    selectedCategory,
    setSelectedCategory,
    viewMode,
    setViewMode,
    setShowFavoritesPanel,
    setShowRecentPanel,
    setShowUploadModal,
  } = useIconStore();

  const libraries: IconLibrary[] = ['fontawesome', 'material', 'custom'];

  return (
    <aside className="w-64 bg-[#12121a] border-r border-[#2a2a3a] flex flex-col h-full">
      <div className="p-4 border-b border-[#2a2a3a]">
        <h1 className="text-xl font-bold bg-gradient-to-r from-[#4F46E5] to-[#06B6D4] bg-clip-text text-transparent">
          Icon Browser
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-6">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            图标库
          </h3>
          <div className="space-y-1">
            {libraries.map((lib) => (
              <button
                key={lib}
                onClick={() => {
                  setCurrentLibrary(lib);
                  setSelectedCategory(null);
                }}
                className={`w-full px-3 py-2 rounded-lg text-left text-sm transition-all ${
                  currentLibrary === lib
                    ? 'bg-[#4F46E5]/20 text-[#4F46E5] border border-[#4F46E5]/30'
                    : 'text-gray-400 hover:bg-[#1a1a2a] hover:text-gray-200'
                }`}
              >
                {libraryNames[lib]}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              分类
            </h3>
            {selectedCategory && (
              <button
                onClick={() => setSelectedCategory(null)}
                className="text-xs text-[#4F46E5] hover:text-[#6366F1] flex items-center gap-1"
              >
                <X size={12} />
                清除
              </button>
            )}
          </div>
          <div className="space-y-1">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
                className={`w-full px-3 py-2 rounded-lg text-left text-sm transition-all ${
                  selectedCategory === cat
                    ? 'bg-[#06B6D4]/20 text-[#06B6D4] border border-[#06B6D4]/30'
                    : 'text-gray-400 hover:bg-[#1a1a2a] hover:text-gray-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <div className="mb-6">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            视图模式
          </h3>
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`flex-1 p-2 rounded-lg flex items-center justify-center gap-2 transition-all ${
                viewMode === 'grid'
                  ? 'bg-[#4F46E5]/20 text-[#4F46E5]'
                  : 'text-gray-500 hover:bg-[#1a1a2a]'
              }`}
            >
              <Grid size={16} />
              <span className="text-xs">网格</span>
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`flex-1 p-2 rounded-lg flex items-center justify-center gap-2 transition-all ${
                viewMode === 'list'
                  ? 'bg-[#4F46E5]/20 text-[#4F46E5]'
                  : 'text-gray-500 hover:bg-[#1a1a2a]'
              }`}
            >
              <List size={16} />
              <span className="text-xs">列表</span>
            </button>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-[#2a2a3a] space-y-2">
        <button
          onClick={() => setShowUploadModal(true)}
          className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-[#4F46E5] to-[#06B6D4] text-white text-sm font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
        >
          <Upload size={16} />
          上传图标
        </button>
        <div className="flex gap-2">
          <button
            onClick={() => setShowFavoritesPanel(true)}
            className="flex-1 px-3 py-2 rounded-lg bg-[#1a1a2a] text-gray-400 text-xs hover:text-white hover:bg-[#2a2a3a] transition-all flex items-center justify-center gap-1.5"
          >
            <Heart size={14} />
            收藏
          </button>
          <button
            onClick={() => setShowRecentPanel(true)}
            className="flex-1 px-3 py-2 rounded-lg bg-[#1a1a2a] text-gray-400 text-xs hover:text-white hover:bg-[#2a2a3a] transition-all flex items-center justify-center gap-1.5"
          >
            <Clock size={14} />
            最近
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
