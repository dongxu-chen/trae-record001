import { useState, useEffect } from 'react';
import { Sparkles, Wand2, Save, RefreshCw } from 'lucide-react';
import { useCardStore } from '@/stores/cardStore';
import { useTemplateStore } from '@/stores/templateStore';
import CardCanvas from '@/components/CardCanvas';
import type { CardData, AICardRequest } from '@/types';

const STYLE_OPTIONS = [
  { value: 'fantasy', label: '暗黑奇幻' },
  { value: 'sci-fi', label: '未来科幻' },
  { value: 'minimal', label: '极简风格' },
  { value: 'classic', label: '经典风格' },
];

const RARITY_OPTIONS = [
  { value: 'common', label: '普通' },
  { value: 'rare', label: '稀有' },
  { value: 'epic', label: '史诗' },
  { value: 'legendary', label: '传说' },
];

const TYPE_OPTIONS = [
  { value: 'attack', label: '攻击型' },
  { value: 'defense', label: '防御型' },
  { value: 'magic', label: '魔法型' },
  { value: 'support', label: '辅助型' },
];

const EXAMPLE_PROMPTS = [
  '一个强大的火焰法师，擅长群体伤害',
  '坚韧的守护者，能够保护队友',
  '敏捷的刺客，拥有致命一击',
  '神圣的牧师，治疗与祝福',
];

