import { useEffect, useState, useCallback, useMemo } from 'react';
import { X, Trash2, Search, Copy, Plus, Sparkles } from 'lucide-react';
import katex from 'katex';
import { useEditorStore } from '@/store/useEditorStore';
import { getAllFormulas, deleteFormula, type Formula } from '@/db/database';
import { findSimilarFormulas, getSimilarityLabel } from '@/utils/formulaSimilarity';

function FormulaCard({ formula, onLoad, onDelete }: { formula: Formula; onLoad: (latex: string) => void; onDelete: (id: number) => void }) {
  const [hovered, setHovered] = useState(false);
  let renderedHtml = '';
  try {
    renderedHtml = katex.renderToString(formula.latex, { displayMode: true, throwOnError: false });
  } catch {
    renderedHtml = `<span style="color:#EF4444">渲染失败</span>`;
  }

  return (
    <div
      className="p-3 bg-bg-tertiary rounded-lg cursor-pointer hover:bg-accent/10 transition-all group"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => onLoad(formula.latex)}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-text-primary truncate max-w-[140px]">{formula.title}</span>
        <div className={`flex items-center gap-1 transition-opacity ${hovered ? 'opacity-100' : 'opacity-0'}`}>
          <button
            onClick={(e) => { e.stopPropagation(); onLoad(formula.latex); }}
            className="p-1 text-text-muted hover:text-accent rounded transition-colors"
            title="加载"
          >
            <Copy size={12} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); if (formula.id) onDelete(formula.id); }}
            className="p-1 text-text-muted hover:text-danger rounded transition-colors"
            title="删除"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>
      <div
        className="katex-preview overflow-hidden text-sm p-1 bg-bg-primary rounded"
        dangerouslySetInnerHTML={{ __html: renderedHtml }}
      />
      <div className="mt-1.5 text-[10px] text-text-muted">
        {formula.category} · {new Date(formula.updatedAt).toLocaleDateString('zh-CN')}
      </div>
    </div>
  );
}

