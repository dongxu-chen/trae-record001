import React, { useMemo } from 'react';
import { useIconStore, getFilteredIcons } from '../../store/iconStore';
import { matchByPinyin, matchTagsByPinyin } from '../../utils/pinyin';
import IconCard from '../IconCard';

const IconGrid: React.FC = () => {
  const { selectedIcons, viewMode } = useIconStore();

  const icons = useMemo(() => getFilteredIcons(), []);

  const filteredIcons = useMemo(() => {
    return useIconStore.getState().currentLibrary === 'custom'
      ? useIconStore.getState().uploadedIcons
      : icons;
  }, [icons]);

  const storeIcons = useIconStore((state) => {
    if (state.currentLibrary === 'custom') {
      return state.uploadedIcons;
    }
    let result = [...filteredIcons];
    if (state.selectedCategory) {
      result = result.filter(icon => icon.category === state.selectedCategory);
    }
    if (state.searchQuery.trim()) {
      const query = state.searchQuery.trim();
      result = result.filter(icon => 
        matchByPinyin(icon.name, query) ||
        matchTagsByPinyin(icon.tags, query)
      );
    }
    return result;
  });

  if (storeIcons.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#1a1a2a] flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-400 mb-2">未找到图标</h3>
          <p className="text-sm text-gray-600">支持拼音、首字母搜索，试试其他关键词</p>
        </div>
      </div>
    );
  }

  if (viewMode === 'list') {
    return (
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {storeIcons.map((icon) => (
            <div
              key={icon.id}
              className={`flex items-center gap-4 p-3 rounded-xl transition-all cursor-pointer ${
                selectedIcons.has(icon.id)
                  ? 'bg-[#4F46E5]/20 border border-[#4F46E5]/50'
                  : 'bg-[#12121a] border border-transparent hover:bg-[#1a1a2a]'
              }`}
            >
              <svg
                width={24}
                height={24}
                viewBox="0 0 24 24"
                fill={useIconStore.getState().currentColor}
              >
                <path d={icon.svgPath} />
              </svg>
              <div className="flex-1">
                <p className="text-sm text-gray-200 font-medium">{icon.name}</p>
                <p className="text-xs text-gray-500">{icon.category}</p>
              </div>
              <div className="flex gap-2">
                {icon.tags.slice(0, 2).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 text-xs rounded-full bg-[#1a1a2a] text-gray-500"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
        {storeIcons.map((icon) => (
          <IconCard
            key={icon.id}
            icon={icon}
            isSelected={selectedIcons.has(icon.id)}
            isActive={useIconStore.getState().activeIconId === icon.id}
          />
        ))}
      </div>
    </div>
  );
};

export default IconGrid;