export default function AIDesign() {
  const { createCard } = useCardStore();
  const { templates, fetchTemplates } = useTemplateStore();
  const [description, setDescription] = useState('');
  const [style, setStyle] = useState('fantasy');
  const [rarity, setRarity] = useState('');
  const [type, setType] = useState('');
  const [generatedCard, setGeneratedCard] = useState<Omit<CardData, 'id' | 'createdAt' | 'updatedAt'> | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const defaultTemplate = templates[0];

  const handleGenerate = async () => {
    if (!description.trim()) {
      setMessage({ type: 'error', text: '请输入卡牌描述' });
      return;
    }

    setIsGenerating(true);
    setMessage(null);

    try {
      const response = await fetch('/api/ai/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description,
          style,
          rarity: rarity || undefined,
          type: type || undefined,
        } as AICardRequest),
      });

      const result = await response.json();
      if (result.success) {
        setGeneratedCard(result.data);
        setMessage({ type: 'success', text: '卡牌生成成功！' });
      } else {
        setMessage({ type: 'error', text: result.error || '生成失败' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: '网络错误，请重试' });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!generatedCard) return;

    setIsSaving(true);
    try {
      const savedCard = await createCard(generatedCard);
      if (savedCard) {
        setMessage({ type: 'success', text: '卡牌已保存！' });
      } else {
        setMessage({ type: 'error', text: '保存失败' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: '保存失败，请重试' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleExampleClick = (prompt: string) => {
    setDescription(prompt);
  };

  return (
    <div className="h-full overflow-auto p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Sparkles className="text-gold-500" size={28} />
          <h1 className="font-cinzel text-2xl text-gold-500">AI 卡牌设计</h1>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div className="bg-dark-800 rounded-xl p-6 border border-dark-600">
              <h2 className="font-cinzel text-lg text-parchment-100 mb-4">描述你的卡牌</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-parchment-200/70 mb-2">卡牌描述</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="例如：一个强大的火焰法师，擅长群体伤害..."
                    className="w-full h-32 px-4 py-3 bg-dark-900 border border-dark-500 rounded-lg text-parchment-100 placeholder-parchment-200/30 focus:border-gold-500 focus:outline-none resize-none transition-colors"
                  />
                </div>

                <div className="flex flex-wrap gap-2">
                  {EXAMPLE_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => handleExampleClick(prompt)}
                      className="px-3 py-1 text-xs bg-dark-700 text-parchment-200/60 rounded-full hover:bg-dark-600 hover:text-parchment-100 transition-colors"
                    >
                      {prompt.slice(0, 15)}...
                    </button>
                  ))}
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm text-parchment-200/70 mb-2">风格</label>
                    <select
                      value={style}
                      onChange={(e) => setStyle(e.target.value)}
                      className="w-full px-3 py-2 bg-dark-900 border border-dark-500 rounded-lg text-parchment-100 focus:border-gold-500 focus:outline-none"
                    >
                      {STYLE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm text-parchment-200/70 mb-2">稀有度</label>
                    <select
                      value={rarity}
                      onChange={(e) => setRarity(e.target.value)}
                      className="w-full px-3 py-2 bg-dark-900 border border-dark-500 rounded-lg text-parchment-100 focus:border-gold-500 focus:outline-none"
                    >
                      <option value="">自动</option>
                      {RARITY_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm text-parchment-200/70 mb-2">类型</label>
                    <select
                      value={type}
                      onChange={(e) => setType(e.target.value)}
                      className="w-full px-3 py-2 bg-dark-900 border border-dark-500 rounded-lg text-parchment-100 focus:border-gold-500 focus:outline-none"
                    >
                      <option value="">自动</option>
                      {TYPE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <button
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  className="w-full py-3 bg-gradient-to-r from-gold-600 to-gold-500 text-dark-900 font-cinzel font-bold rounded-lg hover:from-gold-500 hover:to-gold-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                >
                  {isGenerating ? (
                    <RefreshCw className="animate-spin" size={20} />
                  ) : (
                    <Wand2 size={20} />
                  )}
                  {isGenerating ? '生成中...' : 'AI 生成卡牌'}
                </button>

                {message && (
                  <div className={`p-3 rounded-lg ${
                    message.type === 'success' 
                      ? 'bg-green-900/30 border border-green-500/30 text-green-400' 
                      : 'bg-red-900/30 border border-red-500/30 text-red-400'
                  }`}>
                    {message.text}
                  </div>
                )}
              </div>
            </div>

            {generatedCard && (
              <div className="bg-dark-800 rounded-xl p-6 border border-dark-600">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-cinzel text-lg text-parchment-100">生成结果</h2>
                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                  >
                    <Save size={16} />
                    {isSaving ? '保存中...' : '保存卡牌'}
                  </button>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-sm text-parchment-200/50">名称：</span>
                    <span className="text-parchment-100 ml-2">{generatedCard.name}</span>
                  </div>
                  <div className="flex gap-4">
                    <div>
                      <span className="text-sm text-parchment-200/50">类型：</span>
                      <span className="text-parchment-100 ml-2">{TYPE_OPTIONS.find(t => t.value === generatedCard.type)?.label || generatedCard.type}</span>
                    </div>
                    <div>
                      <span className="text-sm text-parchment-200/50">稀有度：</span>
                      <span className="text-parchment-100 ml-2">{RARITY_OPTIONS.find(r => r.value === generatedCard.rarity)?.label || generatedCard.rarity}</span>
                    </div>
                  </div>
                  <div>
                    <span className="text-sm text-parchment-200/50">属性：</span>
                    <span className="text-parchment-100 ml-2">
                      攻击 {generatedCard.attributes.attack} / 防御 {generatedCard.attributes.defense} / 生命 {generatedCard.attributes.health} / 费用 {generatedCard.attributes.cost}
                    </span>
                  </div>
                  <div>
                    <span className="text-sm text-parchment-200/50">技能 ({generatedCard.skills.length})：</span>
                    <div className="mt-1 space-y-1">
                      {generatedCard.skills.map((skill, i) => (
                        <div key={i} className="text-sm text-parchment-100 ml-4">
                          • {skill.name}：{skill.description}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-center">
            <div className="sticky top-6">
              {generatedCard && defaultTemplate ? (
                <CardCanvas
                  cardData={{
                    ...generatedCard,
                    id: 'preview',
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString(),
                  } as CardData}
                  template={defaultTemplate}
                />
              ) : (
                <div className="w-[400px] h-[560px] bg-dark-800 rounded-xl border-2 border-dashed border-dark-600 flex items-center justify-center">
                  <div className="text-center text-parchment-200/30">
                    <Sparkles size={48} className="mx-auto mb-4" />
                    <p className="font-cinzel">输入描述并点击生成</p>
                    <p className="text-sm mt-2">预览卡牌将显示在这里</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
