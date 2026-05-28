import { useEffect, useState, useMemo, useCallback } from 'react';
import { X, Search, Copy, Star, TrendingUp, Filter, Sparkles } from 'lucide-react';
import { useEditorStore } from '@/store/useEditorStore';
import {
  formulaTemplates,
  templateCategories,
  searchTemplates,
  getTemplatesByCategory,
  getPopularTemplates,
  renderTemplatePreview,
  difficultyLabels,
  type FormulaTemplate,
} from '@/utils/formulaTemplates';

function TemplateCard({
  template,
  onInsert,
}: {
  template: FormulaTemplate;
  onInsert: (latex: string) => void;
}) {
  const [hovered, setHovered] = useState(false);
  const diffInfo = difficultyLabels[template.difficulty];

  return (
    <div
      className="p-3 bg-bg-tertiary rounded-lg cursor-pointer hover:bg-accent/10 transition-all group relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => onInsert(template.latex)}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <div className="text-xs font-medium text-text-primary truncate pr-12">{template.title}</div>
          <div className="text-[10px] text-text-muted mt-0.5 line-clamp-1">{template.description}</div>
        </div>
        <div className={`text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0 ${diffInfo.color}`}>
          {diffInfo.label}
        </div>
      </div>

      <div
        className="katex-preview overflow-hidden text-sm p-2 bg-bg-primary rounded min-h-[50px] flex items-center justify-center"
        dangerouslySetInnerHTML={{ __html: renderTemplatePreview(template.latex) }}
      />

      <div className="flex items-center justify-between mt-2">
        <div className="flex items-center gap-1.5">
          <Star size={10} className="text-warning fill-warning" />
          <span className="text-[10px] text-text-muted">{template.usageCount}</span>
        </div>
        <div className="flex flex-wrap gap-1">
          {template.tags.slice(0, 2).map((tag) => (
            <span key={tag} className="text-[9px] text-text-muted bg-bg-tertiary/50 px-1 py-0.5 rounded">
              {tag}
            </span>
          ))}
        </div>
      </div>

      {hovered && (
        <div className="absolute inset-0 bg-bg-primary/90 rounded-lg flex items-center justify-center animate-fade-in">
          <button
            onClick={(e) => { e.stopPropagation(); onInsert(template.latex); }}
            className="flex items-center gap-1.5 px-4 py-2 bg-accent text-bg-primary text-sm font-medium rounded-lg hover:bg-accent-hover transition-colors"
          >
            <Copy size={14} />
            一键插入
          </button>
        </div>
      )}
    </div>
  );
}

export default function TemplateMarketplace() {
  const { showTemplateMarketplace, toggleTemplateMarketplace, setLatex } = useEditorStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'popular' | 'title' | 'difficulty'>('popular');
  const [activeTab, setActiveTab] = useState<'market' | 'popular'>('market');

  useEffect(() => {
    if (showTemplateMarketplace) {
      setSearchQuery('');
      setActiveCategory('all');
    }
  }, [showTemplateMarketplace]);

  const displayTemplates = useMemo(() => {
    let templates: FormulaTemplate[] = [];

    if (activeTab === 'popular') {
      templates = getPopularTemplates(20);
    } else if (searchQuery) {
      templates = searchTemplates(searchQuery);
    } else if (activeCategory === 'all') {
      templates = formulaTemplates;
    } else {
      templates = getTemplatesByCategory(activeCategory);
    }

    if (sortBy === 'popular') {
      templates = [...templates].sort((a, b) => b.usageCount - a.usageCount);
    } else if (sortBy === 'title') {
      templates = [...templates].sort((a, b) => a.title.localeCompare(b.title, 'zh-CN'));
    } else if (sortBy === 'difficulty') {
      const order = { basic: 0, intermediate: 1, advanced: 2 };
      templates = [...templates].sort((a, b) => order[a.difficulty] - order[b.difficulty]);
    }

    return templates;
  }, [activeTab, searchQuery, activeCategory, sortBy]);

  const handleInsert = useCallback((latex: string) => {
    setLatex(latex);
    toggleTemplateMarketplace();
  }, [setLatex, toggleTemplateMarketplace]);

  if (!showTemplateMarketplace) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 animate-fade-in" onClick={toggleTemplateMarketplace}>
      <div
        className="bg-bg-secondary rounded-xl shadow-2xl w-[820px] max-h-[85vh] animate-scale-in overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-border-custom shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-accent" />
            <span className="text-sm font-medium text-text-primary">公式模板市场</span>
            <span className="text-xs text-text-muted">共 {formulaTemplates.length} 个模板</span>
          </div>
          <button onClick={toggleTemplateMarketplace} className="p-1 text-text-muted hover:text-text-primary transition-colors rounded hover:bg-bg-tertiary">
            <X size={16} />
          </button>
        </div>

        <div className="px-5 py-3 border-b border-border-custom space-y-3 shrink-0">
          <div className="flex gap-1 bg-bg-tertiary rounded-lg p-0.5 w-fit">
            <button
              onClick={() => setActiveTab('market')}
              className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded-md transition-colors ${
                activeTab === 'market'
                  ? 'bg-accent text-bg-primary font-medium'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <Filter size={12} />
              全部分类
            </button>
            <button
              onClick={() => setActiveTab('popular')}
              className={`flex items-center gap-1 px-3 py-1.5 text-xs rounded-md transition-colors ${
                activeTab === 'popular'
                  ? 'bg-accent text-bg-primary font-medium'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              <TrendingUp size={12} />
              热门排行
            </button>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-bg-tertiary rounded-lg px-3 py-1.5 flex-1">
              <Search size={14} className="text-text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索公式模板..."
                className="bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none flex-1"
              />
            </div>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              className="bg-bg-tertiary text-sm text-text-primary rounded-lg px-3 py-1.5 outline-none border border-border-custom focus:border-accent cursor-pointer"
            >
              <option value="popular">按使用量排序</option>
              <option value="title">按名称排序</option>
              <option value="difficulty">按难度排序</option>
            </select>
          </div>

          {activeTab === 'market' && (
            <div className="flex flex-wrap gap-1">
              <button
                onClick={() => setActiveCategory('all')}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  activeCategory === 'all'
                    ? 'bg-accent text-bg-primary font-medium'
                    : 'bg-bg-tertiary text-text-secondary hover:text-text-primary'
                }`}
              >
                全部
              </button>
              {templateCategories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className={`flex items-center gap-1 px-2.5 py-1 text-xs rounded-md transition-colors ${
                    activeCategory === cat.id
                      ? 'bg-accent text-bg-primary font-medium'
                      : 'bg-bg-tertiary text-text-secondary hover:text-text-primary'
                  }`}
                  title={cat.description}
                >
                  <span className="text-xs">{cat.icon}</span>
                  {cat.name}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 scrollbar-thin">
          {activeTab === 'popular' && !searchQuery && (
            <div className="mb-4 p-3 bg-accent/5 border border-accent/20 rounded-lg">
              <div className="flex items-center gap-2 text-xs text-accent font-medium mb-2">
                <TrendingUp size={12} />
                最受欢迎公式 TOP 10
              </div>
              <div className="text-[11px] text-text-muted">
                根据社区使用次数排名，涵盖代数、微积分、物理等核心领域
              </div>
            </div>
          )}

          {displayTemplates.length === 0 ? (
            <div className="text-center text-text-muted text-sm py-16">
              没有找到匹配的公式模板
              <div className="text-xs text-text-muted/70 mt-1">尝试更换搜索关键词或分类</div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {displayTemplates.map((template) => (
                <TemplateCard key={template.id} template={template} onInsert={handleInsert} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
