import React, { useMemo } from 'react';
import { useIconStore, getIconById } from '../../store/iconStore';
import { generateSvgCode, generateJsxCode } from '../../utils/svgUtils';
import { getFilterStyle } from '../../utils/colorFilter';
import { useClipboard } from '../../hooks/useClipboard';
import { Heart, Copy, Check, Download, X, Code } from 'lucide-react';
import ColorPicker from '../ColorPicker';

const DetailPanel: React.FC = () => {
  const {
    activeIconId,
    setActiveIcon,
    currentColor,
    currentSize,
    copyFormat,
    setCopyFormat,
    favorites,
    toggleFavorite,
    addToRecent,
    useFilterMode,
  } = useIconStore();

  const { copied, copyToClipboard } = useClipboard();

  const icon = activeIconId ? getIconById(activeIconId) : null;
  const isFavorite = icon ? !!favorites[icon.id] : false;
  const filterStyle = useMemo(() => getFilterStyle(currentColor), [currentColor]);

  if (!icon) {
    return (
      <div className="w-80 bg-[#12121a] border-l border-[#2a2a3a] flex items-center justify-center p-8">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#1a1a2a] flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-400 mb-2">选择图标</h3>
          <p className="text-sm text-gray-600">点击任意图标查看详情</p>
        </div>
      </div>
    );
  }

  const svgCode = generateSvgCode(icon, currentColor, currentSize);
  const jsxCode = generateJsxCode(icon, currentColor, currentSize);
  const codeToShow = copyFormat === 'svg' ? svgCode : jsxCode;

  const handleCopy = async () => {
    await copyToClipboard(codeToShow);
    addToRecent(icon.id);
  };

  const handleDownload = () => {
    const blob = new Blob([svgCode], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${icon.name}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    addToRecent(icon.id);
  };

  return (
    <div className="w-80 bg-[#12121a] border-l border-[#2a2a3a] flex flex-col">
      <div className="p-4 border-b border-[#2a2a3a] flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200">图标详情</h3>
        <button
          onClick={() => setActiveIcon(null)}
          className="p-1 rounded-md text-gray-500 hover:text-gray-300 hover:bg-[#1a1a2a] transition-all"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="flex flex-col items-center">
          <div
            className="w-24 h-24 rounded-2xl bg-[#1a1a2a] flex items-center justify-center mb-4"
            style={useFilterMode ? filterStyle : {}}
          >
            <svg
              width={currentSize}
              height={currentSize}
              viewBox="0 0 24 24"
              fill={useFilterMode ? '#000' : currentColor}
            >
              <path d={icon.svgPath} />
            </svg>
          </div>
          <h4 className="text-lg font-semibold text-gray-200">{icon.name}</h4>
          <p className="text-sm text-gray-500 mt-1">{icon.library} · {icon.category}</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => toggleFavorite(icon.id)}
            className={`flex-1 px-4 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              isFavorite
                ? 'bg-[#4F46E5]/20 text-[#4F46E5] border border-[#4F46E5]/30'
                : 'bg-[#1a1a2a] text-gray-400 hover:text-white hover:bg-[#2a2a3a]'
            }`}
          >
            <Heart size={16} fill={isFavorite ? '#4F46E5' : 'none'} />
            {isFavorite ? '已收藏' : '收藏'}
          </button>
          <button
            onClick={handleCopy}
            className="flex-1 px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#4F46E5] to-[#06B6D4] text-white text-sm font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
            {copied ? '已复制' : '复制'}
          </button>
        </div>

        <button
          onClick={handleDownload}
          className="w-full px-4 py-2.5 rounded-xl bg-[#1a1a2a] text-gray-300 text-sm font-medium hover:bg-[#2a2a3a] transition-all flex items-center justify-center gap-2"
        >
          <Download size={16} />
          下载 SVG
        </button>

        <ColorPicker />

        <div>
          <div className="flex items-center justify-between mb-3">
            <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              代码
            </h5>
            <div className="flex gap-1">
              <button
                onClick={() => setCopyFormat('svg')}
                className={`px-2 py-1 text-xs rounded-md transition-all ${
                  copyFormat === 'svg'
                    ? 'bg-[#4F46E5]/20 text-[#4F46E5]'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                SVG
              </button>
              <button
                onClick={() => setCopyFormat('jsx')}
                className={`px-2 py-1 text-xs rounded-md transition-all ${
                  copyFormat === 'jsx'
                    ? 'bg-[#4F46E5]/20 text-[#4F46E5]'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                JSX
              </button>
            </div>
          </div>
          <div className="relative">
            <pre className="p-3 rounded-xl bg-[#0a0a12] text-xs text-gray-400 overflow-x-auto max-h-48 border border-[#2a2a3a]">
              <code>{codeToShow}</code>
            </pre>
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 p-1.5 rounded-md bg-[#1a1a2a] text-gray-500 hover:text-white transition-all"
            >
              {copied ? <Check size={12} className="text-green-400" /> : <Code size={12} />}
            </button>
          </div>
        </div>

        <div>
          <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            标签
          </h5>
          <div className="flex flex-wrap gap-2">
            {icon.tags.map((tag) => (
              <span
                key={tag}
                className="px-3 py-1 text-xs rounded-full bg-[#1a1a2a] text-gray-400 border border-[#2a2a3a]"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DetailPanel;
