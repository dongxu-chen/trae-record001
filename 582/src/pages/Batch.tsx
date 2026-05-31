import { useState, useEffect, useRef } from 'react';
import { useTemplateStore } from '@/stores/templateStore';
import { useCardStore } from '@/stores/cardStore';
import { useExportStore } from '@/stores/exportStore';
import CardCanvas from '@/components/CardCanvas';
import { Plus, Trash2, FileJson, Image, Grid, Zap, Clock } from 'lucide-react';
import type { CardData } from '@/types';

const FALLBACK_LAYOUT = {
  name: { x: 30, y: 35, fontSize: 22, color: '#d4a853', fontFamily: 'Cinzel, serif' },
  type: { x: 30, y: 58, fontSize: 13, color: '#a89b8c' },
  rarity: { x: 370, y: 35, iconSize: 18 },
  attributes: {
    attack: { x: 30, y: 530, fontSize: 16, color: '#e74c3c' },
    defense: { x: 120, y: 530, fontSize: 16, color: '#3498db' },
    health: { x: 210, y: 530, fontSize: 16, color: '#2ecc71' },
    cost: { x: 300, y: 530, fontSize: 16, color: '#9b59b6' },
  },
  skills: {
    type: 'loop' as const,
    arrayPath: 'skills',
    itemSpacing: 8,
    startY: 370,
    maxItems: 4,
    headerLine: true,
    separator: true,
    itemLayout: {
      title: { x: 30, y: 370, fontSize: 13, color: '#d4a853', fontFamily: 'serif', fontWeight: 'bold', prefix: '◆ ' },
      description: { x: 30, y: 392, fontSize: 11, color: '#a89b8c', fontFamily: 'sans-serif', fontStyle: 'normal' },
      indent: 12,
    },
  },
  description: { x: 30, y: 290, maxWidth: 340, fontSize: 12, lineHeight: 18 },
  flavorText: { x: 30, y: 460, maxWidth: 340, fontSize: 11, fontStyle: 'italic' },
  backgroundImage: { x: 0, y: 0, width: 400, height: 560 },
  characterImage: { x: 50, y: 80, width: 300, height: 200 },
};

