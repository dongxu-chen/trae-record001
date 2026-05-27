import React, { useState, useMemo } from 'react';
import { Sparkles } from 'lucide-react';
import ThemeCard from '@/components/ThemeCard';
import { recommendedThemes, themeCategories } from '@/utils/recommendedThemes';
import { useThemeActions } from '@/store/useThemeStore';
import type { ThemeCategory } from '@/types/theme';
import { CollapsibleSection } from './ColorSection';
import './ThemeSections.less';

const ThemeRecommendations: React.FC = () => {
  const { applyRecommendedTheme } = useThemeActions();
  const [activeCategory, setActiveCategory] = useState<ThemeCategory | 'all'>('all');

  const filteredThemes = useMemo(() => {
    if (activeCategory === 'all') {
      return recommendedThemes;
    }
    return recommendedThemes.filter((t) => t.category === activeCategory);
  }, [activeCategory]);

  return (
    <CollapsibleSection
      title="主题推荐"
      icon={<Sparkles size={16} />}
      defaultOpen={false}
    >
      <div className="category-tabs">
        {themeCategories.map((cat) => (
          <button
            key={cat.value}
            className={`category-tab ${activeCategory === cat.value ? 'active' : ''}`}
            onClick={() => setActiveCategory(cat.value as ThemeCategory | 'all')}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <div className="theme-grid">
        {filteredThemes.map((theme) => (
          <ThemeCard
            key={theme.id}
            theme={theme}
            onApply={() => applyRecommendedTheme(theme)}
            showActions={false}
            isSaved={false}
          />
        ))}
      </div>

      <p className="section-hint">
        点击「应用」按钮一键替换当前主题配置
      </p>
    </CollapsibleSection>
  );
};

export default React.memo(ThemeRecommendations);
