import React from 'react';
import { Search, X } from 'lucide-react';
import { useIconStore } from '../../store/iconStore';

const SearchBar: React.FC = () => {
  const { searchQuery, setSearchQuery, selectedIcons, clearSelection, currentColor, currentSize } = useIconStore();

  return (
    <div className="flex items-center gap-4 p-4 bg-[#12121a] border-b border-[#2a2a3a]">
      <div className="flex-1 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
        <input
          type="text"
          placeholder="搜索图标名称或标签..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-[#1a1a2a] border border-[#2a2a3a] text-gray-200 placeholder-gray-500 focus:outline-none focus:border-[#4F46E5]/50 focus:ring-1 focus:ring-[#4F46E5]/30 transition-all"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {selectedIcons.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-[#4F46E5]/20 border border-[#4F46E5]/30">
          <span className="text-sm text-[#4F46E5]">
            已选择 {selectedIcons.size} 个图标
          </span>
          <button
            onClick={clearSelection}
            className="text-xs text-gray-400 hover:text-white transition-colors"
          >
            清除
          </button>
        </div>
      )}

      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span>颜色:</span>
        <div
          className="w-6 h-6 rounded-full border-2 border-[#2a2a3a]"
          style={{ backgroundColor: currentColor }}
        />
        <span>大小:</span>
        <span className="text-gray-400">{currentSize}px</span>
      </div>
    </div>
  );
};

export default SearchBar;