const FALLBACK_TEMPLATE = {
  id: 'template-dark-fantasy',
  name: '暗黑奇幻',
  description: '暗黑奇幻风格',
  style: 'fantasy' as const,
  width: 400,
  height: 560,
  colors: {
    background: '#1a1a2e',
    primary: '#d4a853',
    secondary: '#a89b8c',
    accent: '#e74c3c',
    text: '#e8e0d4',
    textSecondary: '#a89b8c',
    cardBackground: '#16213e',
    divider: '#2a2a4a',
  },
  borders: { width: 3, color: '#d4a853', radius: 12, style: 'ornate' as const },
  layout: FALLBACK_LAYOUT,
  builtIn: true,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

function createEmptyRow(templateId: string = 'template-dark-fantasy'): CardData {
  return {
    id: crypto.randomUUID(),
    name: '',
    type: 'attack',
    rarity: 'common',
    element: 'fire',
    attributes: { attack: 5, defense: 5, health: 10, cost: 3 },
    skills: [],
    description: '',
    flavorText: '',
    templateId,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

type InputMode = 'table' | 'import';

export default function Batch() {
  const { templates, fetchTemplates } = useTemplateStore();
  const { fetchCards } = useCardStore();
  const { exportBatch, exportJson, batchGenerate, generating, exporting, progress } = useExportStore();
  const [selectedTemplateId, setSelectedTemplateId] = useState('template-dark-fantasy');
  const [inputMode, setInputMode] = useState<InputMode>('table');
  const [batchData, setBatchData] = useState<CardData[]>([createEmptyRow()]);
  const [importText, setImportText] = useState('');
  const [lastDuration, setLastDuration] = useState<string | null>(null);
  const startTimeRef = useRef<number>(0);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const activeTemplate = templates.find((t) => t.id === selectedTemplateId) || FALLBACK_TEMPLATE;

  const updateRow = (index: number, partial: Partial<CardData>) => {
    setBatchData((prev) => prev.map((row, i) => (i === index ? { ...row, ...partial, templateId: selectedTemplateId } : row)));
  };

  const addRow = () => {
    setBatchData((prev) => [...prev, createEmptyRow(selectedTemplateId)]);
  };

  const removeRow = (index: number) => {
    setBatchData((prev) => prev.filter((_, i) => i !== index));
  };

  const handleImport = () => {
    try {
      const parsed = JSON.parse(importText);
      const items = Array.isArray(parsed) ? parsed : [parsed];
      const cards: CardData[] = items.map((item: any) => ({
        id: item.id || crypto.randomUUID(),
        name: item.name || '',
        type: item.type || 'attack',
        rarity: item.rarity || 'common',
        element: item.element || 'fire',
        attributes: item.attributes || { attack: 5, defense: 5, health: 10, cost: 3 },
        skills: item.skills || [],
        description: item.description || '',
        flavorText: item.flavorText || '',
        templateId: selectedTemplateId,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }));
      setBatchData(cards);
      setInputMode('table');
    } catch {
      alert('JSON 格式错误，请检查输入');
    }
  };

  const handleGenerateAll = async () => {
    const valid = batchData.filter((c) => c.name);
    if (valid.length === 0) return;

    startTimeRef.current = Date.now();
    setLastDuration(null);

    try {
      const results = await batchGenerate(valid);
      const duration = ((Date.now() - startTimeRef.current) / 1000).toFixed(2);
      setLastDuration(duration);
      fetchCards();
      setBatchData([createEmptyRow(selectedTemplateId)]);
    } catch (err) {
      console.error('批量生成失败:', err);
    }
  };

  const handleFillSample = () => {
    const sampleData: CardData[] = [];
    const types: CardData['type'][] = ['attack', 'defense', 'magic', 'support'];
    const rarities: CardData['rarity'][] = ['common', 'rare', 'epic', 'legendary'];
    const elements: CardData['element'][] = ['fire', 'water', 'earth', 'wind', 'light', 'dark'];

    for (let i = 0; i < 50; i++) {
      sampleData.push({
        id: crypto.randomUUID(),
        name: `卡牌 ${i + 1}`,
        type: types[i % 4],
        rarity: rarities[Math.floor(i / 15) % 4],
        element: elements[i % 6],
        attributes: {
          attack: Math.floor(Math.random() * 20) + 1,
          defense: Math.floor(Math.random() * 20) + 1,
          health: Math.floor(Math.random() * 30) + 10,
          cost: Math.floor(Math.random() * 10) + 1,
        },
        skills: [
          { name: `技能 ${i + 1}A`, description: '造成大量伤害并附加灼烧效果', tags: ['伤害', '灼烧'] },
          { name: `技能 ${i + 1}B`, description: '提升自身防御力持续3回合', tags: ['防御', '增益'] },
        ],
        description: `这是第 ${i + 1} 张测试卡牌，具有强大的 ${types[i % 4]} 能力。`,
        flavorText: `传说中的第 ${i + 1} 位勇士。`,
        templateId: selectedTemplateId,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    }
    setBatchData(sampleData);
  };

  const validCards = batchData.filter((c) => c.name);
  const validCardIds = validCards.map((c) => c.id);

  return (
    <div className="min-h-screen p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="font-cinzel text-2xl text-gold-500">批量生成</h1>
          <div className="flex items-center gap-2 text-parchment-200/60 text-xs">
            <Zap size={14} className="text-gold-500" />
            <span>并行处理 · 12并发</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <label className="font-cinzel text-gold-500 text-xs">模板:</label>
          <select
            value={selectedTemplateId}
            onChange={(e) => setSelectedTemplateId(e.target.value)}
            className="dark-input text-sm"
          >
            <option value="template-dark-fantasy">暗黑奇幻</option>
            {templates.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
          <button
            onClick={handleFillSample}
            className="metal-button px-3 py-1.5 rounded text-xs flex items-center gap-1"
          >
            <Plus size={12} /> 填充50张
          </button>
        </div>
      </div>

      {(generating || exporting) && (
        <div className="bg-dark-800/50 border border-dark-600 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Zap size={14} className="text-gold-500 animate-pulse" />
              <span className="font-cinzel text-gold-500 text-xs">
                {generating ? '正在批量生成...' : '正在导出...'}
              </span>
            </div>
            <div className="flex items-center gap-3">
              {startTimeRef.current > 0 && (
                <div className="flex items-center gap-1 text-xs text-parchment-200/60">
                  <Clock size={12} />
                  <span>{((Date.now() - startTimeRef.current) / 1000).toFixed(1)}s</span>
                </div>
              )}
              <span className="font-rajdhani text-gold-500 text-sm">{progress}%</span>
            </div>
          </div>
          <div className="w-full h-2 bg-dark-900 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-gold-600 to-gold-400 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {lastDuration && (
        <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-3 flex items-center gap-2">
          <Zap size={16} className="text-green-500" />
          <span className="text-green-400 text-sm font-cinzel">
            生成完成！用时 <span className="font-bold">{lastDuration}s</span>，平均每张 {(parseFloat(lastDuration) / validCards.length * 1000).toFixed(0)}ms
          </span>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => setInputMode('table')}
          className={`px-3 py-1.5 rounded text-xs font-cinzel transition-all ${
            inputMode === 'table'
              ? 'bg-dark-700 text-gold-500 border border-gold-500/30'
              : 'bg-dark-800 text-parchment-200/60 border border-dark-600 hover:text-parchment-200'
          }`}
        >
          <Grid size={12} className="inline mr-1" />
          表格模式
        </button>
        <button
          onClick={() => setInputMode('import')}
          className={`px-3 py-1.5 rounded text-xs font-cinzel transition-all ${
            inputMode === 'import'
              ? 'bg-dark-700 text-gold-500 border border-gold-500/30'
              : 'bg-dark-800 text-parchment-200/60 border border-dark-600 hover:text-parchment-200'
          }`}
        >
          <FileJson size={12} className="inline mr-1" />
          导入模式
        </button>
      </div>

      {inputMode === 'table' ? (
        <div className="bg-dark-800/50 border border-dark-600 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-dark-700/50">
                  <th className="px-3 py-2 text-left font-cinzel text-gold-500/70 text-xs">#</th>
                  <th className="px-3 py-2 text-left font-cinzel text-gold-500/70 text-xs">名称</th>
                  <th className="px-3 py-2 text-left font-cinzel text-gold-500/70 text-xs">类型</th>
                  <th className="px-3 py-2 text-left font-cinzel text-gold-500/70 text-xs">稀有度</th>
                  <th className="px-3 py-2 text-center font-cinzel text-gold-500/70 text-xs">攻击</th>
                  <th className="px-3 py-2 text-center font-cinzel text-gold-500/70 text-xs">防御</th>
                  <th className="px-3 py-2 text-center font-cinzel text-gold-500/70 text-xs">生命</th>
                  <th className="px-3 py-2 text-center font-cinzel text-gold-500/70 text-xs">费用</th>
                  <th className="px-3 py-2 text-left font-cinzel text-gold-500/70 text-xs">描述</th>
                  <th className="px-3 py-2 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {batchData.map((row, i) => (
                  <tr key={row.id} className="border-t border-dark-600/50 hover:bg-dark-700/30">
                    <td className="px-3 py-1.5 text-parchment-200/40 text-xs font-mono">{i + 1}</td>
                    <td className="px-3 py-1.5">
                      <input
                        type="text"
                        value={row.name}
                        onChange={(e) => updateRow(i, { name: e.target.value })}
                        className="dark-input w-full text-xs py-1"
                        placeholder="名称"
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={row.type}
                        onChange={(e) => updateRow(i, { type: e.target.value as CardData['type'] })}
                        className="dark-input text-xs py-1"
                      >
                        <option value="attack">攻击</option>
                        <option value="defense">防御</option>
                        <option value="magic">魔法</option>
                        <option value="support">辅助</option>
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      <select
                        value={row.rarity}
                        onChange={(e) => updateRow(i, { rarity: e.target.value as CardData['rarity'] })}
                        className="dark-input text-xs py-1"
                      >
                        <option value="common">普通</option>
                        <option value="rare">稀有</option>
                        <option value="epic">史诗</option>
                        <option value="legendary">传说</option>
                      </select>
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        type="number"
                        value={row.attributes.attack}
                        onChange={(e) => updateRow(i, { attributes: { ...row.attributes, attack: Number(e.target.value) } })}
                        className="dark-input w-full text-xs py-1 text-center"
                        min={0} max={99}
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        type="number"
                        value={row.attributes.defense}
                        onChange={(e) => updateRow(i, { attributes: { ...row.attributes, defense: Number(e.target.value) } })}
                        className="dark-input w-full text-xs py-1 text-center"
                        min={0} max={99}
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        type="number"
                        value={row.attributes.health}
                        onChange={(e) => updateRow(i, { attributes: { ...row.attributes, health: Number(e.target.value) } })}
                        className="dark-input w-full text-xs py-1 text-center"
                        min={0} max={99}
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        type="number"
                        value={row.attributes.cost}
                        onChange={(e) => updateRow(i, { attributes: { ...row.attributes, cost: Number(e.target.value) } })}
                        className="dark-input w-full text-xs py-1 text-center"
                        min={0} max={99}
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <input
                        type="text"
                        value={row.description}
                        onChange={(e) => updateRow(i, { description: e.target.value })}
                        className="dark-input w-full text-xs py-1"
                        placeholder="描述"
                      />
                    </td>
                    <td className="px-3 py-1.5">
                      <button onClick={() => removeRow(i)} className="text-crimson-500 hover:text-crimson-600">
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="p-3 border-t border-dark-600/50 flex items-center justify-between">
            <button onClick={addRow} className="metal-button text-xs py-1.5 px-3 rounded flex items-center gap-1">
              <Plus size={12} /> 添加行
            </button>
            <span className="text-parchment-200/40 text-xs">
              共 {batchData.length} 行，有效 {validCards.length} 张
            </span>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <textarea
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            className="dark-input w-full font-mono text-xs resize-none"
            rows={10}
            placeholder='[{"name":"卡牌1","type":"attack","rarity":"common","element":"fire","attributes":{"attack":5,"defense":3,"health":10,"cost":3}}]'
          />
          <button onClick={handleImport} className="metal-button text-xs py-1.5 px-4 rounded">
            导入数据
          </button>
        </div>
      )}

      {validCards.length > 0 && (
        <div>
          <h3 className="font-cinzel text-gold-500 text-sm mb-3">预览 ({validCards.length} 张)</h3>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
            {validCards.slice(0, 24).map((card) => (
              <CardCanvas
                key={card.id}
                cardData={card}
                template={activeTemplate}
                width={120}
                height={168}
              />
            ))}
            {validCards.length > 24 && (
              <div className="flex items-center justify-center border border-dashed border-dark-600 rounded-lg h-40 text-parchment-200/40 text-xs">
                +{validCards.length - 24} 更多
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={handleGenerateAll}
          className="metal-button-primary px-5 py-2.5 rounded text-sm flex items-center gap-2"
          disabled={validCards.length === 0 || generating || exporting}
        >
          <Zap size={16} /> 并行生成 ({validCards.length}张)
        </button>
        <button
          onClick={() => validCardIds.length > 0 && exportBatch(validCardIds, 'png', 2)}
          className="metal-button px-5 py-2.5 rounded text-sm flex items-center gap-2"
          disabled={validCards.length === 0 || exporting || generating}
        >
          <Image size={16} /> 导出图片
        </button>
        <button
          onClick={() => validCardIds.length > 0 && exportJson(validCardIds)}
          className="metal-button px-5 py-2.5 rounded text-sm flex items-center gap-2"
          disabled={validCards.length === 0 || exporting || generating}
        >
          <FileJson size={16} /> 导出 JSON
        </button>
      </div>
    </div>
  );
}
