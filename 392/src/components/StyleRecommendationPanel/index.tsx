import React, { useMemo } from 'react';
import { useIconStore, getFilteredIcons, getAllIcons } from '../../store/iconStore';
import { generateStyleRecommendations, analyzeUserStyleProfile, iconStyles } from '../../utils/styleRecommendation';
import { Sparkles, X, ArrowRight } from 'lucide-react';
import { getIconById } from '../../store/iconStore';

interface StyleRecommendationPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const StyleRecommendationPanel: React.FC<StyleRecommendationPanelProps> = ({ isOpen, onClose }) => {
  const { recent, uploadedIcons, setCurrentLibrary, setActiveIcon } = useIconStore();

  const recommendations = useMemo(() => {
    const recentIconIds = Object.keys(recent).sort((a, b) => recent[b].usedAt - recent[a].usedAt).slice(0, 20);
    const recentIcons = recentIconIds.map(id => getIconById(id)).filter(Boolean);
    
    const usageHistory: Record<string, number> = {};
    recentIconIds.forEach(id => {
      usageHistory[id] = recent[id]?.usedAt ? 1 : 0;
    });
    
    const profile = analyzeUserStyleProfile(recentIcons as any, uploadedIcons, usageHistory);
    return generateStyleRecommendations(profile);
  }, [recent, uploadedIcons]);

  if (!isOpen) return null;

  const handleStyleSelect = (styleId: string) => {
    const allIcons = getAllIcons();
    const style = iconStyles.find(s => s.id === styleId);
    if (!style) return;

    const matchingIcons = allIcons.filter(icon => {
      const iconText = `${icon.name} ${icon.tags.join(' ')} ${icon.category}`.toLowerCase();
      return style.keywords.some(k => iconText.includes(k.toLowerCase()));
    });

    if (matchingIcons.length > 0) {
      setActiveIcon(matchingIcons[0].id);
    }
  };

  return (
    <div className="w-80 bg-[#12121a] border-l border-[#2a2a3a] flex flex-col">
      <div className="p-4 border-b border-[#2a2a3a] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-[#4F46E5]" />
          <h3 className="text-sm font-semibold text-gray-200">风格推荐</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md text-gray-500 hover:text-gray-300 hover:bg-[#1a1a2a] transition-all"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {recommendations.map((rec, index) => (
          <div
            key={rec.style.id}
            className="p-4 rounded-xl bg-[#1a1a2a] hover:bg-[#2a2a3a] cursor-pointer transition-all group"
            onClick={() => handleStyleSelect(rec.style.id)}
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  {index === 0 && (
                    <span className="px-2 py-0.5 text-xs rounded-full bg-[#4F46E5]/20 text-[#4F46E5]">
                      最佳匹配
                    </span>
                  )}
                  <h4 className="text-sm font-semibold text-gray-200">{rec.style.name}</h4>
                </div>
                <p className="text-xs text-gray-500">{rec.style.description}</p>
              </div>
              <span className="text-xs text-[#4F46E5] font-medium">
                {Math.round(rec.confidence * 100)}%
              </span>
            </div>

            <div className="flex gap-1.5 mb-3">
              {rec.style.colorPalette.map((color, i) => (
                <div
                  key={i}
                  className="w-6 h-6 rounded-lg border border-[#2a2a3a]"
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>

            <p className="text-xs text-gray-400 mb-3">{rec.reason}</p>

            <div className="flex flex-wrap gap-1.5">
              {rec.style.keywords.slice(0, 4).map(keyword => (
                <span
                  key={keyword}
                  className="px-2 py-0.5 text-xs rounded-full bg-[#0a0a12] text-gray-500"
                >
                  {keyword}
                </span>
              ))}
            </div>

            <div className="mt-3 pt-3 border-t border-[#2a2a3a] flex items-center justify-between">
              <span className="text-xs text-gray-500">
                {rec.style.roundedness === 'rounded' ? '圆润' : rec.style.roundedness === 'sharp' ? '锐利' : '适中'} · 
                {rec.style.strokeWidth === 'thick' ? '粗线条' : rec.style.strokeWidth === 'thin' ? '细线条' : '中等'}
              </span>
              <ArrowRight size={14} className="text-gray-500 group-hover:text-[#4F46E5] transition-colors" />
            </div>
          </div>
        ))}

        <div className="p-4 rounded-xl bg-[#4F46E5]/5 border border-[#4F46E5]/20">
          <p className="text-xs text-gray-400">
            💡 风格推荐基于您最近使用的图标和上传的自定义图标分析生成
          </p>
        </div>
      </div>
    </div>
  );
};

export default StyleRecommendationPanel;
