import { useState, useEffect, useCallback } from 'react';
import { useCardStore } from '@/stores/cardStore';
import { useTemplateStore } from '@/stores/templateStore';
import { useExportStore } from '@/stores/exportStore';
import CardCanvas from '@/components/CardCanvas';
import CardForm from '@/components/CardForm';
import TemplateCard from '@/components/TemplateCard';
import type { CardData, CardTemplate } from '@/types';

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

const FALLBACK_TEMPLATE: CardTemplate = {
  id: 'template-dark-fantasy',
  name: '暗黑奇幻',
  description: '暗黑奇幻风格的卡牌模板',
  style: 'fantasy',
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
  borders: { width: 3, color: '#d4a853', radius: 12, style: 'ornate' },
  layout: FALLBACK_LAYOUT,
  builtIn: true,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

function createEmptyCard(templateId: string): CardData {
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

export default function Editor() {
  const { currentCard, setCurrentCard, createCard, updateCard } = useCardStore();
  const { templates, fetchTemplates } = useTemplateStore();
  const { exportCard } = useExportStore();
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [saveTimeout, setSaveTimeout] = useState<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  useEffect(() => {
    if (templates.length > 0 && !selectedTemplateId) {
      setSelectedTemplateId(templates[0].id);
    }
  }, [templates, selectedTemplateId]);

  const activeTemplate = templates.find((t) => t.id === selectedTemplateId) || FALLBACK_TEMPLATE;

  const card = currentCard || createEmptyCard(activeTemplate.id);

  const handleChange = useCallback(
    (updated: CardData) => {
      setCurrentCard(updated);
      if (saveTimeout) clearTimeout(saveTimeout);
      const timeout = setTimeout(() => {
        if (updated.name) {
          updateCard(updated.id, updated);
        }
      }, 1500);
      setSaveTimeout(timeout);
    },
    [saveTimeout, setCurrentCard, updateCard],
  );

  const handleSave = async () => {
    if (!card.name) return;
    const cardWithTemplate = { ...card, templateId: selectedTemplateId || activeTemplate.id };
    if (currentCard) {
      await updateCard(card.id, cardWithTemplate);
    } else {
      await createCard(cardWithTemplate);
    }
  };

  const handleExport = async () => {
    if (!card.name) return;
    await exportCard(card.id, 'png', 2);
  };

  return (
    <div className="h-screen flex flex-col lg:flex-row">
      <div className="lg:w-80 xl:w-96 flex-shrink-0 bg-dark-800/50 border-r border-dark-600 overflow-y-auto p-4">
        <h2 className="font-cinzel text-gold-500 text-sm mb-4">卡牌属性</h2>
        <CardForm card={card} template={activeTemplate} onChange={handleChange} />
      </div>

      <div className="flex-1 flex items-center justify-center bg-dark-900/50 p-6">
        <CardCanvas cardData={card} template={activeTemplate} width={300} height={420} />
      </div>

      <div className="lg:w-72 xl:w-80 flex-shrink-0 bg-dark-800/50 border-l border-dark-600 overflow-y-auto p-4 space-y-4">
        <h2 className="font-cinzel text-gold-500 text-sm">模板选择</h2>
        <div className="flex gap-3 overflow-x-auto pb-2 lg:flex-wrap">
          {templates.map((tmpl) => (
            <TemplateCard
              key={tmpl.id}
              template={tmpl}
              selected={selectedTemplateId === tmpl.id}
              onClick={() => setSelectedTemplateId(tmpl.id)}
            />
          ))}
        </div>

        <div className="divider-ornate text-xs font-cinzel">◆</div>

        <div className="space-y-2">
          <h3 className="font-cinzel text-gold-500 text-xs">图片上传</h3>
          <button className="metal-button w-full text-xs py-2 rounded">
            上传卡面图片
          </button>
          <button className="metal-button w-full text-xs py-2 rounded">
            上传背景图片
          </button>
        </div>

        <div className="divider-ornate text-xs font-cinzel">◆</div>

        <div className="space-y-2 pt-2">
          <button
            onClick={handleSave}
            className="metal-button-primary w-full text-xs py-2.5 rounded"
            disabled={!card.name}
          >
            保存卡牌
          </button>
          <button
            onClick={handleExport}
            className="metal-button w-full text-xs py-2.5 rounded"
            disabled={!card.name}
          >
            导出图片
          </button>
        </div>
      </div>
    </div>
  );
}
