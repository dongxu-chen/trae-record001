import { useState, useEffect } from 'react';
import { useCardStore } from '@/stores/cardStore';
import { useExportStore } from '@/stores/exportStore';
import { Download, Image, Printer, FileJson, Search } from 'lucide-react';
import type { PrintLayoutOptions } from '@/types';

const FORMAT_OPTIONS = [
  { value: 'png', label: 'PNG', icon: Image },
  { value: 'jpg', label: 'JPG', icon: Image },
  { value: 'pdf', label: 'PDF', icon: Printer },
];

const RESOLUTION_OPTIONS = [
  { value: 1, label: '1x' },
  { value: 2, label: '2x' },
  { value: 4, label: '4x' },
];

const PAPER_SIZES = ['A4', 'A3', 'Letter'] as const;
const ORIENTATIONS = ['portrait', 'landscape'] as const;

const DEFAULT_PRINT_LAYOUT: PrintLayoutOptions = {
  paperSize: 'A4',
  orientation: 'portrait',
  columns: 3,
  rows: 3,
  margin: 10,
  bleed: 0,
  cropMarks: false,
};

export default function Export() {
  const { cards, fetchCards } = useCardStore();
  const { exporting, exportCard, exportBatch, exportPrint, exportJson } = useExportStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCardIds, setSelectedCardIds] = useState<Set<string>>(new Set());
  const [format, setFormat] = useState('png');
  const [resolution, setResolution] = useState(2);
  const [printLayout, setPrintLayout] = useState<PrintLayoutOptions>(DEFAULT_PRINT_LAYOUT);

  useEffect(() => {
    fetchCards();
  }, [fetchCards]);

  const filteredCards = cards.filter((c) =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const toggleCard = (id: string) => {
    setSelectedCardIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    setSelectedCardIds(new Set(filteredCards.map((c) => c.id)));
  };

  const deselectAll = () => {
    setSelectedCardIds(new Set());
  };

  const handleExport = async () => {
    const ids = Array.from(selectedCardIds);
    if (ids.length === 0) return;

    if (format === 'pdf') {
      await exportPrint(ids, printLayout);
    } else if (ids.length === 1) {
      await exportCard(ids[0], format, resolution);
    } else {
      await exportBatch(ids, format, resolution);
    }
  };

  const handleExportJson = async () => {
    const ids = Array.from(selectedCardIds);
    if (ids.length > 0) {
      await exportJson(ids);
    }
  };

  const isPdf = format === 'pdf';

  return (
    <div className="min-h-screen p-6">
      <h1 className="font-cinzel text-2xl text-gold-500 mb-6">导出中心</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-dark-800/50 border border-dark-600 rounded-lg p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-parchment-200/40" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="dark-input w-full text-sm pl-8"
                  placeholder="搜索卡牌..."
                />
              </div>
              <button onClick={selectAll} className="text-xs text-gold-500 hover:text-gold-400 font-cinzel">
                全选
              </button>
              <button onClick={deselectAll} className="text-xs text-parchment-200/60 hover:text-parchment-200 font-cinzel">
                清除
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-[400px] overflow-y-auto">
              {filteredCards.map((card) => (
                <button
                  key={card.id}
                  onClick={() => toggleCard(card.id)}
                  className={`text-left p-2 rounded border transition-all text-xs ${
                    selectedCardIds.has(card.id)
                      ? 'border-gold-500 bg-dark-700 shadow-[0_0_8px_rgba(212,168,83,0.2)]'
                      : 'border-dark-600 bg-dark-800 hover:border-dark-600 hover:bg-dark-700/50'
                  }`}
                >
                  <span className="font-cinzel text-parchment-200 truncate block">{card.name || '未命名'}</span>
                  <span className="text-parchment-200/40 text-[10px]">{card.type} · {card.rarity}</span>
                </button>
              ))}
              {filteredCards.length === 0 && (
                <div className="col-span-full text-center py-8 text-parchment-200/40 text-sm font-crimson">
                  {searchQuery ? '未找到匹配的卡牌' : '暂无卡牌，请先在编辑器中创建'}
                </div>
              )}
            </div>

            <div className="mt-3 text-xs text-parchment-200/40 font-cinzel">
              已选择 {selectedCardIds.size} 张卡牌
            </div>
          </div>

          {isPdf && (
            <div className="bg-dark-800/50 border border-dark-600 rounded-lg p-4">
              <h3 className="font-cinzel text-gold-500 text-sm mb-3">打印布局预览</h3>
              <div className="bg-white rounded p-4 aspect-[3/4] max-w-xs mx-auto relative">
                {Array.from({ length: printLayout.columns * printLayout.rows }).map((_, i) => {
                  const col = i % printLayout.columns;
                  const row = Math.floor(i / printLayout.columns);
                  const cellW = 100 / printLayout.columns;
                  const cellH = 100 / printLayout.rows;
                  return (
                    <div
                      key={i}
                      className="absolute border border-gray-300 rounded"
                      style={{
                        left: `${col * cellW}%`,
                        top: `${row * cellH}%`,
                        width: `${cellW}%`,
                        height: `${cellH}%`,
                        margin: '2px',
                      }}
                    >
                      <div className="w-full h-full bg-gray-100 rounded flex items-center justify-center text-gray-400 text-[8px]">
                        {i < selectedCardIds.size ? `卡${i + 1}` : ''}
                      </div>
                    </div>
                  );
                })}
                {printLayout.cropMarks && (
                  <>
                    <div className="absolute inset-0 border border-dashed border-gray-400" style={{ margin: '4px' }} />
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-dark-800/50 border border-dark-600 rounded-lg p-4">
            <h3 className="font-cinzel text-gold-500 text-sm mb-3">导出格式</h3>
            <div className="space-y-2">
              {FORMAT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setFormat(opt.value)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded border transition-all text-sm ${
                    format === opt.value
                      ? 'border-gold-500 bg-dark-700 text-gold-500'
                      : 'border-dark-600 bg-dark-800 text-parchment-200/60 hover:border-dark-600 hover:text-parchment-200'
                  }`}
                >
                  <opt.icon size={16} />
                  <span className="font-cinzel text-xs">{opt.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-dark-800/50 border border-dark-600 rounded-lg p-4">
            <h3 className="font-cinzel text-gold-500 text-sm mb-3">分辨率</h3>
            <div className="flex gap-2">
              {RESOLUTION_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setResolution(opt.value)}
                  className={`flex-1 px-3 py-2 rounded border text-sm font-rajdhani transition-all ${
                    resolution === opt.value
                      ? 'border-gold-500 bg-dark-700 text-gold-500'
                      : 'border-dark-600 bg-dark-800 text-parchment-200/60 hover:text-parchment-200'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {isPdf && (
            <div className="bg-dark-800/50 border border-dark-600 rounded-lg p-4 space-y-3">
              <h3 className="font-cinzel text-gold-500 text-sm">打印设置</h3>

              <div>
                <label className="text-[10px] text-parchment-200/40 font-cinzel">纸张大小</label>
                <select
                  value={printLayout.paperSize}
                  onChange={(e) => setPrintLayout({ ...printLayout, paperSize: e.target.value as any })}
                  className="dark-input w-full text-sm"
                >
                  {PAPER_SIZES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] text-parchment-200/40 font-cinzel">方向</label>
                <select
                  value={printLayout.orientation}
                  onChange={(e) => setPrintLayout({ ...printLayout, orientation: e.target.value as any })}
                  className="dark-input w-full text-sm"
                >
                  {ORIENTATIONS.map((o) => (
                    <option key={o} value={o}>{o === 'portrait' ? '纵向' : '横向'}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-parchment-200/40 font-cinzel">列数</label>
                  <input
                    type="number"
                    value={printLayout.columns}
                    onChange={(e) => setPrintLayout({ ...printLayout, columns: Number(e.target.value) })}
                    className="dark-input w-full text-sm"
                    min={1} max={10}
                  />
                </div>
                <div>
                  <label className="text-[10px] text-parchment-200/40 font-cinzel">行数</label>
                  <input
                    type="number"
                    value={printLayout.rows}
                    onChange={(e) => setPrintLayout({ ...printLayout, rows: Number(e.target.value) })}
                    className="dark-input w-full text-sm"
                    min={1} max={10}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-parchment-200/40 font-cinzel">边距 (mm)</label>
                  <input
                    type="number"
                    value={printLayout.margin}
                    onChange={(e) => setPrintLayout({ ...printLayout, margin: Number(e.target.value) })}
                    className="dark-input w-full text-sm"
                    min={0} max={50}
                  />
                </div>
                <div>
                  <label className="text-[10px] text-parchment-200/40 font-cinzel">出血 (mm)</label>
                  <input
                    type="number"
                    value={printLayout.bleed}
                    onChange={(e) => setPrintLayout({ ...printLayout, bleed: Number(e.target.value) })}
                    className="dark-input w-full text-sm"
                    min={0} max={10}
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={printLayout.cropMarks}
                  onChange={(e) => setPrintLayout({ ...printLayout, cropMarks: e.target.checked })}
                  className="accent-gold-500"
                />
                <span className="text-xs text-parchment-200/60 font-cinzel">裁切标记</span>
              </label>
            </div>
          )}

          <div className="space-y-2">
            <button
              onClick={handleExport}
              className="metal-button-primary w-full py-2.5 rounded text-sm flex items-center justify-center gap-2"
              disabled={selectedCardIds.size === 0 || exporting}
            >
              <Download size={16} />
              {exporting ? '导出中...' : '导出卡牌'}
            </button>

            <button
              onClick={handleExportJson}
              className="metal-button w-full py-2.5 rounded text-sm flex items-center justify-center gap-2"
              disabled={selectedCardIds.size === 0 || exporting}
            >
              <FileJson size={16} />
              导出 JSON
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
