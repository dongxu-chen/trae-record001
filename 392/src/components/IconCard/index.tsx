import React, { useMemo } from 'react';
import { Icon } from '../../types';
import { useIconStore } from '../../store/iconStore';
import { Heart, Copy, Check, Download } from 'lucide-react';
import { useClipboard } from '../../hooks/useClipboard';
import { generateSvgCode } from '../../utils/svgUtils';
import { getFilterStyle } from '../../utils/colorFilter';

interface IconCardProps {
  icon: Icon;
  isSelected: boolean;
  isActive: boolean;
}

const IconCard: React.FC<IconCardProps> = ({ icon, isSelected, isActive }) => {
  const {
    toggleIconSelection,
    setActiveIcon,
    favorites,
    toggleFavorite,
    addToRecent,
    currentColor,
    currentSize,
    useFilterMode,
  } = useIconStore();

  const { copied, copyToClipboard } = useClipboard();
  const isFavorite = !!favorites[icon.id];

  const filterStyle = useMemo(() => getFilterStyle(currentColor), [currentColor]);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const svgCode = generateSvgCode(icon, currentColor, currentSize);
    await copyToClipboard(svgCode);
    addToRecent(icon.id);
  };

  const handleClick = () => {
    setActiveIcon(isActive ? null : icon.id);
  };

  return (
    <div
      onClick={handleClick}
      className={`group relative p-4 rounded-xl cursor-pointer transition-all duration-200 ${
        isSelected
          ? 'bg-[#4F46E5]/20 border-2 border-[#4F46E5]'
          : isActive
          ? 'bg-[#1a1a2a] border-2 border-[#06B6D4]'
          : 'bg-[#12121a] border-2 border-transparent hover:bg-[#1a1a2a] hover:border-[#2a2a3a]'
      }`}
    >
      <div
        className="absolute top-2 left-2 w-4 h-4 rounded border-2 flex items-center justify-center transition-all opacity-0 group-hover:opacity-100"
        style={{
          borderColor: isSelected ? '#4F46E5' : '#3a3a4a',
          backgroundColor: isSelected ? '#4F46E5' : 'transparent',
        }}
        onClick={(e) => {
          e.stopPropagation();
          toggleIconSelection(icon.id);
        }}
      >
        {isSelected && <Check size={10} className="text-white" />}
      </div>

      <button
        onClick={(e) => {
          e.stopPropagation();
          toggleFavorite(icon.id);
        }}
        className={`absolute top-2 right-2 p-1 rounded-md transition-all ${
          isFavorite
            ? 'text-[#4F46E5] opacity-100'
            : 'text-gray-600 opacity-0 group-hover:opacity-100 hover:text-[#4F46E5]'
        }}`}
      >
        <Heart size={14} fill={isFavorite ? '#4F46E5' : 'none'} />
      </button>

      <div className="flex flex-col items-center justify-center py-4">
        <div
          className="relative"
          style={useFilterMode ? filterStyle : {}}
        >
          <svg
            width={currentSize}
            height={currentSize}
            viewBox="0 0 24 24"
            fill={useFilterMode ? '#000' : currentColor}
            className="transition-all duration-200 group-hover:scale-110"
          >
            <path d={icon.svgPath} />
          </svg>
        </div>
      </div>

      <div className="text-center">
        <p className="text-sm text-gray-300 truncate font-medium">{icon.name}</p>
        <p className="text-xs text-gray-600 mt-0.5">{icon.category}</p>
      </div>

      <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1 opacity-0 group-hover:opacity-100 transition-all">
        <button
          onClick={handleCopy}
          className="p-1.5 rounded-md bg-[#2a2a3a] text-gray-400 hover:text-white hover:bg-[#3a3a4a] transition-all"
          title="复制SVG"
        >
          {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            const svgContent = generateSvgCode(icon, currentColor, currentSize);
            const blob = new Blob([svgContent], { type: 'image/svg+xml' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${icon.name}.svg`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            addToRecent(icon.id);
          }}
          className="p-1.5 rounded-md bg-[#2a2a3a] text-gray-400 hover:text-white hover:bg-[#3a3a4a] transition-all"
          title="下载SVG"
        >
          <Download size={12} />
        </button>
      </div>
    </div>
  );
};

export default IconCard;
