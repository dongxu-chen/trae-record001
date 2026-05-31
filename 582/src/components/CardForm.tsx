import { Swords, Shield, Wand2, Heart, Flame, Droplets, Mountain, Wind, Sun, Moon, Plus, Trash2 } from 'lucide-react';
import type { CardData, CardSkill } from '@/types';

interface CardFormProps {
  card: CardData;
  template: { id: string };
  onChange: (card: CardData) => void;
}

const TYPE_OPTIONS = [
  { value: 'attack' as const, icon: Swords, label: '攻击' },
  { value: 'defense' as const, icon: Shield, label: '防御' },
  { value: 'magic' as const, icon: Wand2, label: '魔法' },
  { value: 'support' as const, icon: Heart, label: '辅助' },
];

const RARITY_OPTIONS = [
  { value: 'common' as const, color: '#888888', label: '普通' },
  { value: 'rare' as const, color: '#4488ff', label: '稀有' },
  { value: 'epic' as const, color: '#aa44ff', label: '史诗' },
  { value: 'legendary' as const, color: '#ff8800', label: '传说' },
];

const ELEMENT_OPTIONS = [
  { value: 'fire' as const, icon: Flame, label: '火' },
  { value: 'water' as const, icon: Droplets, label: '水' },
  { value: 'earth' as const, icon: Mountain, label: '地' },
  { value: 'wind' as const, icon: Wind, label: '风' },
  { value: 'light' as const, icon: Sun, label: '光' },
  { value: 'dark' as const, icon: Moon, label: '暗' },
];

export default function CardForm({ card, onChange }: CardFormProps) {
  const update = (partial: Partial<CardData>) => {
    onChange({ ...card, ...partial });
  };

  const updateAttr = (key: keyof CardData['attributes'], value: number) => {
    onChange({ ...card, attributes: { ...card.attributes, [key]: value } });
  };

  const addSkill = () => {
    const newSkill: CardSkill = { name: '', description: '', tags: [] };
    update({ skills: [...card.skills, newSkill] });
  };

  const updateSkill = (index: number, partial: Partial<CardSkill>) => {
    const skills = card.skills.map((s, i) => (i === index ? { ...s, ...partial } : s));
    update({ skills });
  };

  const removeSkill = (index: number) => {
    update({ skills: card.skills.filter((_, i) => i !== index) });
  };

  return (
    <div className="space-y-5">
      <div>
        <label className="block font-cinzel text-gold-500 text-sm mb-1">名称</label>
        <input
          type="text"
          value={card.name}
          onChange={(e) => update({ name: e.target.value })}
          className="dark-input w-full font-crimson"
          placeholder="输入卡牌名称..."
        />
      </div>

      <div>
        <label className="block font-cinzel text-gold-500 text-sm mb-1">类型</label>
        <div className="flex gap-2">
          {TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => update({ type: opt.value })}
              className={`flex items-center gap-1.5 px-3 py-2 rounded border transition-all ${
                card.type === opt.value
                  ? 'border-gold-500 bg-dark-700 text-gold-500'
                  : 'border-dark-600 bg-dark-800 text-dark-600 hover:border-dark-600 hover:text-parchment-200'
              }`}
            >
              <opt.icon size={16} />
              <span className="text-xs font-cinzel">{opt.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block font-cinzel text-gold-500 text-sm mb-1">稀有度</label>
        <div className="flex gap-2">
          {RARITY_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => update({ rarity: opt.value })}
              className={`flex items-center gap-1.5 px-3 py-2 rounded border transition-all ${
                card.rarity === opt.value
                  ? 'bg-dark-700'
                  : 'border-dark-600 bg-dark-800 hover:bg-dark-700'
              }`}
              style={{
                borderColor: card.rarity === opt.value ? opt.color : undefined,
                color: card.rarity === opt.value ? opt.color : undefined,
              }}
            >
              <span className="text-sm">◆</span>
              <span className="text-xs font-cinzel">{opt.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block font-cinzel text-gold-500 text-sm mb-1">元素</label>
        <div className="grid grid-cols-6 gap-2">
          {ELEMENT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => update({ element: opt.value })}
              className={`flex flex-col items-center gap-1 px-2 py-2 rounded border transition-all ${
                card.element === opt.value
                  ? 'border-gold-500 bg-dark-700 text-gold-500'
                  : 'border-dark-600 bg-dark-800 text-parchment-200 hover:border-dark-600 hover:bg-dark-700'
              }`}
            >
              <opt.icon size={16} />
              <span className="text-[10px] font-cinzel">{opt.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block font-cinzel text-gold-500 text-sm mb-2">属性</label>
        <div className="grid grid-cols-2 gap-3">
          {([
            { key: 'attack' as const, label: '攻击', icon: '⚔' },
            { key: 'defense' as const, label: '防御', icon: '🛡' },
            { key: 'health' as const, label: '生命', icon: '♥' },
            { key: 'cost' as const, label: '费用', icon: '◈' },
          ]).map((attr) => (
            <div key={attr.key} className="flex items-center gap-2">
              <span className="text-sm w-5">{attr.icon}</span>
              <input
                type="range"
                min={0}
                max={99}
                value={card.attributes[attr.key]}
                onChange={(e) => updateAttr(attr.key, Number(e.target.value))}
                className="flex-1 accent-gold-500 h-1"
              />
              <span className="font-rajdhani text-gold-500 w-6 text-right text-sm font-bold">
                {card.attributes[attr.key]}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="font-cinzel text-gold-500 text-sm">技能</label>
          <button onClick={addSkill} className="text-gold-500 hover:text-gold-400 transition-colors">
            <Plus size={16} />
          </button>
        </div>
        <div className="space-y-3">
          {card.skills.map((skill, i) => (
            <div key={i} className="bg-dark-800 border border-dark-600 rounded p-3 space-y-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={skill.name}
                  onChange={(e) => updateSkill(i, { name: e.target.value })}
                  className="dark-input flex-1 text-sm"
                  placeholder="技能名称"
                />
                <button onClick={() => removeSkill(i)} className="text-crimson-500 hover:text-crimson-600 transition-colors">
                  <Trash2 size={14} />
                </button>
              </div>
              <textarea
                value={skill.description}
                onChange={(e) => updateSkill(i, { description: e.target.value })}
                className="dark-input w-full text-sm resize-none"
                rows={2}
                placeholder="技能描述"
              />
              <input
                type="text"
                value={skill.tags.join(', ')}
                onChange={(e) => updateSkill(i, { tags: e.target.value.split(',').map((t) => t.trim()).filter(Boolean) })}
                className="dark-input w-full text-sm"
                placeholder="标签 (逗号分隔)"
              />
            </div>
          ))}
        </div>
      </div>

      <div>
        <label className="block font-cinzel text-gold-500 text-sm mb-1">描述</label>
        <textarea
          value={card.description}
          onChange={(e) => update({ description: e.target.value })}
          className="dark-input w-full font-crimson resize-none"
          rows={3}
          placeholder="卡牌描述..."
        />
      </div>

      <div>
        <label className="block font-cinzel text-gold-500 text-sm mb-1">风味文字</label>
        <textarea
          value={card.flavorText}
          onChange={(e) => update({ flavorText: e.target.value })}
          className="dark-input w-full font-crimson italic resize-none"
          rows={2}
          placeholder="风味文字 (斜体显示)..."
        />
      </div>
    </div>
  );
}