function SimilarFormulaCard({
  formula,
  similarity,
  onLoad,
}: {
  formula: Formula;
  similarity: number;
  onLoad: (latex: string) => void;
}) {
  let renderedHtml = '';
  try {
    renderedHtml = katex.renderToString(formula.latex, { displayMode: true, throwOnError: false });
  } catch {
    renderedHtml = `<span style="color:#EF4444">渲染失败</span>`;
  }

  const simLabel = getSimilarityLabel(similarity);
  const simPercent = Math.round(similarity * 100);

  return (
    <div
      className="p-2.5 bg-bg-tertiary/60 rounded-lg cursor-pointer hover:bg-accent/10 transition-all border border-accent/30"
      onClick={() => onLoad(formula.latex)}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[11px] font-medium text-text-primary truncate">{formula.title}</span>
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${simLabel.color} bg-opacity-20`}>
          {simPercent}% 相似
        </span>
      </div>
      <div
        className="katex-preview overflow-hidden text-[11px] p-1 bg-bg-primary rounded"
        dangerouslySetInnerHTML={{ __html: renderedHtml }}
      />
      <div className="mt-1 text-[9px] text-text-muted">点击复用此公式</div>
    </div>
  );
}

export default function FormulaLibrary() {
  const { showFormulaLibrary, toggleFormulaLibrary, setLatex, latex } = useEditorStore();
  const [formulas, setFormulas] = useState<Formula[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [saveTitle, setSaveTitle] = useState('');
  const [showSaveInput, setShowSaveInput] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'similar'>('all');

  const loadFormulas = useCallback(async () => {
    const all = await getAllFormulas();
    setFormulas(all);
  }, []);

  useEffect(() => {
    if (showFormulaLibrary) {
      loadFormulas();
    }
  }, [showFormulaLibrary, loadFormulas]);

  const similarFormulas = useMemo(() => {
    if (!latex.trim() || activeTab !== 'similar') return [];
    return findSimilarFormulas(latex, formulas, 0.35, 5);
  }, [latex, formulas, activeTab]);

  const handleLoad = useCallback((loadedLatex: string) => {
    setLatex(loadedLatex);
  }, [setLatex]);

  const handleDelete = useCallback(async (id: number) => {
    await deleteFormula(id);
    loadFormulas();
  }, [loadFormulas]);

  const handleSave = useCallback(async () => {
    if (!latex.trim() || !saveTitle.trim()) return;
    const { saveFormula } = await import('@/db/database');
    await saveFormula({
      title: saveTitle,
      latex,
      category: '通用',
      thumbnail: '',
      createdAt: new Date(),
      updatedAt: new Date(),
    });
    setSaveTitle('');
    setShowSaveInput(false);
    loadFormulas();
  }, [latex, saveTitle, loadFormulas]);

  const filtered = formulas.filter(
    (f) =>
      f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.latex.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  if (!showFormulaLibrary) return null;

  return (
    <div className="fixed right-0 top-0 bottom-0 w-80 bg-bg-secondary border-l border-border-custom z-40 animate-slide-in-right flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-custom">
        <span className="text-sm font-medium text-text-primary">公式库</span>
        <button onClick={toggleFormulaLibrary} className="p-1 text-text-muted hover:text-text-primary rounded hover:bg-bg-tertiary transition-colors">
          <X size={16} />
        </button>
      </div>

      <div className="px-4 py-3 border-b border-border-custom">
        <div className="flex items-center gap-2 bg-bg-tertiary rounded-lg px-3 py-1.5">
          <Search size={14} className="text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索公式..."
            className="bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none flex-1"
          />
        </div>
      </div>

      <div className="px-4 py-2 border-b border-border-custom">
        <div className="flex gap-1 bg-bg-tertiary rounded-lg p-0.5">
          <button
            onClick={() => setActiveTab('all')}
            className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${
              activeTab === 'all'
                ? 'bg-accent text-bg-primary font-medium'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            全部公式
          </button>
          <button
            onClick={() => setActiveTab('similar')}
            className={`flex items-center justify-center gap-1 flex-1 text-xs py-1.5 rounded-md transition-colors ${
              activeTab === 'similar'
                ? 'bg-accent text-bg-primary font-medium'
                : 'text-text-secondary hover:text-text-primary'
            }`}
            disabled={!latex.trim()}
          >
            <Sparkles size={10} />
            相似推荐
          </button>
        </div>
      </div>

      <div className="px-4 py-3 border-b border-border-custom">
        {showSaveInput ? (
          <div className="flex flex-col gap-2">
            <input
              type="text"
              value={saveTitle}
              onChange={(e) => setSaveTitle(e.target.value)}
              placeholder="公式名称..."
              className="bg-bg-tertiary text-sm text-text-primary placeholder:text-text-muted rounded-lg px-3 py-1.5 outline-none border border-border-custom focus:border-accent"
              autoFocus
              onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); }}
            />
            <div className="flex gap-2">
              <button
                onClick={handleSave}
                className="flex-1 text-xs bg-accent text-bg-primary font-medium py-1.5 rounded-lg hover:bg-accent-hover transition-colors"
              >
                保存
              </button>
              <button
                onClick={() => setShowSaveInput(false)}
                className="flex-1 text-xs bg-bg-tertiary text-text-secondary py-1.5 rounded-lg hover:text-text-primary transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowSaveInput(true)}
            disabled={!latex.trim()}
            className="w-full flex items-center justify-center gap-1.5 text-xs bg-accent/10 text-accent font-medium py-2 rounded-lg hover:bg-accent/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Plus size={14} />
            保存当前公式
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2 scrollbar-thin">
        {activeTab === 'similar' ? (
          <>
            {!latex.trim() ? (
              <div className="text-center text-text-muted text-sm py-8">
                请先在编辑器中输入公式
              </div>
            ) : similarFormulas.length === 0 ? (
              <div className="text-center text-text-muted text-sm py-8">
                暂无相似公式推荐
                <div className="text-xs text-text-muted/70 mt-1">
                  继续编辑或保存更多公式以获得推荐
                </div>
              </div>
            ) : (
              <>
                <div className="text-xs text-text-muted mb-2 px-1">
                  找到 {similarFormulas.length} 个相似公式，可直接复用：
                </div>
                {similarFormulas.map((result, idx) => (
                  <SimilarFormulaCard
                    key={`similar-${idx}-${result.formula.id}`}
                    formula={result.formula}
                    similarity={result.similarity}
                    onLoad={handleLoad}
                  />
                ))}
              </>
            )}
          </>
        ) : (
          <>
            {filtered.length === 0 ? (
              <div className="text-center text-text-muted text-sm py-8">
                {formulas.length === 0 ? '公式库为空，保存你的第一个公式吧' : '没有匹配的公式'}
              </div>
            ) : (
              filtered.map((f) => (
                <FormulaCard key={f.id} formula={f} onLoad={handleLoad} onDelete={handleDelete} />
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}
